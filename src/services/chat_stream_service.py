import asyncio
import json
import traceback
import uuid
from collections.abc import AsyncIterator
from datetime import datetime

from langchain.messages import AIMessage, AIMessageChunk, HumanMessage
from langgraph.types import Command

from src import config as conf
from src import knowledge_base
from src.agents import agent_manager
from src.plugins.guard import content_guard
from src.repositories.agent_config_repository import AgentConfigRepository
from src.repositories.conversation_repository import ConversationRepository
from src.storage.postgres.manager import pg_manager
from src.utils.logging_config import logger


def _build_state_files(attachments: list[dict]) -> dict:
    """将附件列表转换为 StateBackend 格式的 files 字典

    StateBackend 期望的格式:
    {
        "/attachments/file.md": {
            "content": ["line1", "line2", ...],
            "created_at": "...",
            "modified_at": "...",
        }
    }
    """
    files = {}
    for attachment in attachments:
        if attachment.get("status") != "parsed":
            continue

        file_path = attachment.get("file_path")
        markdown = attachment.get("markdown")

        if not file_path or not markdown:
            continue

        now = datetime.utcnow().isoformat() + "+00:00"
        # 将 markdown 内容按行拆分
        content_lines = markdown.split("\n")
        files[file_path] = {
            "content": content_lines,
            "created_at": attachment.get("uploaded_at", now),
            "modified_at": attachment.get("uploaded_at", now),
        }

    return files


async def _get_langgraph_messages(agent_instance, config_dict):
    graph = await agent_instance.get_graph()
    state = await graph.aget_state(config_dict)

    if not state or not state.values:
        logger.warning("No state found in LangGraph")
        return None

    return state.values.get("messages", [])


def extract_agent_state(values: dict) -> dict:
    """从 LangGraph state 中提取 agent 状态"""
    if not isinstance(values, dict):
        return {}

    # 直接获取，信任 state 的数据结构
    todos = values.get("todos")
    result = {
        "todos": list(todos)[:20] if todos else [],
        "files": values.get("files") or {},
    }

    return result


async def _get_existing_message_ids(conv_repo: ConversationRepository, thread_id: str) -> set[str]:
    existing_messages = await conv_repo.get_messages_by_thread_id(thread_id)
    return {
        msg.extra_metadata["id"]
        for msg in existing_messages
        if msg.extra_metadata and "id" in msg.extra_metadata and isinstance(msg.extra_metadata["id"], str)
    }


def _normalize_tool_call(tc: dict) -> dict:
    """兼容 LangChain 多种 tool_call 格式：顶层 name/args/id 或 function.name/function.arguments，id 可能在 tool_call_id。"""
    if not tc:
        return {}
    name = tc.get("name")
    args = tc.get("args")
    tc_id = tc.get("id") or tc.get("tool_call_id")
    if name is None and isinstance(tc.get("function"), dict):
        fn = tc["function"]
        name = fn.get("name", "unknown")
        args = args or fn.get("arguments")
        if isinstance(args, str):
            try:
                args = json.loads(args) if args.strip() else {}
            except Exception:
                args = {}
    return {"name": name or "unknown", "args": args if isinstance(args, dict) else (args or {}), "id": tc_id}


def _ensure_response_metadata_model(msg_dict: dict, model_name: str | None) -> None:
    """若消息无 response_metadata.model_name，则用当前请求的 model 填充，便于调用统计按模型分组。"""
    if not model_name:
        return
    existing = (msg_dict.get("response_metadata") or {}).get("model_name")
    if existing and str(existing).strip():
        return
    msg_dict.setdefault("response_metadata", {})["model_name"] = model_name


async def _save_ai_message(
    conv_repo: ConversationRepository,
    thread_id: str,
    msg_dict: dict,
    model_name: str | None = None,
) -> None:
    _ensure_response_metadata_model(msg_dict, model_name)
    content = msg_dict.get("content", "")
    tool_calls_data = msg_dict.get("tool_calls", [])

    ai_msg = await conv_repo.add_message_by_thread_id(
        thread_id=thread_id,
        role="assistant",
        content=content,
        message_type="text",
        extra_metadata=msg_dict,
    )

    if ai_msg and tool_calls_data:
        for tc in tool_calls_data:
            if not isinstance(tc, dict):
                continue
            norm = _normalize_tool_call(tc)
            await conv_repo.add_tool_call(
                message_id=ai_msg.id,
                tool_name=norm.get("name", "unknown"),
                tool_input=norm.get("args") or {},
                status="pending",
                langgraph_tool_call_id=norm.get("id"),
            )


