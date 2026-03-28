"""Custom task tool for subagent delegation.

Replicates the DeepAgents SDK's _build_task_tool() behavior using
StructuredTool.from_function() + ToolRuntime pattern.

The task tool allows the main agent to spawn ephemeral subagents that
handle isolated tasks and return a single result via Command(update=...).
"""

from __future__ import annotations

from typing import Annotated, Any

from langchain.tools import ToolRuntime
from langchain_core.messages import HumanMessage, ToolMessage
from langchain_core.runnables import Runnable
from langchain_core.tools import StructuredTool
from langgraph.types import Command

# State keys excluded when passing state to subagents and when returning
# updates from subagents. Matches the SDK's _EXCLUDED_STATE_KEYS exactly.
#
# - messages: replaced with [HumanMessage(description)] for subagent invocation
# - todos / structured_response: no defined reducer, no clear meaning for subagent
# - skills_metadata / memory_contents: auto-excluded via PrivateStateAttr but
#   must also be filtered from runtime.state to prevent parent state leakage
_EXCLUDED_STATE_KEYS: frozenset[str] = frozenset({
    "messages",
    "todos",
    "structured_response",
    "skills_metadata",
    "memory_contents",
})

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
7. When only the general-purpose agent is provided, you should use it for all tasks. It is great for isolating context and token usage, and completing specific, complex tasks, as it has all the same capabilities as the main agent.

## CRITICAL: Launch Multiple Subagents for Cross-Domain Requests

When a user request spans multiple domains, launch ALL relevant subagents in a single message. Examples:

**Example 1: WBE + Cost Elements**
User: "Show me the WBE hierarchy with cost breakdowns for project X"
Assistant: Launches BOTH `project_manager` AND `cost_controller` in parallel
- `project_manager`: Gets WBE structure, hierarchy, descriptions
- `cost_controller`: Gets cost elements with budgets, actual costs
Then synthesizes a unified response showing WBE tree with cost details

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

### Example usage of the general-purpose agent:

<example_agent_descriptions>
"general-purpose": use this agent for general purpose tasks, it has access to all tools as the main agent.
</example_agent_descriptions>

<example>
User: "I want to conduct research on the accomplishments of Lebron James, Michael Jordan, and Kobe Bryant, and then compare them."
Assistant: *Uses the task tool in parallel to conduct isolated research on each of the three players*
Assistant: *Synthesizes the results of the three isolated research tasks and responds to the User*
<commentary>
Research is a complex, multi-step task in it of itself.
The research of each individual player is not dependent on the research of the other players.
The assistant uses the task tool to break down the complex objective into three isolated tasks.
Each research task only needs to worry about context and tokens about one player, then returns synthesized information about each player as the Tool Result.
This means each research task can dive deep and spend tokens and context deeply researching each player, but the final result is synthesized information, and saves us tokens in the long run when comparing the players to each other.
</commentary>
</example>

<example>
User: "Analyze a single large code repository for security vulnerabilities and generate a report."
Assistant: *Launches a single `task` subagent for the repository analysis*
Assistant: *Receives report and integrates results into final summary*
<commentary>
Subagent is used to isolate a large, context-heavy task, even though there is only one. This prevents the main thread from being overloaded with details.
If the user then asks followup questions, we have a concise report to reference instead of the entire history of analysis and tool calls, which is good and saves us time and money.
</commentary>
</example>

<example>
User: "I want to order a pizza from Dominos, order a burger from McDonald's, and order a salad from Subway."
Assistant: *Calls tools directly in parallel to order a pizza from Dominos, a burger from McDonald's, and a salad from Subway*
<commentary>
The assistant did not use the task tool because the objective is super simple and clear and only requires a few trivial tool calls.
It is better to just complete the task directly and NOT use the `task`tool.
</commentary>
</example>

### Example usage with custom agents:

<example_agent_descriptions>
"content-reviewer": use this agent after you are done creating significant content or documents
"greeting-responder": use this agent when to respond to user greetings with a friendly joke
"research-analyst": use this agent to conduct thorough research on complex topics
</example_agent_description>

