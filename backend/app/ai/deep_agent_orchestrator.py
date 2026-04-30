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
from app.ai.middleware.backcast_security import BackcastSecurityMiddleware
from app.ai.middleware.temporal_context import TemporalContextMiddleware
from app.ai.subagent_compiler import DEFAULT_SYSTEM_PROMPT, compile_subagents
from app.ai.subagents import get_all_subagents
from app.ai.tools import (
    create_project_tools,
    filter_tools_by_execution_mode,
    filter_tools_by_role,
)
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

        Routing priority:
        1. ``config.use_supervisor`` -> :class:`SupervisorOrchestrator`
        2. Default -> traditional subagent-as-tool graph

        Args:
            config: Optional AgentConfig encapsulating creation parameters.
                When None, defaults are used (no tool whitelist, no subagent
                overrides, no checkpointer, no context schema, no role filtering).

        Returns:
            Compiled agent graph (CompiledStateGraph)

        Example:
            >>> config = AgentConfig(checkpointer=shared_checkpointer)
            >>> orchestrator = DeepAgentOrchestrator("openai:gpt-4o", context)
            >>> agent = orchestrator.create_agent(config)
            >>> result = await agent.ainvoke({"messages": [("user", "Hello")]})
        """
        if config is None:
            config = AgentConfig()

        # Delegate to supervisor orchestrator when flag is set
        if config.use_supervisor:
            from app.ai.supervisor_orchestrator import SupervisorOrchestrator

            supervisor = SupervisorOrchestrator(
                model=self.model,
                context=self.context,
                system_prompt=self.system_prompt,
            )
            return supervisor.create_supervisor_graph(config)

        allowed_tools = config.allowed_tools
        subagents = config.subagents
        checkpointer = config.checkpointer
        context_schema = config.context_schema
        assistant_role = config.assistant_role
        user_role = config.user_role
        # Log agent creation start
        logger.info(
            f"[AGENT_CREATION_START] create_agent | "
            f"model={self.model} | "
            f"enable_subagents={self.enable_subagents} | "
            f"system_prompt_length={len(self.system_prompt) if self.system_prompt else 0} | "
            f"user_role={self.context.user_role} | "
            f"execution_mode={self.context.execution_mode.value}"
        )

        # Get existing tools from @ai_tool ecosystem
        all_tools = create_project_tools(self.context)

        # Filter by allowed_tools if specified
        if allowed_tools is not None:
            all_tools = [t for t in all_tools if t.name in allowed_tools]

        # Log tool filtering
        original_tool_count = len(all_tools)
        # Filter by execution mode - this prevents LLM from seeing tools it can't use
        all_tools = filter_tools_by_execution_mode(
            all_tools, self.context.execution_mode
        )
        filtered_tool_count = len(all_tools)
        logger.info(
            f"[TOOL_FILTERING] create_agent | "
            f"execution_mode={self.context.execution_mode.value} | "
            f"original_tool_count={original_tool_count} | "
            f"filtered_tool_count={filtered_tool_count} | "
            f"removed_count={original_tool_count - filtered_tool_count}"
        )

        # Filter by assistant RBAC role if specified
        if assistant_role is not None:
            pre_role_count = len(all_tools)
            all_tools = filter_tools_by_role(all_tools, assistant_role)
            logger.info(
                f"[TOOL_ROLE_FILTERING] create_agent | "
                f"assistant_role={assistant_role} | "
                f"pre_filter_count={pre_role_count} | "
                f"post_filter_count={len(all_tools)} | "
                f"removed_count={pre_role_count - len(all_tools)}"
            )

        # Filter by user's actual role (per-user restriction)
        if user_role is not None:
            pre_user_count = len(all_tools)
            all_tools = filter_tools_by_role(all_tools, user_role)
            logger.info(
                f"[TOOL_USER_ROLE_FILTERING] create_agent | "
                f"user_role={user_role} | "
                f"pre_filter_count={pre_user_count} | "
                f"post_filter_count={len(all_tools)} | "
                f"removed_count={pre_user_count - len(all_tools)}"
            )

        # Build Backcast middleware stack (shared between main agent and subagents)
        backcast_middleware = [
            TemporalContextMiddleware(self.context),
            BackcastSecurityMiddleware(
                self.context,
                tools=all_tools,
                interrupt_node=None,  # Per-request InterruptNode set via ContextVar at invocation time
            ),
        ]

        # Build system prompt
        base_prompt = self.system_prompt or DEFAULT_SYSTEM_PROMPT

        # Track compiled subagents (built once, reused for prompt + task tool + logging)
        compiled_subagents: list[dict[str, Any]] | None = None

        if self.enable_subagents:
            # Build subagent compiled graphs — SINGLE compilation
            subagent_configs = (
                subagents if subagents is not None else get_all_subagents()
            )
            compiled_subagents = compile_subagents(
                self.model,
                self.context,
                subagent_configs,
                all_tools,
                allowed_tools=allowed_tools,
            )

            if compiled_subagents:
                # Build prompt suffix from already-compiled dicts (no recompilation)
                subagent_prompt_suffix = self._build_system_prompt_suffix(
                    compiled_subagents
                )
                # Main agent delegates via task tool, but also gets get_temporal_context
                # for direct access to temporal context information (LOW risk, read-only)
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
                # Fallback: no valid subagents, use direct tools mode
                tools = all_tools
                final_system_prompt = base_prompt
                middleware = list(backcast_middleware)
                logger.info(
                    "No valid subagents after filtering - "
                    "falling back to direct tools mode"
                )
        else:
            # Without subagents, main agent needs direct tool access
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
            checkpointer=checkpointer,
            context_schema=context_schema,
        )

        # DEBUG: Log what the main agent has access to (uses already-compiled dicts)
        if logger.isEnabledFor(20):  # INFO level
            logger.info(
                f"DEBUG: Main agent created with {len(tools)} tools, "
                f"enable_subagents={self.enable_subagents}"
            )
            if compiled_subagents:
                logger.info(
                    f"DEBUG: Created {len(compiled_subagents)} subagents with tools:"
                )
                for sa in compiled_subagents:
                    sa_tools = sa.get("tools", [])
                    logger.info(f"DEBUG:   - {sa.get('name')}: {len(sa_tools)} tools")

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
