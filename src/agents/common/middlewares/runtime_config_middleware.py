from __future__ import annotations

from collections.abc import Callable
from typing import Any

from langchain.agents.middleware import AgentMiddleware, ModelRequest, ModelResponse
from langchain_core.messages import SystemMessage

from src.agents.common import load_chat_model
from src.agents.common.tools import get_buildin_tools, get_kb_based_tools, get_tavily_search
from src.services.mcp_service import get_enabled_mcp_tools
from src.utils.datetime_utils import shanghai_now
from src.utils.logging_config import logger


class RuntimeConfigMiddleware(AgentMiddleware):
    """运行时配置中间件 - 应用模型/工具/知识库/MCP/提示词配置

    注意：所有可能用到的知识库工具必须在初始化时预加载并注册到 self.tools
    运行时根据配置从 self.tools 中筛选工具，不能动态添加新工具

    支持自定义上下文字段名称，以便在不同场景（如主智能体/子智能体）使用不同的配置字段
    """

    def __init__(
        self,
        *,
        extra_tools: list[Any] | None = None,
        model_context_name: str = "model",
        system_prompt_context_name: str = "system_prompt",
        tools_context_name: str = "tools",
        knowledges_context_name: str = "knowledges",
        mcps_context_name: str = "mcps",
        enable_model_override: bool = True,
        enable_system_prompt_override: bool = True,
        enable_tools_override: bool = True,
    ):
        """初始化中间件

        Args:
            extra_tools: 额外工具列表（从 create_agent 的 tools 参数传入）
            model_context_name: 上下文中的模型字段名称（默认 "model"）
            system_prompt_context_name: 上下文中的系统提示词字段名称（默认 "system_prompt"）
            tools_context_name: 上下文中的工具列表字段名称（默认 "tools"）
            knowledges_context_name: 上下文中的知识库列表字段名称（默认 "knowledges"）
            mcps_context_name: 上下文中的 MCP 服务器列表字段名称（默认 "mcps"）
            enable_model_override: 是否允许覆盖模型配置（默认 True）
            enable_system_prompt_override: 是否允许覆盖系统提示词（默认 True）
            enable_tools_override: 是否允许覆盖工具列表（默认 True）
        """
        super().__init__()
        # 存储自定义字段名称
        self.model_context_name = model_context_name
        self.system_prompt_context_name = system_prompt_context_name
        self.tools_context_name = tools_context_name
        self.knowledges_context_name = knowledges_context_name
        self.mcps_context_name = mcps_context_name
        # 存储覆盖配置
        self.enable_model_override = enable_model_override
        self.enable_system_prompt_override = enable_system_prompt_override
        self.enable_tools_override = enable_tools_override

        self.tools: list[Any] = []
        # 预加载工具列表（仅当启用工具覆盖时）
        if self.enable_tools_override:
            self.kb_tools = get_kb_based_tools()
            self.buildin_tools = get_buildin_tools()
            self.tools = self.kb_tools + self.buildin_tools + (extra_tools or [])
        elif extra_tools:
            logger.warning(
                "RuntimeConfigMiddleware: extra_tools 参数已提供，但 enable_tools_override=False，"
                "将忽略 extra_tools 并不会应用任何工具覆盖。"
            )

        logger.debug(
            f"Initialized RuntimeConfigMiddleware with custom field names: model={model_context_name}, "
            f"system_prompt={system_prompt_context_name}, tools={tools_context_name}, "
            f"knowledges={knowledges_context_name}, mcps={mcps_context_name}"
        )

    async def awrap_model_call(
        self, request: ModelRequest, handler: Callable[[ModelRequest], ModelResponse]
    ) -> ModelResponse:
        runtime_context = request.runtime.context
        overrides: dict[str, Any] = {}

        # 1. 模型覆盖（可选）
        if self.enable_model_override:
            model = load_chat_model(getattr(runtime_context, self.model_context_name, None))
            overrides["model"] = model

        # 2. 工具覆盖（可选）：直接使用 enabled_tools，确保 enable_web_search 等运行时开关生效
        # （若只过滤 request.tools，当 initial default_tools 未包含 Tavily 时无法加入）
        if self.enable_tools_override:
            enabled_tools = await self.get_tools_from_context(runtime_context)
            overrides["tools"] = enabled_tools
            enable_web = getattr(runtime_context, "enable_web_search", False)
            logger.info(
                f"RuntimeConfigMiddleware tools: enable_web_search={enable_web}, "
                f"count={len(enabled_tools)}, names={[t.name for t in enabled_tools]}"
            )

        # 3. 系统提示词覆盖（可选）
        if self.enable_system_prompt_override:
            cur_datetime = f"当前时间：{shanghai_now().strftime('%Y-%m-%d %H:%M:%S')} UTC"
            system_prompt = getattr(runtime_context, self.system_prompt_context_name, "") or ""
            extra = f"{cur_datetime}\n\n{system_prompt}"
            tool_use_instruction = getattr(runtime_context, "tool_use_instruction", "") or ""
            if tool_use_instruction and isinstance(tool_use_instruction, str):
                extra = f"{extra}\n\n{tool_use_instruction}"
            new_content = list(request.system_message.content_blocks) + [{"type": "text", "text": extra}]
            new_system_message = SystemMessage(content=new_content)
            overrides["system_message"] = new_system_message

        if overrides:
            request = request.override(**overrides)

        return await handler(request)

    async def get_tools_from_context(self, context) -> list:
        """从上下文配置中获取工具列表"""
        selected_tools = []

        # 1. 基础工具 (从 context.tools 中筛选)
        tools = getattr(context, self.tools_context_name, None)
        if tools:
            tools_map = {t.name: t for t in self.tools}
            for tool_name in tools:
                if tool_name in tools_map:
                    selected_tools.append(tools_map[tool_name])

        # 2. 知识库工具
        knowledges = getattr(context, self.knowledges_context_name, None)
        if knowledges:
            kb_tools = get_kb_based_tools(db_names=knowledges)
            selected_tools.extend(kb_tools)

        # 3. MCP 工具（使用统一入口，自动过滤 disabled_tools）
        mcps = getattr(context, self.mcps_context_name, None)
        if mcps:
            for server_name in mcps:
                mcp_tools = await get_enabled_mcp_tools(server_name)
                selected_tools.extend(mcp_tools)

        # 4. 网络搜索工具（用户/会话级开关，仅当全局已启用时可用）
        if getattr(context, "enable_web_search", False):
            tavily = get_tavily_search()
            if tavily is not None:
                selected_tools.append(tavily)
        else:
            # 预检索完成后会关掉开关：同时去掉默认工具列表里的 Tavily，避免生成阶段再搜
            selected_tools = [t for t in selected_tools if "tavily" not in (getattr(t, "name", "") or "").lower()]

        return selected_tools
