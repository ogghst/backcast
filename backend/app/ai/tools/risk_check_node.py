"""RiskCheckNode for execution mode-based tool filtering.

Provides LangGraph node that filters tools based on execution mode and risk level.
Integrates with RBACToolNode to ensure both permission and risk checks pass.
"""

from langchain_core.tools import BaseTool
from langgraph.prebuilt import ToolNode

from app.ai.tools.types import ExecutionMode, RiskLevel, ToolContext


class RiskCheckNode(ToolNode):
    """ToolNode subclass with risk-based filtering.

    Extends LangGraph's ToolNode to filter tools based on execution mode:
    - SAFE mode: Only low-risk tools
    - STANDARD mode: Low and high-risk tools (critical requires approval)
    - EXPERT mode: All tools

    Attributes:
        tools: List of tools available for execution
        context: ToolContext containing execution_mode for filtering

    Example:
        ```python
        from app.ai.tools import create_project_tools
        from app.ai.tools.risk_check_node import RiskCheckNode

        context = ToolContext(session, user_id, execution_mode=ExecutionMode.SAFE)
        tools = create_project_tools(context)
        tool_node = RiskCheckNode(tools, context)

        # Add to StateGraph
        workflow.add_node("tools", tool_node)
        ```
    """

    def __init__(
        self,
        tools: list[BaseTool],
        context: ToolContext,
    ) -> None:
        """Initialize RiskCheckNode with tools and context.

        Args:
            tools: List of BaseTool instances to execute
            context: ToolContext with execution_mode for filtering
        """
        # Filter tools based on execution mode
        filtered_tools = self._filter_tools_by_mode(tools, context.execution_mode)

        # Initialize parent ToolNode with filtered tools
        super().__init__(filtered_tools)
        self.context = context
        self.all_tools = tools  # Keep all tools for reference

    def _filter_tools_by_mode(
        self,
        tools: list[BaseTool],
        mode: ExecutionMode,
    ) -> list[BaseTool]:
        """Filter tools based on execution mode.

        Args:
            tools: List of tools to filter
            mode: Execution mode for filtering

        Returns:
            Filtered list of tools
        """
        filtered = []

        for tool in tools:
            # Get tool metadata
            metadata = getattr(tool, "_tool_metadata", None)
            if metadata is None:
                # No metadata means no risk level - assume high (safe default)
                risk_level = RiskLevel.HIGH
            else:
                risk_level = metadata.risk_level

            # Apply filtering rules
            if mode == ExecutionMode.SAFE:
                # Safe mode: Only low-risk tools
                if risk_level == RiskLevel.LOW:
                    filtered.append(tool)
            elif mode == ExecutionMode.STANDARD:
                # Standard mode: Low and high-risk tools (critical requires approval)
                if risk_level in [RiskLevel.LOW, RiskLevel.HIGH]:
                    filtered.append(tool)
                # Critical tools are NOT included - they require approval workflow
                # This will be handled in Phase 3 (InterruptNode)
            elif mode == ExecutionMode.EXPERT:
                # Expert mode: All tools
                filtered.append(tool)

        return filtered

    def check_tool_risk(
        self,
        tool_name: str,
    ) -> tuple[bool, str | None]:
        """Check if a tool is allowed based on execution mode.

        Args:
            tool_name: Name of the tool to check

        Returns:
            Tuple of (allowed, error_message)
            - allowed: True if tool can be executed, False otherwise
            - error_message: Error message if not allowed, None otherwise
        """
        # Find the tool by name
        tool = None
        for t in self.all_tools:
            if t.name == tool_name:
                tool = t
                break

        if tool is None:
            return False, f"Tool not found: {tool_name}"

        # Get tool metadata
        metadata = getattr(tool, "_tool_metadata", None)
        if metadata is None:
            # No metadata means no risk level - assume high (safe default)
            risk_level = RiskLevel.HIGH
        else:
            risk_level = metadata.risk_level

        # Check based on execution mode
        mode = self.context.execution_mode

        if mode == ExecutionMode.SAFE:
            if risk_level != RiskLevel.LOW:
                return (
                    False,
                    f"Tool '{tool_name}' requires {risk_level.value} risk level. "
                    f"Safe mode only allows low-risk tools."
                )
        elif mode == ExecutionMode.STANDARD:
            if risk_level == RiskLevel.CRITICAL:
                return (
                    False,
                    f"Tool '{tool_name}' has critical risk level. "
                    f"Standard mode requires approval for critical tools."
                )
        # Expert mode allows all tools

        return True, None
