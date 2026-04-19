"""Custom task tool for subagent delegation.

Replicates the DeepAgents SDK's _build_task_tool() behavior using
StructuredTool.from_function() + ToolRuntime pattern.

The task tool allows the main agent to spawn ephemeral subagents that
handle isolated tasks and return a single result via Command(update=...).
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Annotated, Any

import httpx
from langchain.tools import ToolRuntime
from langchain_core.messages import HumanMessage, ToolMessage
from langchain_core.tools import StructuredTool
from langgraph.types import Command
from pydantic import BaseModel

logger = logging.getLogger(__name__)

# State keys excluded when passing state to subagents and when returning
# updates from subagents. Matches the SDK's _EXCLUDED_STATE_KEYS exactly.
#
# - messages: replaced with [HumanMessage(description)] for subagent invocation
# - todos / structured_response: no defined reducer, no clear meaning for subagent
# - skills_metadata / memory_contents: auto-excluded via PrivateStateAttr but
#   must also be filtered from runtime.state to prevent parent state leakage
_EXCLUDED_STATE_KEYS: frozenset[str] = frozenset(
    {
        "messages",
        "todos",
        "structured_response",
        "skills_metadata",
        "memory_contents",
    }
)

TASK_TOOL_DESCRIPTION: str = """Launch an ephemeral subagent to handle complex, multi-step independent tasks with isolated context windows.

Available agent types and the tools they have access to:
{available_agents}

When using the Task tool, you must specify a subagent_type parameter to select which agent type to use.

## Usage notes:
1. Launch multiple agents concurrently whenever possible, to maximize performance; to do that, use a single message with multiple tool uses
2. When the agent is done, it will return a single message back to you. The result returned by the agent is not visible to the user. To show the user the result, you should send a text message back to the user with a concise summary of the result.
3. Each agent invocation is stateless. You will not be able to send additional messages to the agent, nor will the agent be able to communicate with you outside of its final report. Therefore, your prompt should contain a highly detailed task description for the agent to perform autonomously and you should specify exactly what information the agent should return back to you in its final and only message to you.
4. The agent's outputs should generally be trusted
5. Clearly tell the agent whether you expect it to create content, perform analysis, or just do research (search, file reads, web fetches, etc.), since it is not aware of the user's intent
6. If the agent description mentions that it should be used proactively, then you should try your best to use it without the user having to ask for it first. Use your judgement.
7. When no specialist subagent fits a task, use the general-purpose agent. It has access to all available tools and is suitable as a fallback for tasks that don't clearly map to a specialist domain.

## CRITICAL: Launch Multiple Subagents for Cross-Domain Requests

When a user request spans multiple domains, launch ALL relevant subagents in a single message. Examples:

**Example 1: WBE + Cost Elements**
User: "Show me the WBE hierarchy with cost breakdowns for project X"
Assistant: Launches `project_manager` to get WBE structure and cost elements
- `project_manager`: Gets WBE hierarchy and cost elements with budgets, actual costs
Then presents the WBE tree with integrated cost details

**Example 2: Project + EVM Metrics**
User: "What's the performance status of project X?"
Assistant: Launches BOTH `project_manager` AND `evm_analyst` in parallel
- `project_manager`: Gets project details and WBE structure
- `evm_analyst`: Calculates CPI, SPI, CV, SV, EAC, health assessment
Then synthesizes performance report with project context

**Example 3: Change Order + Impact**
User: "Analyze the impact of change order CO-001"
Assistant: Launches BOTH `change_order_manager` AND `forecast_manager` in parallel
- `change_order_manager`: Gets change order details and approval status
- `forecast_manager`: Analyzes budget/schedule impact
Then synthesizes impact assessment with change order context

### Example usage with the general-purpose agent:

<example>
User: "Search for all elements related to conveyor belt assembly in the project"
Assistant: Launches `general_purpose` subagent with instructions to use global_search
- `general_purpose`: Uses global_search to find matching WBEs, cost elements, and other entities
Returns search results to the user
<commentary>
Search is a cross-cutting concern that doesn't fit a single specialist. The general-purpose agent handles it.
</commentary>
</example>"""  # noqa: E501

TASK_SYSTEM_PROMPT: str = """## `task` (subagent spawner)

