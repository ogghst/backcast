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

from app.ai.middleware.backcast_security import BackcastSecurityMiddleware
from app.ai.middleware.temporal_context import TemporalContextMiddleware
from app.ai.subagents import get_all_subagents
from app.ai.tools import create_project_tools, filter_tools_by_execution_mode
from app.ai.tools.subagent_task import TASK_SYSTEM_PROMPT, build_task_tool
from app.ai.tools.types import ToolContext

logger = logging.getLogger(__name__)

# Default system prompt (fallback when no custom prompt is provided)
DEFAULT_SYSTEM_PROMPT = """You are a helpful AI assistant for the Backcast project budget management system.

You can help with:
- Listing and viewing projects
- Getting detailed project information
- Earned value management calculations

When providing information:
- Be accurate and rely on the project data
- Use three-letter codes for project status (e.g., "ACT" for active, "PLN" for planned)
- Present data in clear, structured formats
- Only use tools you have been explicitly enabled for the assistant

When using tools:
- Always use the exact field names expected by the tools
- For status filters, use three-letter codes like 'ACT', 'PLN', 'CLS'
"""


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

    def create_agent(
        self,
        allowed_tools: list[str] | None = None,
        subagents: list[dict[str, Any]] | None = None,
        checkpointer: Any | None = None,
        context_schema: type | None = None,
    ) -> Any:
        """Create a LangChain agent with Backcast tools and context.

        Args:
            allowed_tools: Optional list of tool names to include (filters all tools)
            subagents: Optional subagent configurations (uses default if None and enabled)
            checkpointer: Optional shared checkpointer for graph state persistence
            context_schema: Optional context schema for StateGraph construction

        Returns:
            Compiled agent graph (CompiledStateGraph)

        Example:
            >>> orchestrator = DeepAgentOrchestrator("openai:gpt-4o", context)
            >>> agent = orchestrator.create_agent()
            >>> result = await agent.ainvoke({"messages": [("user", "Hello")]})
        """
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
        all_tools = filter_tools_by_execution_mode(all_tools, self.context.execution_mode)
        filtered_tool_count = len(all_tools)
        logger.info(
            f"[TOOL_FILTERING] create_agent | "
            f"execution_mode={self.context.execution_mode.value} | "
            f"original_tool_count={original_tool_count} | "
            f"filtered_tool_count={filtered_tool_count} | "
            f"removed_count={original_tool_count - filtered_tool_count}"
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
        subagent_prompt_suffix = self._build_system_prompt_suffix()

        if self.enable_subagents:
            # Build subagent compiled graphs and the task tool
            subagent_configs = subagents if subagents is not None else get_all_subagents()
            subagent_dicts = self._build_subagent_dicts(
                subagent_configs,
                all_tools,
                allowed_tools=allowed_tools,
            )

            if subagent_dicts:
                # Main agent delegates via task tool, but also gets get_temporal_context
                # for direct access to temporal context information (LOW risk, read-only)
                task_tool = build_task_tool(subagent_dicts)
                temporal_context_tool = next((t for t in all_tools if t.name == "get_temporal_context"), None)
                tools: list[BaseTool] = [task_tool]
                if temporal_context_tool:
                    tools.append(temporal_context_tool)
                final_system_prompt = base_prompt + TASK_SYSTEM_PROMPT + subagent_prompt_suffix
                middleware = [TodoListMiddleware(), *backcast_middleware]
                logger.info(
                    f"Creating agent with subagents - "
                    f"main agent delegates via task tool, "
                    f"{len(subagent_dicts)} subagents compiled"
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
            logger.info(
                f"Creating agent with {len(tools)} tools (subagents disabled)"
            )

        # Create the agent via langchain.agents.create_agent()
        agent = langchain_create_agent(
            model=self.model,
            tools=tools,
            system_prompt=final_system_prompt,
            middleware=middleware,  # type: ignore[arg-type]
            checkpointer=checkpointer,
            context_schema=context_schema,
        )

        # DEBUG: Log what the main agent has access to
        if logger.isEnabledFor(20):  # INFO level
            logger.info(
                f"DEBUG: Main agent created with {len(tools)} tools, "
                f"enable_subagents={self.enable_subagents}"
            )
            if self.enable_subagents:
                subagent_configs = subagents if subagents is not None else get_all_subagents()
                subagent_dicts_debug = self._build_subagent_dicts(
                    subagent_configs,
                    all_tools,
                    allowed_tools=allowed_tools,
                )
                if subagent_dicts_debug:
                    logger.info(
                        f"DEBUG: Created {len(subagent_dicts_debug)} subagents with tools:"
                    )
                    for sa in subagent_dicts_debug:
                        sa_tools = sa.get("tools", [])
                        logger.info(
                            f"DEBUG:   - {sa.get('name')}: {len(sa_tools)} tools"
                        )

        logger.info("Agent created successfully")
        return agent

    def _build_system_prompt_suffix(self) -> str:
        """Build system prompt suffix for subagent-only access.

        When subagents are enabled, the main agent MUST delegate all
        Backcast operations to subagents. The main agent has NO direct
        access to Backcast tools.

        Returns:
            System prompt suffix with subagent delegation instructions
        """
        if not self.enable_subagents:
            return ""

        # Get subagent info for the prompt
        subagent_info = []
        for sa in self._build_subagent_dicts(
            get_all_subagents(),
            create_project_tools(self.context),
            allowed_tools=None,  # Get full tool lists for descriptions
        ):
            sa_name = sa.get("name", "")
            sa_tools = sa.get("tools", [])
            # Get tool names safely - tools can be BaseTool, callable, or dict
            tool_names = []
            for t in sa_tools:
                if hasattr(t, "name"):
                    tool_names.append(t.name)
                elif isinstance(t, dict):
                    tool_names.append(t.get("name", str(t)))
                else:
                    # Callable - use function name
                    tool_names.append(
                        t.__name__ if hasattr(t, "__name__") else str(t)
                    )
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

    def _build_subagent_dicts(
        self,
        subagent_configs: list[dict[str, Any]],
        available_tools: list[BaseTool],
        allowed_tools: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        """Compile subagent configuration dicts into runnable graphs.

        Each subagent is compiled via langchain.agents.create_agent() with
        Backcast middleware (TemporalContextMiddleware + BackcastSecurityMiddleware)
        but without TodoListMiddleware (only the main agent needs planning).

        Args:
            subagent_configs: List of subagent configuration dictionaries
            available_tools: List of all available tools for filtering
            allowed_tools: Optional whitelist of tool names from the assistant config

        Returns:
            List of dicts with 'name', 'description', and 'runnable' keys
        """
        subagent_dicts: list[dict[str, Any]] = []

        # Build Backcast middleware for subagents
        subagent_middleware = [
            TemporalContextMiddleware(self.context),
            BackcastSecurityMiddleware(
                self.context,
                tools=available_tools,
                interrupt_node=None,  # Per-request InterruptNode set via ContextVar at invocation time
            ),
        ]

        for config in subagent_configs:
            name = config.get("name", "")
            description = config.get("description", "")
            system_prompt = config.get("system_prompt", "")
            allowed_tool_names = config.get("allowed_tools", [])

            # Filter tools by subagent's allowed_tool_names AND assistant's whitelist
            if allowed_tools is not None:
                filtered_tool_names = [
                    tool_name
                    for tool_name in allowed_tool_names
                    if tool_name in allowed_tools
                ]
                logger.debug(
                    f"Subagent '{name}': filtered {len(filtered_tool_names)} tools "
                    f"(from {len(allowed_tool_names)} requested) based on assistant whitelist"
                )
            else:
                filtered_tool_names = allowed_tool_names

            # Filter tools by the filtered tool names
            subagent_tools = [t for t in available_tools if t.name in filtered_tool_names]

            if not subagent_tools:
                logger.warning(
                    f"Subagent '{name}' has no valid tools after filtering - skipping"
                )
                continue

            # Compile the subagent into a runnable graph
            runnable = langchain_create_agent(
                model=self.model,
                tools=subagent_tools,
                system_prompt=system_prompt,
                middleware=subagent_middleware,
            )

            schema = config.get("structured_output_schema")

            subagent_dicts.append({
                "name": name,
                "description": description,
                "runnable": runnable,
                "structured_output_schema": schema,
            })
            logger.info(
                f"Compiled subagent '{name}' with {len(subagent_tools)} tools"
            )

        return subagent_dicts


__all__ = ["DeepAgentOrchestrator"]