async def _save_tool_message(conv_repo: ConversationRepository, msg_dict: dict) -> None:
    tool_call_id = msg_dict.get("tool_call_id")
    content = msg_dict.get("content", "")

    if not tool_call_id:
        return

    if isinstance(content, list):
        tool_output = json.dumps(content) if content else ""
    else:
        tool_output = str(content)

    await conv_repo.update_tool_call_output(
        langgraph_tool_call_id=tool_call_id,
        tool_output=tool_output,
        status="success",
    )


async def save_partial_message(
    conv_repo: ConversationRepository,
    thread_id: str,
    full_msg=None,
    error_message: str | None = None,
    error_type: str = "interrupted",
):
    try:
        extra_metadata = {
            "error_type": error_type,
            "is_error": True,
            "error_message": error_message or f"发生错误: {error_type}",
        }
        if full_msg:
            msg_dict = full_msg.model_dump() if hasattr(full_msg, "model_dump") else {}
            content = full_msg.content if hasattr(full_msg, "content") else str(full_msg)
            extra_metadata = msg_dict | extra_metadata
        else:
            content = ""

        return await conv_repo.add_message_by_thread_id(
            thread_id=thread_id,
            role="assistant",
            content=content,
            message_type="text",
            extra_metadata=extra_metadata,
        )

    except Exception as e:
        logger.error(f"Error saving message: {e}")
        logger.error(traceback.format_exc())
        return None


async def save_messages_from_langgraph_state(
    agent_instance,
    thread_id: str,
    conv_repo: ConversationRepository,
    config_dict: dict,
    model_name: str | None = None,
) -> None:
    try:
        messages = await _get_langgraph_messages(agent_instance, config_dict)
        if messages is None:
            return

        existing_ids = await _get_existing_message_ids(conv_repo, thread_id)

        for msg in messages:
            msg_dict = msg.model_dump() if hasattr(msg, "model_dump") else {}
            # LangChain 可能返回 type="ai" 或 type="AIMessage"
            msg_type = (msg_dict.get("type") or "").lower()
            if msg_type == "aimessage":
                msg_type = "ai"

            if msg_type == "human" or getattr(msg, "id", None) in existing_ids:
                continue

            if msg_type == "ai":
                await _save_ai_message(conv_repo, thread_id, msg_dict, model_name=model_name)
            elif msg_type == "tool":
                await _save_tool_message(conv_repo, msg_dict)

    except Exception as e:
        logger.error(f"Error saving messages from LangGraph state: {e}")
        logger.error(traceback.format_exc())


async def check_and_handle_interrupts(
    agent,
    langgraph_config: dict,
    make_chunk,
    meta: dict,
    thread_id: str,
) -> AsyncIterator[bytes]:
    try:
        graph = await agent.get_graph()
        state = await graph.aget_state(langgraph_config)

        if not state or not state.values:
            return

        interrupt_info = None

        if hasattr(state, "tasks") and state.tasks:
            for task in state.tasks:
                if hasattr(task, "interrupts") and task.interrupts:
                    interrupt_info = task.interrupts[0]
                    break

        if not interrupt_info and state.values:
            interrupt_data = state.values.get("__interrupt__")
            if interrupt_data and isinstance(interrupt_data, list) and len(interrupt_data) > 0:
                interrupt_info = interrupt_data[0]

        if interrupt_info:
            question = "是否批准以下操作？"
            operation = "需要人工审批的操作"
            if isinstance(interrupt_info, dict):
                question = interrupt_info.get("question", question)
                operation = interrupt_info.get("operation", operation)
            elif hasattr(interrupt_info, "question"):
                question = getattr(interrupt_info, "question", question)
                operation = getattr(interrupt_info, "operation", operation)

            meta["interrupt"] = {
                "question": question,
                "operation": operation,
                "thread_id": thread_id,
            }
            yield make_chunk(status="interrupted", message=question, meta=meta)

    except Exception as e:
        logger.error(f"Error checking interrupts: {e}")
        logger.error(traceback.format_exc())