You have access to a `task` tool to launch short-lived subagents that handle isolated tasks. These agents are ephemeral -- they live only for the duration of the task and return a single result.

When to use the task tool:
- When a task is complex and multi-step, and can be fully delegated in isolation
- When a task is independent of other tasks and can run in parallel
- When a task requires focused reasoning or heavy token/context usage that would bloat the orchestrator thread
- When sandboxing improves reliability (e.g. code execution, structured searches, data formatting)
- When you only care about the output of the subagent, and not the intermediate steps (ex. performing a lot of research and then returned a synthesized report, performing a series of computations or lookups to achieve a concise, relevant answer.)

## CRITICAL: When to Call MULTIPLE Subagents

When a user request spans multiple domains or data types, you MUST delegate to ALL relevant subagents in parallel. Common scenarios:

1. **WBE + Cost Elements**: If the user asks for WBE structure AND cost elements/financial data:
   - Call `project_manager` for WBE hierarchy, structure, and cost element details
   - Present WBE tree with integrated cost breakdown

2. **Project + Forecasts**: If the user asks for project details AND forecast data:
   - Call `project_manager` for project metadata
   - Call `forecast_manager` for forecast projections and trends
   - Combine project context with forecast analysis

3. **WBE + EVM Metrics**: If the user asks for WBEs AND performance metrics (CPI, SPI, etc.):
   - Call `project_manager` for WBE structure
   - Call `evm_analyst` for EVM calculations and performance analysis
   - Present WBE hierarchy with EVM metrics integrated

4. **Change Order + Impact**: If the user asks for change orders AND their impact:
   - Call `change_order_manager` for change order details
   - Call `forecast_manager` for budget/schedule impact analysis
   - Synthesize change order information with impact assessment

**Rule of thumb**: Each subagent specializes in a specific domain. If the user's request spans multiple domains, delegate to ALL relevant subagents in parallel, then synthesize their results.

Subagent lifecycle:
1. **Spawn** -> Provide clear role, instructions, and expected output (for multiple subagents, spawn them in parallel)
2. **Run** -> The subagent completes the task autonomously (all subagents run concurrently)
3. **Return** -> The subagent provides a single structured result
4. **Reconcile** -> Incorporate or synthesize the result into the main thread (combine results from multiple subagents into a unified response)

When NOT to use the task tool:
- If you need to see the intermediate reasoning or steps after the subagent has completed (the task tool hides them)
- If the task is trivial (a few tool calls or simple lookup)
- If delegating does not reduce token usage, complexity, or context switching
- If splitting would add latency without benefit

