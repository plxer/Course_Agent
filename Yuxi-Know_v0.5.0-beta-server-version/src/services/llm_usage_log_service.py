"""将课程域非 LangGraph 的 LLM 调用写入 messages 表，供运维看板统计模型/智能体/Token。"""

from __future__ import annotations

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from src.repositories.conversation_repository import ConversationRepository
from src.utils import logger

# 与对话智能体区分，运维「智能体调用」时间序列中单独成类
COURSE_EXERCISE_AGENT_ID = "CourseExercise"
COURSE_RELEVANCE_AGENT_ID = "CourseRelevance"
COURSE_TRANSLATE_AGENT_ID = "CourseTranslate"


def extract_usage_from_lc_response(resp: Any) -> tuple[int, int]:
    """从 LangChain ChatModel 返回的 AIMessage 等对象解析 input/output token 数。"""
    if resp is None:
        return 0, 0
    inp = out = 0
    um = getattr(resp, "usage_metadata", None)
    if isinstance(um, dict):
        inp = int(um.get("input_tokens") or um.get("prompt_tokens") or 0)
        out = int(um.get("output_tokens") or um.get("completion_tokens") or 0)
    if inp or out:
        return inp, out
    rm = getattr(resp, "response_metadata", None) or {}
    if isinstance(rm, dict):
        tu = rm.get("token_usage")
        if isinstance(tu, dict):
            inp = int(tu.get("prompt_tokens") or tu.get("input_tokens") or 0)
            out = int(tu.get("completion_tokens") or tu.get("output_tokens") or 0)
    return inp, out


async def log_course_aux_llm_call(
    db: AsyncSession,
    *,
    user_int_id: int,
    agent_id: str,
    model_spec: str,
    content: str,
    input_tokens: int,
    output_tokens: int,
    source: str,
) -> None:
    """
    写入一条 assistant 消息，extra_metadata 结构与对话流一致，便于 dashboard 复用查询。
    """
    try:
        repo = ConversationRepository(db)
        user_str = str(user_int_id)
        thread_id = f"course_aux_{agent_id}_{user_str}"
        conv = await repo.get_conversation_by_thread_id(thread_id)
        if conv is None:
            conv = await repo.create_conversation(
                user_id=user_str,
                agent_id=agent_id,
                title="课程辅助 LLM 统计",
                thread_id=thread_id,
                metadata={"source": "course_aux_stats", "aux_agent": agent_id},
            )
        extra = {
            "response_metadata": {"model_name": model_spec},
            "usage_metadata": {
                "input_tokens": int(input_tokens or 0),
                "output_tokens": int(output_tokens or 0),
            },
            "course_aux_source": source,
        }
        preview = (content or "").strip()[:2000] or "(empty)"
        await repo.add_message(
            conv.id,
            role="assistant",
            content=preview,
            message_type="text",
            extra_metadata=extra,
        )
    except Exception as e:
        logger.warning("log_course_aux_llm_call failed (non-fatal): %s", e)