async def stream_agent_chat(
    *,
    agent_id: str,
    query: str,
    config: dict,
    meta: dict,
    image_content: str | None,
    current_user,
    db,
) -> AsyncIterator[bytes]:
    start_time = asyncio.get_event_loop().time()

    def make_chunk(content=None, **kwargs):
        return (
            json.dumps(
                {"request_id": meta.get("request_id"), "response": content, **kwargs}, ensure_ascii=False
            ).encode("utf-8")
            + b"\n"
        )

    if image_content:
        human_message = HumanMessage(
            content=[
                {"type": "text", "text": query},
                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_content}"}},
            ]
        )
        message_type = "multimodal_image"
    else:
        human_message = HumanMessage(content=query)
        message_type = "text"

    init_msg = {"role": "user", "content": query, "type": "human"}
    if image_content:
        init_msg["message_type"] = "multimodal_image"
        init_msg["image_content"] = image_content
    else:
        init_msg["message_type"] = "text"

    yield make_chunk(status="init", meta=meta, msg=init_msg)

    if conf.enable_content_guard and await content_guard.check(query):
        yield make_chunk(
            status="error", error_type="content_guard_blocked", error_message="输入内容包含敏感词", meta=meta
        )
        return

    try:
        agent = agent_manager.get_agent(agent_id)
    except Exception as e:
        logger.error(f"Error getting agent {agent_id}: {e}, {traceback.format_exc()}")
        yield make_chunk(
            status="error",
            error_type="agent_error",
            error_message=f"智能体 {agent_id} 获取失败: {str(e)}",
            meta=meta,
        )
        return

    messages = [human_message]

    # 课程知识库：若本次请求带上了课本检索上下文，则将其与用户问题一起放入首条消息，便于模型基于课本作答
    course_context = config.get("course_knowledge_context")
    if course_context and isinstance(course_context, str) and course_context.strip():
        enable_web = config.get("enable_web_search") is True
        page_instruction = (
            "仅以 **数字** 形式给出页码（如 **35**、**36**），不要在 **数字** 后面再写「页」字，"
            "前端会自动将 **数字** 显示为「第N页」可点击链接。"
        )
        web_instruction = ""
        source_format_instruction = ""
        if enable_web:
            web_instruction = (
                "\n本对话已开启网络搜索。请严格依据上述课本摘录作答，"
                "并请在本轮回答中至少使用一次网络搜索工具以补充或核实信息，使课本与网络内容紧密配合。\n\n"
            )
            source_format_instruction = (
                "列举知识点时只使用一行标题：「基于课本摘录和搜索结果，该问题涉及的知识点包括：」，"
                "不要先写「基于课本摘录，该问题涉及的知识点包括：」再写「基于课本摘录和搜索结果…」。\n\n"
            )
        wrapped_content = (
            "以下是从《计算机网络：自顶向下方法》课本中检索到的相关内容，请严格基于课本摘录作答。\n\n"
            "重要说明：摘录中形如 **数字**（如 **327**）的是原书 PDF 页码。请你：\n"
            "1. 先简要列出该题涉及的知识点；\n"
            "2. 再给出对应课本页码。" + page_instruction + "\n\n"
            + source_format_instruction
            + web_instruction
            + "【课本摘录】\n"
            f"{course_context.strip()}\n\n"
            "【用户问题】\n"
            f"{query}"
        )
        human_message = HumanMessage(content=wrapped_content)
        messages = [human_message]

    user_id = str(current_user.id)
    department_id = current_user.department_id
    if not department_id:
        yield make_chunk(status="error", error_type="no_department", error_message="当前用户未绑定部门", meta=meta)
        return

    agent_config_id = config.get("agent_config_id")
    config_repo = AgentConfigRepository(db)
    config_item = None
    if agent_config_id is not None:
        try:
            config_item = await config_repo.get_by_id(int(agent_config_id))
        except Exception:
            logger.warning(f"Failed to fetch agent config {agent_config_id}: {traceback.format_exc()}")
            config_item = None
        if config_item is not None and (config_item.department_id != department_id or config_item.agent_id != agent_id):
            config_item = None

    if config_item is None:
        config_item = await config_repo.get_or_create_default(
            department_id=department_id, agent_id=agent_id, created_by=user_id
        )
        agent_config_id = config_item.id

    if not (thread_id := config.get("thread_id")):
        thread_id = str(uuid.uuid4())
        logger.warning(f"No thread_id provided, generated new thread_id: {thread_id}")

    agent_config = (config_item.config_json or {}).get("context", {})
    # 请求级覆盖：确保本回合使用用户当前选择的联网搜索、知识库，避免中途切换后仍用旧配置
    if config.get("enable_web_search") is not None:
        agent_config = {**agent_config, "enable_web_search": bool(config["enable_web_search"])}
    if "knowledges" in config:
        agent_config = {**agent_config, "knowledges": config["knowledges"] if config["knowledges"] else []}

    # 本回合若开启了联网搜索或知识库，注入明确指令，避免模型因上下文已有内容而不调用工具
    tool_use_instruction = ""
    if agent_config.get("enable_web_search") or (agent_config.get("knowledges") and len(agent_config.get("knowledges", [])) > 0):
        parts = []
        if agent_config.get("enable_web_search"):
            parts.append("联网搜索")
        if agent_config.get("knowledges") and len(agent_config["knowledges"]) > 0:
            parts.append("知识库检索")
        tool_use_instruction = (
            f"本回合用户已开启「{'」与「'.join(parts)}」，请在本轮回答中主动使用相应工具获取信息，不要仅依赖对话上文作答。"
        )

    input_context = {
        "user_id": user_id,
        "thread_id": thread_id,
        "department_id": department_id,
        "agent_config_id": agent_config_id,
        "agent_config": agent_config,
    }
    if tool_use_instruction:
        input_context["tool_use_instruction"] = tool_use_instruction

    try:
        conv_repo = ConversationRepository(db)

        # 若该 thread_id 尚无对话（如课程页前端自建 thread_id），先创建一条，避免 add_message_by_thread_id 落库失败
        if await conv_repo.get_conversation_by_thread_id(thread_id) is None:
            conv_metadata = {"source": meta.get("source", "conversation")}
            if conv_metadata.get("source") == "reading" and meta.get("book_id"):
                conv_metadata["book_id"] = meta.get("book_id")
                if meta.get("book_type"):
                    conv_metadata["book_type"] = meta.get("book_type")
                if meta.get("book_label"):
                    conv_metadata["book_label"] = meta.get("book_label")
            await conv_repo.create_conversation(
                user_id=user_id,
                agent_id=agent_id,
                title="New Conversation",
                thread_id=thread_id,
                metadata=conv_metadata,
            )

        try:
            await conv_repo.add_message_by_thread_id(
                thread_id=thread_id,
                role="user",
                content=query,
                message_type=message_type,
                image_content=image_content,
                extra_metadata={"raw_message": human_message.model_dump()},
            )
        except Exception as e:
            logger.error(f"Error saving user message: {e}")

        # 先构建 langgraph_config
        langgraph_config = {"configurable": {"thread_id": thread_id, "user_id": user_id}}

        # 注意：LangGraph 会自动从 checkpointer 恢复 state（包括 attachments 和 files）
        # 无需手动加载或传递

        # 根据用户权限过滤知识库
        requested_knowledge_names = input_context["agent_config"].get("knowledges")
        logger.info(f"Requesting knowledges: {requested_knowledge_names}")
        if requested_knowledge_names and isinstance(requested_knowledge_names, list) and requested_knowledge_names:
            user_info = {"role": "user", "department_id": department_id}
            accessible_databases = await knowledge_base.get_databases_by_user(user_info)
            accessible_kb_names = {
                db.get("name")
                for db in accessible_databases.get("databases", [])
                if isinstance(db, dict) and db.get("name")
            }
            logger.info(f"Accessible knowledges: {accessible_kb_names}")

            filtered_knowledge_names = [kb for kb in requested_knowledge_names if kb in accessible_kb_names]
            blocked_knowledge_names = [kb for kb in requested_knowledge_names if kb not in accessible_kb_names]
            if blocked_knowledge_names:
                logger.warning(f"用户 {user_id} 无权访问知识库: {blocked_knowledge_names}, 已自动过滤")
            input_context["agent_config"]["knowledges"] = filtered_knowledge_names

        full_msg = None
        accumulated_content = []
        async for msg, metadata in agent.stream_messages(messages, input_context=input_context):
            if isinstance(msg, AIMessageChunk):
                accumulated_content.append(msg.content)

                content_for_check = "".join(accumulated_content[-10:])
                if conf.enable_content_guard and await content_guard.check_with_keywords(content_for_check):
                    full_msg = AIMessage(content="".join(accumulated_content))
                    await save_partial_message(conv_repo, thread_id, full_msg, "content_guard_blocked")
                    meta["time_cost"] = asyncio.get_event_loop().time() - start_time
                    yield make_chunk(status="interrupted", message="检测到敏感内容，已中断输出", meta=meta)
                    return

                chunk_dict = msg.model_dump()
                yield make_chunk(content=msg.content, msg=chunk_dict, metadata=metadata, status="loading")
                # 流式 chunk 也可能带 tool_calls（如第二次搜索），显式下发便于前端显示「搜索中」
                tool_calls = chunk_dict.get("tool_calls") or []
                for tc in tool_calls:
                    name = (tc.get("name") or (tc.get("function") or {}).get("name") or "").lower()
                    if "tavily" in name:
                        args = tc.get("args") or (tc.get("function") or {}).get("arguments")
                        query = ""
                        if isinstance(args, dict):
                            query = args.get("query") or args.get("q") or ""
                        elif isinstance(args, str):
                            try:
                                p = json.loads(args)
                                query = p.get("query") or p.get("q") or ""
                            except Exception:
                                pass
                        yield make_chunk(
                            status="loading",
                            tool_calling={"name": "tavily_search", "query": query},
                            metadata=metadata,
                        )
                        break
            else:
                msg_dict = msg.model_dump()
                yield make_chunk(msg=msg_dict, metadata=metadata, status="loading")

                # 显式下发「正在搜索」事件，便于前端稳定显示（不依赖 msg.type 命名）
                tool_calls = msg_dict.get("tool_calls") or []
                for tc in tool_calls:
                    name = (tc.get("name") or (tc.get("function") or {}).get("name") or "").lower()
                    if "tavily" in name:
                        args = tc.get("args") or (tc.get("function") or {}).get("arguments")
                        query = ""
                        if isinstance(args, dict):
                            query = args.get("query") or args.get("q") or ""
                        elif isinstance(args, str):
                            try:
                                p = json.loads(args)
                                query = p.get("query") or p.get("q") or ""
                            except Exception:
                                pass
                        yield make_chunk(
                            status="loading",
                            tool_calling={"name": "tavily_search", "query": query},
                            metadata=metadata,
                        )
                        break

                try:
                    if msg_dict.get("type") == "tool":
                        graph = await agent.get_graph()
                        state = await graph.aget_state(langgraph_config)
                        agent_state = extract_agent_state(getattr(state, "values", {})) if state else {}
                        if agent_state:
                            yield make_chunk(status="agent_state", agent_state=agent_state, meta=meta)
                except Exception as e:
                    logger.error(f"Error processing tool message: {e}")

        if not full_msg and accumulated_content:
            full_msg = AIMessage(content="".join(accumulated_content))

        if conf.enable_content_guard and hasattr(full_msg, "content") and await content_guard.check(full_msg.content):
            await save_partial_message(conv_repo, thread_id, full_msg, "content_guard_blocked")
            meta["time_cost"] = asyncio.get_event_loop().time() - start_time
            yield make_chunk(status="interrupted", message="检测到敏感内容，已中断输出", meta=meta)
            return

        async for chunk in check_and_handle_interrupts(agent, langgraph_config, make_chunk, meta, thread_id):
            yield chunk

        meta["time_cost"] = asyncio.get_event_loop().time() - start_time
        try:
            graph = await agent.get_graph()
            state = await graph.aget_state(langgraph_config)
            agent_state = extract_agent_state(getattr(state, "values", {})) if state else {}
        except Exception:
            agent_state = {}

        if agent_state:
            yield make_chunk(status="agent_state", agent_state=agent_state, meta=meta)

        yield make_chunk(status="finished", meta=meta)

        model_name = input_context.get("agent_config") and input_context["agent_config"].get("model")
        await save_messages_from_langgraph_state(
            agent_instance=agent,
            thread_id=thread_id,
            conv_repo=conv_repo,
            config_dict=langgraph_config,
            model_name=model_name or None,
        )

    except (asyncio.CancelledError, ConnectionError) as e:
        if isinstance(e, asyncio.CancelledError):
            logger.debug("Stream cancelled (client disconnect or worker shutdown): {}", e)
        else:
            logger.warning("Client connection error, ending stream: {}", e)

        async def save_cleanup():
            nonlocal full_msg
            if not full_msg and accumulated_content:
                full_msg = AIMessage(content="".join(accumulated_content))

            async with pg_manager.get_async_session_context() as new_db:
                new_conv_repo = ConversationRepository(new_db)
                await save_partial_message(
                    new_conv_repo,
                    thread_id,
                    full_msg=full_msg,
                    error_message="对话已中断" if not full_msg else None,
                    error_type="interrupted",
                )

        cleanup_task = asyncio.create_task(save_cleanup())
        try:
            await asyncio.shield(cleanup_task)
        except asyncio.CancelledError:
            pass
        except Exception as exc:
            logger.error(f"Error during cleanup save: {exc}")

        yield make_chunk(status="interrupted", message="对话已中断", meta=meta)

    except Exception as e:
        logger.error(f"Error streaming messages: {e}, {traceback.format_exc()}")

        error_msg = f"Error streaming messages: {e}"
        error_type = "unexpected_error"

        if not full_msg and accumulated_content:
            full_msg = AIMessage(content="".join(accumulated_content))

        async with pg_manager.get_async_session_context() as new_db:
            new_conv_repo = ConversationRepository(new_db)
            await save_partial_message(
                new_conv_repo,
                thread_id,
                full_msg=full_msg,
                error_message=error_msg,
                error_type=error_type,
            )

        yield make_chunk(status="error", error_type=error_type, error_message=error_msg, meta=meta)


