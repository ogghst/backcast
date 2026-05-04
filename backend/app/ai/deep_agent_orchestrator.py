"""DeepAgentOrchestrator for LangChain agent integration.

Wraps langchain.agents.create_agent() with:
- Temporal context injection (as_of, branch_name, branch_mode)
- RBAC and risk-based security filtering
- Subagent management with isolated contexts via custom task tool
- Tool registration from existing @ai_tool ecosystem
"""

import logging
from typing import Any

from langchain.agents import create_agent as langchain_create_agent
from langchain.agents.middleware import TodoListMiddleware
from langchain_core.language_models import BaseChatModel
from langchain_core.tools import BaseTool

from app.ai.config import AgentConfig
from app.ai.subagent_compiler import (
    DEFAULT_SYSTEM_PROMPT,
    build_backcast_middleware,
    compile_subagents,
    filter_tools_for_context,
)
from app.ai.subagents import get_all_subagents
from app.ai.tools.subagent_task import TASK_SYSTEM_PROMPT, build_task_tool
from app.ai.tools.types import ToolContext

logger = logging.getLogger(__name__)


class DeepAgentOrchestrator:
    """Orchestrator for LangChain agents with Backcast context and security.

    This class wraps langchain.agents.create_agent() with Backcast-specific
    configuration including temporal context, security middleware, and
    subagent tool delegation.

    Attributes:
        model: Model string (e.g., 'openai:gpt-4o') or ChatOpenAI instance
        context: ToolContext with user permissions and temporal parameters
        system_prompt: Optional custom system prompt
        enable_subagents: Whether to enable subagent delegation (default: True)
        interrupt_node: Optional InterruptNode for handling approvals
    """

    def __init__(
        self,
        model: str | BaseChatModel,
        context: ToolContext,
        system_prompt: str | None = None,
        enable_subagents: bool = True,
        interrupt_node: Any = None,
    ) -> None:
        """Initialize DeepAgentOrchestrator.

        Args:
            model: Model string (e.g., 'openai:gpt-4o') or BaseChatModel instance
            context: ToolContext with user permissions and temporal parameters
            system_prompt: Optional custom system prompt
            enable_subagents: Whether to enable subagent delegation
            interrupt_node: Optional InterruptNode for handling approvals
        """
        self.model = model
        self.context = context
        self.system_prompt = system_prompt
        self.enable_subagents = enable_subagents
        self.interrupt_node = interrupt_node

    def create_agent(self, config: AgentConfig | None = None) -> Any:
        """Create a LangChain agent with Backcast tools and context.

        Args:
            config: Optional AgentConfig encapsulating creation parameters.

        Returns:
            Compiled agent graph (CompiledStateGraph)
        """
        if config is None:
            config = AgentConfig()

        logger.info(
            "[AGENT_CREATION_START] create_agent | "
            "model=%s | enable_subagents=%s | execution_mode=%s",
            self.model,
            self.enable_subagents,
            self.context.execution_mode.value,
        )

        all_tools = filter_tools_for_context(self.context, config)

        backcast_middleware = build_backcast_middleware(self.context, all_tools)

        base_prompt = self.system_prompt or DEFAULT_SYSTEM_PROMPT

        compiled_subagents: list[dict[str, Any]] | None = None

        if self.enable_subagents:
            subagent_configs = (
                config.subagents
                if config.subagents is not None
                else get_all_subagents()
            )
            compiled_subagents = compile_subagents(
                self.model,
                self.context,
                subagent_configs,
                all_tools,
                allowed_tools=config.allowed_tools,
            )

            if compiled_subagents:
                subagent_prompt_suffix = self._build_system_prompt_suffix(
                    compiled_subagents
                )
                task_tool = build_task_tool(compiled_subagents)
                temporal_context_tool = next(
                    (t for t in all_tools if t.name == "get_temporal_context"), None
                )
                tools: list[BaseTool] = [task_tool]
                if temporal_context_tool:
                    tools.append(temporal_context_tool)
                final_system_prompt = (
                    base_prompt + TASK_SYSTEM_PROMPT + subagent_prompt_suffix
                )
                middleware = [TodoListMiddleware(), *backcast_middleware]
                logger.info(
                    f"Creating agent with subagents - "
                    f"main agent delegates via task tool, "
                    f"{len(compiled_subagents)} subagents compiled"
                )
            else:
                tools = all_tools
                final_system_prompt = base_prompt
                middleware = list(backcast_middleware)
                logger.info(
                    "No valid subagents after filtering - "
                    "falling back to direct tools mode"
                )
        else:
            tools = all_tools
            final_system_prompt = base_prompt
            middleware = list(backcast_middleware)
            logger.info(f"Creating agent with {len(tools)} tools (subagents disabled)")

        # Create the agent via langchain.agents.create_agent()
        agent = langchain_create_agent(
            model=self.model,
            tools=tools,
            system_prompt=final_system_prompt,
            middleware=middleware,  # type: ignore[arg-type]
            checkpointer=config.checkpointer,
            context_schema=config.context_schema,
        )

        if logger.isEnabledFor(20):  # INFO level
            logger.info(
                "Main agent created with %d tools, enable_subagents=%s",
                len(tools),
                self.enable_subagents,
            )
            if compiled_subagents:
                for sa in compiled_subagents:
                    logger.info(
                        "  - %s: %d tools",
                        sa.get("name"),
                        len(sa.get("tools", [])),
                    )

        logger.info("Agent created successfully")
        return agent

    def _build_system_prompt_suffix(
        self, subagent_dicts: list[dict[str, Any]] | None = None
    ) -> str:
        """Build system prompt suffix for subagent-only access.

        When subagents are enabled, the main agent MUST delegate all
        Backcast operations to subagents. The main agent has NO direct
        access to Backcast tools.

        Args:
            subagent_dicts: Pre-built subagent dicts (each has a "tools" key).
                When None or empty, returns an empty string.

        Returns:
            System prompt suffix with subagent delegation instructions
        """
        if not subagent_dicts:
            return ""

        subagent_info = []
        for sa in subagent_dicts:
            sa_name = sa.get("name", "")
            tool_names = [t.name for t in sa.get("tools", [])]
            subagent_info.append(
                f"- {sa_name}: {', '.join(tool_names[:5])}"
                f"{'...' if len(tool_names) > 5 else ''}"
            )

        return f"""
IMPORTANT: You do NOT have direct access to Backcast tools.
ALL Backcast operations must be delegated to specialized subagents:

Available Subagents:
{chr(10).join(subagent_info)}

When a user asks for Backcast-related operations, you MUST use the task tool to delegate to the appropriate subagent.

After the subagent completes, provide a brief, helpful synthesis that:
1. Acknowledges what was accomplished (1-2 sentences)
2. Highlights the most important findings or actions taken
3. DO NOT repeat the entire detailed output
4. Offers relevant next steps or asks if the user needs clarification

Example good responses:
- "I've analyzed the project's EVM metrics. The key finding is a CPI of 0.95, indicating the project is slightly over budget."
- "I've created the new project 'Assembly Line B' with a budget of $500,000."
- "The forecast has been generated. Current projections show a 5% cost variance by Q3. Would you like me to explore mitigation strategies?"

Do NOT attempt to use Backcast tools directly - they will not work. Always delegate via the task tool.
"""


__all__ = ["AgentConfig", "DeepAgentOrchestrator"]
