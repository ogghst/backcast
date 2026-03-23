"""DeepAgentOrchestrator for LangChain Deep Agents SDK integration.

Wraps create_deep_agent() with:
- Temporal context injection (as_of, branch_name, branch_mode)
- RBAC and risk-based security filtering
- Subagent management with isolated contexts
- Tool registration from existing @ai_tool ecosystem
"""

import logging
from typing import Any

from deepagents import create_deep_agent
from deepagents.middleware.subagents import SubAgent
from langchain_core.language_models import BaseChatModel
from langchain_core.tools import BaseTool

from app.ai.middleware.backcast_security import BackcastSecurityMiddleware
from app.ai.middleware.temporal_context import TemporalContextMiddleware
from app.ai.subagents import get_all_subagents
from app.ai.tools import create_project_tools, filter_tools_by_execution_mode
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
    """Orchestrator for Deep Agents with Backcast context and security.

    This class wraps the Deep Agents SDK's create_deep_agent function with
    Backcast-specific configuration including temporal context, security middleware,
    and tool filtering.

    Attributes:
        model: Model string (e.g., 'openai:gpt-4o') or ChatOpenAI instance
        context: ToolContext with user permissions and temporal parameters
        system_prompt: Optional custom system prompt
        enable_subagents: Whether to enable subagent delegation (default: True)
    """

    def __init__(
        self,
        model: str | BaseChatModel,
        context: ToolContext,
        system_prompt: str | None = None,
        enable_subagents: bool = True,
    ) -> None:
        """Initialize DeepAgentOrchestrator.

        Args:
            model: Model string (e.g., 'openai:gpt-4o') or BaseChatModel instance
            context: ToolContext with user permissions and temporal parameters
            system_prompt: Optional custom system prompt
            enable_subagents: Whether to enable subagent delegation
        """
        self.model = model
        self.context = context
        self.system_prompt = system_prompt
        self.enable_subagents = enable_subagents

    def create_agent(
        self,
        allowed_tools: list[str] | None = None,
        subagents: list[dict[str, Any]] | None = None,
    ) -> Any:
        """Create a Deep Agent with Backcast tools and context.

        Args:
            allowed_tools: Optional list of tool names to include (filters all tools)
            subagents: Optional subagent configurations (uses default if None and enabled)

        Returns:
            Compiled Deep Agent graph (CompiledStateGraph)

        Example:
            >>> orchestrator = DeepAgentOrchestrator("openai:gpt-4o", context)
            >>> agent = orchestrator.create_agent()
            >>> result = await agent.ainvoke({"messages": [("user", "Hello")]})
        """
        # Get existing tools from @ai_tool ecosystem
        all_tools = create_project_tools(self.context)

        # Filter by allowed_tools if specified
        if allowed_tools is not None:
            all_tools = [t for t in all_tools if t.name in allowed_tools]

        # Filter by execution mode - this prevents LLM from seeing tools it can't use
        all_tools = filter_tools_by_execution_mode(all_tools, self.context.execution_mode)

        # When subagents are enabled, the main agent should NOT have direct access
        # to Backcast tools - it should only delegate via the "task" tool.
        # Subagents will have access to the actual tools.
        if self.enable_subagents:
            # Main agent only gets Deep Agents SDK built-in tools (write_todos, task)
            # These are added automatically by create_deep_agent()
            tools = []
            logger.info("Creating Deep Agent with subagents - main agent delegates only")
        else:
            # Without subagents, main agent needs direct tool access
            tools = all_tools
            logger.info(f"Creating Deep Agent with {len(tools)} tools (no subagents)")

        # Build context_schema for temporal parameters
        # Note: Deep Agents uses this for validation but actual injection happens in middleware
        context_schema = self._build_context_schema()

        # Configure interrupts for critical tools
        # These tools will pause execution for approval in standard mode
        interrupt_config = self._build_interrupt_config(tools) if not self.enable_subagents else {}

        # Create middleware stack with tools reference
        # Order matters: temporal first (logging), then security (checking)
        # Security middleware needs filtered_tools for permission checking
        middleware = [
            TemporalContextMiddleware(self.context),
            BackcastSecurityMiddleware(self.context, tools=all_tools),
        ]

        # Get subagents
        agent_subagents = None
        if self.enable_subagents:
            if subagents is None:
                # Convert dict configs to SubAgent objects
                # Pass all_tools so subagents can access Backcast tools
                agent_subagents = self._create_subagent_objects(
                    get_all_subagents(),
                    all_tools,  # Subagents need access to actual tools
                    allowed_tools=allowed_tools,
                )
            else:
                agent_subagents = self._create_subagent_objects(
                    subagents,
                    all_tools,  # Subagents need access to actual tools
                    allowed_tools=allowed_tools,
                )

        # Build system prompt with subagent delegation instructions
        base_prompt = self.system_prompt or DEFAULT_SYSTEM_PROMPT
        subagent_prompt_suffix = self._build_system_prompt_suffix()
        final_system_prompt = base_prompt + subagent_prompt_suffix

        # Create Deep Agent with Backcast configuration
        # Pass model string or ChatOpenAI instance directly to create_deep_agent
        agent = create_deep_agent(
            model=self.model,
            tools=tools,
            system_prompt=final_system_prompt,
            subagents=agent_subagents,  # type: ignore[arg-type]
            context_schema=context_schema,  # type: ignore[arg-type]
            interrupt_on=interrupt_config,  # type: ignore[arg-type]
            middleware=middleware,
            checkpointer=None,  # Use default checkpointer
        )

        # DEBUG: Log what tools the main agent actually has access to
        if logger.isEnabledFor(20):  # INFO level
            logger.info(f"DEBUG: Main agent created with tools={len(tools)} direct tools, enable_subagents={self.enable_subagents}")
            if agent_subagents:
                logger.info(f"DEBUG: Created {len(agent_subagents)} subagents with tools:")
                for sa in agent_subagents:
                    sa_tools = sa.get('tools', [])
                    logger.info(f"DEBUG:   - {sa.get('name')}: {len(sa_tools)} tools")

        logger.info("Deep Agent created successfully")
        return agent

    def _build_context_schema(self) -> dict[str, Any] | None:
        """Build context schema for temporal parameters.

        Returns:
            Dictionary defining temporal context schema or None

        Note:
            Deep Agents uses this for type validation. The actual injection
            happens in TemporalContextMiddleware.
        """
        return {
            "as_of": {
                "type": "string",
                "description": "Historical date for temporal queries (ISO format)",
            },
            "branch_name": {
                "type": "string",
                "description": "Branch name for temporal queries",
            },
            "branch_mode": {
                "type": "string",
                "description": "Branch mode: 'merged' or 'isolated'",
            },
            "project_id": {
                "type": "string",
                "description": "Project ID for project-scoped queries",
            },
            "execution_mode": {
                "type": "string",
                "description": "Execution mode: 'safe', 'standard', or 'expert'",
            },
        }

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
        for sa in self._create_subagent_objects(
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
                    tool_names.append(t.__name__ if hasattr(t, "__name__") else str(t))
            subagent_info.append(
                f"- {sa_name}: {', '.join(tool_names[:5])}"
                f"{'...' if len(tool_names) > 5 else ''}"
            )

        return f"""
IMPORTANT: You do NOT have direct access to Backcast tools.
ALL Backcast operations must be delegated to specialized subagents:

Available Subagents:
{chr(10).join(subagent_info)}

When a user asks for Backcast-related operations, you MUST use the task tool to delegate to the appropriate subagent. The task result will contain the information the user needs.

Do NOT attempt to use Backcast tools directly - they will not work. Always delegate via the task tool.
"""

    def _build_interrupt_config(self, tools: list[BaseTool]) -> dict[str, bool]:
        """Build interrupt configuration for critical tools.

        Args:
            tools: List of tools to check for critical risk level

        Returns:
            Dictionary mapping critical tool names to True
        """
        critical_tools = {}
        for tool in tools:
            metadata = getattr(tool, "_tool_metadata", None)
            if metadata and metadata.risk_level.value == "critical":
                critical_tools[tool.name] = True
                logger.debug(f"Tool '{tool.name}' marked for interrupt (critical)")
        return critical_tools

    def _create_subagent_objects(
        self,
        subagent_configs: list[dict[str, Any]],
        available_tools: list[BaseTool],
        allowed_tools: list[str] | None = None,
    ) -> list[SubAgent]:
        """Convert subagent configuration dicts to SubAgent objects.

        Args:
            subagent_configs: List of subagent configuration dictionaries
            available_tools: List of all available tools for filtering
            allowed_tools: Optional whitelist of tool names from the assistant config

        Returns:
            List of SubAgent objects

        Note:
            Subagent tools are filtered in two stages:
            1. By the subagent's own allowed_tools list
            2. By the assistant's allowed_tools whitelist (if provided)
            This ensures subagents can only access tools that the assistant is allowed to use.
        """
        subagent_objects = []

        for config in subagent_configs:
            name = config.get("name", "")
            description = config.get("description", "")
            system_prompt = config.get("system_prompt", "")
            allowed_tool_names = config.get("allowed_tools", [])

            # Filter tools by subagent's allowed_tool_names AND assistant's allowed_tools whitelist
            # This ensures subagents respect the assistant's tool restrictions
            if allowed_tools is not None:
                # Intersection of subagent tools and assistant whitelist
                filtered_tool_names = [
                    tool_name for tool_name in allowed_tool_names
                    if tool_name in allowed_tools
                ]
                logger.debug(
                    f"Subagent '{name}': filtered {len(filtered_tool_names)} tools "
                    f"(from {len(allowed_tool_names)} requested) based on assistant whitelist"
                )
            else:
                # No assistant whitelist, use subagent's full list
                filtered_tool_names = allowed_tool_names

            # Filter tools by the filtered tool names
            subagent_tools = [t for t in available_tools if t.name in filtered_tool_names]

            if subagent_tools:
                subagent = SubAgent(
                    name=name,
                    description=description,
                    system_prompt=system_prompt,
                    tools=subagent_tools,
                )
                subagent_objects.append(subagent)
                logger.info(
                    f"Created subagent '{name}' with {len(subagent_tools)} tools"
                )
            else:
                logger.warning(
                    f"Subagent '{name}' has no valid tools after filtering - skipping"
                )

        return subagent_objects


__all__ = ["DeepAgentOrchestrator"]