async def stream_agent_resume(
    *,
    agent_id: str,
    thread_id: str,
    approved: bool,
    meta: dict,
    config: dict,
    current_user,
    db,
) -> AsyncIterator[bytes]:
    start_time = asyncio.get_event_loop().time()

    def make_resume_chunk(content=None, **kwargs):
        return (
            json.dumps(
                {"request_id": meta.get("request_id"), "response": content, **kwargs}, ensure_ascii=False
            ).encode("utf-8")
            + b"\n"
        )

    try:
        agent = agent_manager.get_agent(agent_id)
    except Exception as e:
        logger.error(f"Error getting agent {agent_id}: {e}, {traceback.format_exc()}")
        yield (
            f'{{"request_id": "{meta.get("request_id")}", "message": '
            f'"Error getting agent {agent_id}: {e}", "status": "error"}}\n'
        )
        return

    init_msg = {"type": "system", "content": f"Resume with approved: {approved}"}
    yield make_resume_chunk(status="init", meta=meta, msg=init_msg)

    resume_command = Command(resume=approved)
    graph = await agent.get_graph()

    user_id = str(current_user.id)
    department_id = current_user.department_id
    if not department_id:
        yield make_resume_chunk(
            status="error", error_type="no_department", error_message="当前用户未绑定部门", meta=meta
        )
        return

    agent_config_id = (config or {}).get("agent_config_id")
    config_repo = AgentConfigRepository(db)
    config_item = None
    if agent_config_id is not None:
        try:
            config_item = await config_repo.get_by_id(int(agent_config_id))
        except Exception:
            logger.warning(f"Failed to fetch agent config {agent_config_id}: {traceback.format_exc()}")
            config_item = None
        if config_item is not None and (config_item.department_id != department_id or config_item.agent_id != agent_id):
            config_item = None

    if config_item is None:
        config_item = await config_repo.get_or_create_default(
            department_id=department_id, agent_id=agent_id, created_by=user_id
        )
        agent_config_id = config_item.id

    input_context = {
        "user_id": user_id,
        "thread_id": thread_id,
        "department_id": department_id,
        "agent_config_id": agent_config_id,
        "agent_config": (config_item.config_json or {}).get("context", config_item.config_json or {}),
    }
    context = agent.context_schema()
    agent_config = input_context.get("agent_config")
    if isinstance(agent_config, dict):
        context.update(agent_config)
    context.update(input_context)

    stream_source = graph.astream(
        resume_command,
        context=context,
        config={"configurable": {"thread_id": thread_id, "user_id": user_id}},
        stream_mode="messages",
    )

    try:
        async for msg, metadata in stream_source:
            msg_dict = msg.model_dump()
            if "id" not in msg_dict:
                msg_dict["id"] = str(uuid.uuid4())

            yield make_resume_chunk(
                content=getattr(msg, "content", ""), msg=msg_dict, metadata=metadata, status="loading"
            )

        langgraph_config = {"configurable": {"thread_id": thread_id, "user_id": str(current_user.id)}}
        async for chunk in check_and_handle_interrupts(agent, langgraph_config, make_resume_chunk, meta, thread_id):
            yield chunk

        meta["time_cost"] = asyncio.get_event_loop().time() - start_time
        yield make_resume_chunk(status="finished", meta=meta)

        conv_repo = ConversationRepository(db)
        model_name = input_context.get("agent_config") and input_context["agent_config"].get("model")
        await save_messages_from_langgraph_state(
            agent_instance=agent,
            thread_id=thread_id,
            conv_repo=conv_repo,
            config_dict=langgraph_config,
            model_name=model_name or None,
        )

    except (asyncio.CancelledError, ConnectionError) as e:
        logger.warning(f"Client disconnected during resume: {e}")

        async with pg_manager.get_async_session_context() as new_db:
            new_conv_repo = ConversationRepository(new_db)
            await save_partial_message(
                new_conv_repo, thread_id, error_message="对话恢复已中断", error_type="resume_interrupted"
            )

        yield make_resume_chunk(status="interrupted", message="对话恢复已中断", meta=meta)

    except Exception as e:
        logger.error(f"Error during resume: {e}, {traceback.format_exc()}")

        async with pg_manager.get_async_session_context() as new_db:
            new_conv_repo = ConversationRepository(new_db)
            await save_partial_message(
                new_conv_repo, thread_id, error_message=f"Error during resume: {e}", error_type="resume_error"
            )

        yield make_resume_chunk(message=f"Error during resume: {e}", status="error")