<example>
user: "Please write a function that checks if a number is prime"
assistant: Sure let me write a function that checks if a number is prime
assistant: First let me use the Write tool to write a function that checks if a number is prime
assistant: I'm going to use the Write tool to write the following code:
<code>
function isPrime(n) {{
  if (n <= 1) return false
  for (let i = 2; i * i <= n; i++) {{
    if (n % i === 0) return false
  }}
  return true
}}
</code>
<commentary>
Since significant content was created and the task was completed, now use the content-reviewer agent to review the work
</commentary>
assistant: Now let me use the content-reviewer agent to review the code
assistant: Uses the Task tool to launch with the content-reviewer agent
</example>

<example>
user: "Can you help me research the environmental impact of different renewable energy sources and create a comprehensive report?"
<commentary>
This is a complex research task that would benefit from using the research-analyst agent to conduct thorough analysis
</commentary>
assistant: I'll help you research the environmental impact of renewable energy sources. Let me use the research-analyst agent to conduct comprehensive research on this topic.
assistant: Uses the Task tool to launch with the research-analyst agent, providing detailed instructions about what research to conduct and what format the report should take
</example>

<example>
user: "Hello"
<commentary>
Since the user is greeting, use the greeting-responder agent to respond with a friendly joke
</commentary>
assistant: "I'm going to use the Task tool to launch with the greeting-responder agent"
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
   - Call `project_manager` for WBE hierarchy and structure
   - Call `cost_controller` for cost element details, budgets, actual costs
   - Synthesize both results into a unified response

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
    subagent_graphs: dict[str, Runnable] = {
        spec["name"]: spec["runnable"] for spec in subagents
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
        description = task_description.format(
            available_agents=subagent_description_str
        )
    else:
        description = task_description

    def _return_command_with_state_update(
        result: dict[str, Any],
        tool_call_id: str,
    ) -> Command:
        """Build a Command that updates parent state with subagent result."""
        if "messages" not in result:
            raise ValueError(
                "CompiledSubAgent must return a state containing a 'messages' key. "
                "Custom StateGraphs used with CompiledSubAgent should include "
                "'messages' in their state schema to communicate results back "
                "to the main agent."
            )

        # Filter out excluded keys from the subagent result
        state_update = {
            k: v
            for k, v in result.items()
            if k not in _EXCLUDED_STATE_KEYS
        }

        # Strip trailing whitespace to prevent API errors
        last_message = result["messages"][-1]
        message_text = (
            last_message.content.rstrip()
            if last_message.content
            else ""
        )

        return Command(
            update={
                **state_update,
                "messages": [
                    ToolMessage(message_text, tool_call_id=tool_call_id)
                ],
            }
        )

    def _validate_and_prepare_state(
        subagent_type: str,
        description: str,
        runtime: ToolRuntime,
    ) -> tuple[Runnable, dict[str, Any]]:
        """Validate subagent_type and prepare state for invocation."""
        subagent = subagent_graphs[subagent_type]
        # Filter excluded keys from parent state
        subagent_state = {
            k: v
            for k, v in runtime.state.items()
            if k not in _EXCLUDED_STATE_KEYS
        }
        # Replace messages with the task description
        subagent_state["messages"] = [HumanMessage(content=description)]
        return subagent, subagent_state

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
    ) -> str | Command:
        if subagent_type not in subagent_graphs:
            allowed_types = ", ".join(
                f"`{k}`" for k in subagent_graphs
            )
            return (
                f"We cannot invoke subagent {subagent_type} because it does "
                f"not exist, the only allowed types are {allowed_types}"
            )
        if not runtime.tool_call_id:
            raise ValueError("Tool call ID is required for subagent invocation")
        subagent, subagent_state = _validate_and_prepare_state(
            subagent_type, description, runtime
        )
        result = subagent.invoke(subagent_state)
        return _return_command_with_state_update(result, runtime.tool_call_id)

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
    ) -> str | Command:
        if subagent_type not in subagent_graphs:
            allowed_types = ", ".join(
                f"`{k}`" for k in subagent_graphs
            )
            return (
                f"We cannot invoke subagent {subagent_type} because it does "
                f"not exist, the only allowed types are {allowed_types}"
            )
        if not runtime.tool_call_id:
            raise ValueError("Tool call ID is required for subagent invocation")
        subagent, subagent_state = _validate_and_prepare_state(
            subagent_type, description, runtime
        )
        result = await subagent.ainvoke(subagent_state)
        return _return_command_with_state_update(result, runtime.tool_call_id)

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