## Important Task Tool Usage Notes to Remember
- Whenever possible, parallelize the work that you do. This is true for both tool_calls, and for tasks. Whenever you have independent steps to complete - make tool_calls, or kick off tasks (subagents) in parallel to accomplish them faster. This saves time for the user, which is incredibly important.
- Remember to use the `task` tool to silo independent tasks within a multi-part objective.
- You should use the `task` tool whenever you have a complex task that will take multiple steps, and is independent from other tasks that the agent needs to complete. These agents are highly competent and efficient.
- **Cross-domain requests**: When a user asks for information that spans multiple subagent domains, launch ALL relevant subagents in parallel, then synthesize their results into a cohesive response."""  # noqa: E501


def _summarize_structured_output(model: BaseModel) -> str:
    """Generate human-readable summary from Pydantic model.

    Args:
        model: Pydantic model instance from structured output

    Returns:
        Human-readable summary string for display in chat
    """
    # Import schemas here to avoid circular imports
    from app.models.schemas.dashboard import DashboardData
    from app.models.schemas.evm import EVMMetricsRead
    from app.models.schemas.forecast import ForecastRead
    from app.models.schemas.impact_analysis import ImpactAnalysisResponse

    if isinstance(model, EVMMetricsRead):
        # Summarize EVM metrics
        parts = [
            f"**EVM Metrics for Cost Element {model.cost_element_id}**",
        ]
        if model.cpi is not None:
            cpi_status = "on track" if model.cpi >= 1.0 else "over budget"
            parts.append(f"- CPI: {model.cpi:.2f} ({cpi_status})")
        if model.spi is not None:
            spi_status = "on track" if model.spi >= 1.0 else "behind schedule"
            parts.append(f"- SPI: {model.spi:.2f} ({spi_status})")
        parts.append(f"- Cost Variance (CV): {model.cv:,.2f}")
        parts.append(f"- Schedule Variance (SV): {model.sv:,.2f}")
        if model.eac is not None:
            parts.append(f"- Estimate at Completion (EAC): {model.eac:,.2f}")
        if model.etc is not None:
            parts.append(f"- Estimate to Complete (ETC): {model.etc:,.2f}")
        if model.warning:
            parts.append(f"- Warning: {model.warning}")
        return "\n".join(parts)

    elif isinstance(model, DashboardData):
        # Summarize dashboard data
        parts = ["**Dashboard Data**"]
        if model.last_edited_project:
            lep = model.last_edited_project
            parts.append(f"- Last edited: {lep.project_name} ({lep.project_code})")
            parts.append(f"  - Budget: {lep.metrics.total_budget:,.2f}")
            parts.append(f"  - WBEs: {lep.metrics.total_wbes}")
            parts.append(f"  - Cost Elements: {lep.metrics.total_cost_elements}")
        activity_count = sum(len(acts) for acts in model.recent_activity.values())
        parts.append(f"- Recent activity: {activity_count} updates")
        return "\n".join(parts)

    elif isinstance(model, ImpactAnalysisResponse):
        # Summarize impact analysis
        parts = [
            f"**Impact Analysis for Change Order {model.change_order_id}**",
            f"- Branch: {model.branch_name} vs {model.main_branch_name}",
        ]
        # Summarize KPIs
        kpi = model.kpi_scorecard
        if kpi.bac.delta != 0:
            parts.append(f"- BAC change: {kpi.bac.delta:,.2f}")
        if kpi.eac and kpi.eac.delta != 0:
            parts.append(f"- EAC change: {kpi.eac.delta:,.2f}")
        # Summarize entity changes
        ec = model.entity_changes
        total_changes = (
            len(ec.wbes) + len(ec.cost_elements) + len(ec.cost_registrations)
        )
        if total_changes > 0:
            parts.append(f"- Entity changes: {total_changes} total")
            if ec.wbes:
                parts.append(f"  - WBEs: {len(ec.wbes)} changes")
            if ec.cost_elements:
                parts.append(f"  - Cost Elements: {len(ec.cost_elements)} changes")
        return "\n".join(parts)

    elif isinstance(model, ForecastRead):
        # Summarize forecast
        parts = [
            f"**Forecast {model.forecast_id}**",
            f"- Cost Element: {model.cost_element_code or model.cost_element_id}",
            f"- Estimate at Completion: {model.eac_amount:,.2f}",
            f"- Basis: {model.basis_of_estimate[:100]}{'...' if len(model.basis_of_estimate) > 100 else ''}",
        ]
        if model.cost_element_budget_amount:
            budget_diff = model.eac_amount - model.cost_element_budget_amount
            parts.append(f"- Budget variance: {budget_diff:,.2f}")
        if model.approved_date:
            parts.append(f"- Approved: {model.approved_date.strftime('%Y-%m-%d')}")
        return "\n".join(parts)

    else:
        # Fallback: generic summary
        try:
            data_dict = model.model_dump(mode="json")
            # Truncate for display
            json_str = json.dumps(data_dict, indent=2, default=str)
            if len(json_str) > 500:
                json_str = json_str[:500] + "\n... (truncated)"
            return f"Structured output ({model.__class__.__name__}):\n{json_str}"
        except Exception:
            return str(model)


def build_task_tool(
    subagents: list[dict[str, Any]],
    task_description: str | None = None,
) -> StructuredTool:
    """Create a task tool from pre-built subagent graphs.

    Replicates the DeepAgents SDK's _build_task_tool() behavior.
    Uses StructuredTool.from_function() with sync task() and async atask()
    functions, and ToolRuntime for proper event streaming through parent
    astream_events.

    Args:
        subagents: List of CompiledSubAgent-like dicts, each with 'name',
            'description', and 'runnable' (a compiled Runnable / StateGraph).
        task_description: Custom description for the task tool. If None,
            uses the default TASK_TOOL_DESCRIPTION template with
            {available_agents} placeholder.

    Returns:
        A StructuredTool named 'task' that invokes subagents by type.
    """
    # Build lookup dict and description string
    subagent_graphs: dict[str, Any] = {
        spec["name"]: spec["runnable"] for spec in subagents
    }
    # Store schema for each subagent
    subagent_schemas: dict[str, type[BaseModel] | None] = {
        spec["name"]: spec.get("structured_output_schema") for spec in subagents
    }
    subagent_description_str = "\n".join(
        f"- {s['name']}: {s['description']}" for s in subagents
    )

    # Resolve description
    if task_description is None:
        description = TASK_TOOL_DESCRIPTION.format(
            available_agents=subagent_description_str
        )
    elif "{available_agents}" in task_description:
        description = task_description.format(available_agents=subagent_description_str)
    else:
        description = task_description

    def _return_command_with_state_update(
        result: dict[str, Any],
        tool_call_id: str,
        subagent_schema: type[BaseModel] | None = None,
    ) -> Command[Any]:
        """Build a Command that updates parent state with subagent result.

        Args:
            result: Subagent execution result state
            tool_call_id: Tool call ID for the ToolMessage
            subagent_schema: Optional Pydantic schema for structured output

        Returns:
            Command with state update including ToolMessage

        Raises:
            ValueError: If result doesn't contain 'messages' key
        """
        if "messages" not in result:
            raise ValueError(
                "CompiledSubAgent must return a state containing a 'messages' key. "
                "Custom StateGraphs used with CompiledSubAgent should include "
                "'messages' in their state schema to communicate results back "
                "to the main agent."
            )

        # Filter out excluded keys from the subagent result
        state_update = {
            k: v for k, v in result.items() if k not in _EXCLUDED_STATE_KEYS
        }

        # Extract the last message from subagent
        last_message = result["messages"][-1]

        # Handle structured output (Pydantic model)
        additional_kwargs = {}
        message_text = ""

        if subagent_schema is not None:
            try:
                # Check if content is a Pydantic model instance
                if isinstance(last_message.content, subagent_schema):
                    # Extract structured data
                    structured_model = last_message.content
                    # Generate human-readable summary
                    message_text = _summarize_structured_output(structured_model)
                    # Serialize model to dict for JSON storage in additional_kwargs
                    additional_kwargs["structured_output"] = {
                        "schema": subagent_schema.__name__,
                        "data": structured_model.model_dump(mode="json"),
                    }
                    logger.debug(
                        f"Extracted structured output {subagent_schema.__name__} "
                        f"from subagent result"
                    )
                else:
                    # Content is not a Pydantic model, treat as regular text
                    message_text = (
                        last_message.content.rstrip() if last_message.content else ""
                    )
                    logger.debug(
                        f"Subagent schema {subagent_schema.__name__} was "
                        f"specified but content is not a Pydantic instance"
                    )
            except Exception as e:
                # Error processing structured output, fall back to text
                logger.warning(
                    f"Error extracting structured output from subagent: {e}. "
                    f"Falling back to text content."
                )
                message_text = (
                    last_message.content.rstrip() if last_message.content else ""
                )
        else:
            # Regular text content (no structured output)
            message_text = last_message.content.rstrip() if last_message.content else ""

        # Build ToolMessage with or without additional_kwargs
        tool_message_kwargs: dict[str, Any] = {
            "content": message_text,
            "tool_call_id": tool_call_id,
        }
        if additional_kwargs:
            tool_message_kwargs["additional_kwargs"] = additional_kwargs

        return Command(
            update={
                **state_update,
                "messages": [ToolMessage(**tool_message_kwargs)],
            }
        )

    def _validate_and_prepare_state(
        subagent_type: str,
        description: str,
        runtime: ToolRuntime,
    ) -> tuple[Any, dict[str, Any], type[BaseModel] | None]:
        """Validate subagent_type and prepare state for invocation.

        Args:
            subagent_type: Name of the subagent to invoke
            description: Task description for the subagent
            runtime: ToolRuntime instance with state and config

        Returns:
            Tuple of (subagent_runnable, subagent_state, subagent_schema)
        """
        subagent = subagent_graphs[subagent_type]
        schema = subagent_schemas.get(subagent_type)
        # Filter excluded keys from parent state
        subagent_state = {
            k: v for k, v in runtime.state.items() if k not in _EXCLUDED_STATE_KEYS
        }
        # Replace messages with the task description
        subagent_state["messages"] = [HumanMessage(content=description)]
        return subagent, subagent_state, schema

    def task(
        description: Annotated[
            str,
            "A detailed description of the task for the subagent to perform "
            "autonomously. Include all necessary context and specify the "
            "expected output format.",
        ],
        subagent_type: Annotated[
            str,
            "The type of subagent to use. Must be one of the available "
            "agent types listed in the tool description.",
        ],
        runtime: ToolRuntime,
    ) -> str | Command[Any]:
        if subagent_type not in subagent_graphs:
            allowed_types = ", ".join(f"`{k}`" for k in subagent_graphs)
            return (
                f"We cannot invoke subagent {subagent_type} because it does "
                f"not exist, the only allowed types are {allowed_types}"
            )
        if not runtime.tool_call_id:
            raise ValueError("Tool call ID is required for subagent invocation")
        subagent, subagent_state, schema = _validate_and_prepare_state(
            subagent_type, description, runtime
        )
        result = subagent.invoke(subagent_state)
        return _return_command_with_state_update(
            result, runtime.tool_call_id, subagent_schema=schema
        )

    async def atask(
        description: Annotated[
            str,
            "A detailed description of the task for the subagent to perform "
            "autonomously. Include all necessary context and specify the "
            "expected output format.",
        ],
        subagent_type: Annotated[
            str,
            "The type of subagent to use. Must be one of the available "
            "agent types listed in the tool description.",
        ],
        runtime: ToolRuntime,
    ) -> str | Command[Any]:
        if subagent_type not in subagent_graphs:
            allowed_types = ", ".join(f"`{k}`" for k in subagent_graphs)
            return (
                f"We cannot invoke subagent {subagent_type} because it does "
                f"not exist, the only allowed types are {allowed_types}"
            )
        if not runtime.tool_call_id:
            raise ValueError("Tool call ID is required for subagent invocation")
        subagent, subagent_state, schema = _validate_and_prepare_state(
            subagent_type, description, runtime
        )
        max_retries = 3
        last_exc: BaseException | None = None
        for attempt in range(max_retries + 1):
            try:
                result = await subagent.ainvoke(subagent_state)
                return _return_command_with_state_update(
                    result, runtime.tool_call_id, subagent_schema=schema
                )
            except (
                httpx.ReadError,
                httpx.ConnectError,
                httpx.ConnectTimeout,
                httpx.ReadTimeout,
            ) as exc:
                last_exc = exc
                if attempt < max_retries:
                    wait = 2**attempt  # 1s, 2s, 4s
                    logger.warning(
                        "Transient %s invoking subagent %s, "
                        "attempt %d/%d, retrying in %ds",
                        type(exc).__name__,
                        subagent_type,
                        attempt + 1,
                        max_retries + 1,
                        wait,
                    )
                    await asyncio.sleep(wait)
        raise last_exc  # type: ignore[misc]

    return StructuredTool.from_function(
        name="task",
        func=task,
        coroutine=atask,
        description=description,
    )


__all__ = [
    "TASK_SYSTEM_PROMPT",
    "TASK_TOOL_DESCRIPTION",
    "_EXCLUDED_STATE_KEYS",
    "build_task_tool",
]