async def get_agent_state_view(
    *,
    agent_id: str,
    thread_id: str,
    current_user_id: str,
    db,
) -> dict:
    if not agent_manager.get_agent(agent_id):
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail=f"智能体 {agent_id} 不存在")

    conv_repo = ConversationRepository(db)
    conversation = await conv_repo.get_conversation_by_thread_id(thread_id)
    if not conversation or conversation.user_id != str(current_user_id) or conversation.status == "deleted":
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="对话线程不存在")

    agent = agent_manager.get_agent(agent_id)
    graph = await agent.get_graph()
    langgraph_config = {"configurable": {"user_id": str(current_user_id), "thread_id": thread_id}}
    state = await graph.aget_state(langgraph_config)
    agent_state = extract_agent_state(getattr(state, "values", {})) if state else {}

    # 如果 state 中没有 files，从附件构建
    # 这确保了上传附件后立即可以在文件列表中看到文件
    if not agent_state.get("files") or agent_state["files"] == {}:
        try:
            attachments = await conv_repo.get_attachments_by_thread_id(thread_id)
            logger.info(f"[get_agent_state_view] found {len(attachments)} attachments in DB")
            if attachments:
                first_status = attachments[0].get("status")
                first_has_markdown = bool(attachments[0].get("markdown"))
                logger.info(
                    f"[get_agent_state_view] first attachment status: {first_status}, "
                    f"has markdown: {first_has_markdown}"
                )
                files = _build_state_files(attachments)
                agent_state["files"] = files
                logger.info(f"[get_agent_state_view] Built files from attachments: {len(files)} files")
        except Exception as e:
            logger.warning(f"Failed to fetch attachments for thread {thread_id}: {e}")

    return {"agent_state": agent_state}
