"""Handoff tools for supervisor + specialist agent delegation.

Creates tools that allow the supervisor and specialist agents to transfer
control to each other within a shared parent StateGraph. Handoff preserves
full message history — the receiving agent sees everything discussed so far.
"""

from __future__ import annotations

import logging
from typing import Annotated, Any

from langchain.tools import InjectedToolCallId, tool
from langchain_core.messages import AIMessage, ToolMessage
from langchain_core.tools import BaseTool
from langgraph.prebuilt.tool_node import InjectedState
from langgraph.types import Command

from app.ai.briefing import BriefingDocument

logger = logging.getLogger(__name__)

# Metadata key set on handoff tool results so routing logic can detect
# the target agent without parsing the tool name.
METADATA_KEY_HANDOFF_DESTINATION = "__handoff_destination__"


def create_handoff_tool(
    agent_name: str,
    agent_description: str,
) -> BaseTool:
    """Create a handoff tool that transfers control to a specialist agent.

    The tool returns ``Command(goto=agent_name, graph=Command.PARENT)`` which
    tells LangGraph to route to the target agent's subgraph node in the parent
    graph, preserving the full shared state including message history.

    Args:
        agent_name: Name of the target specialist agent (must match the
            subgraph node name in the parent StateGraph).
        agent_description: Human-readable description of what the specialist
            does. Used as the tool description for the LLM.

    Returns:
        A BaseTool named ``handoff_to_{agent_name}``.
    """
    tool_name = f"handoff_to_{agent_name}"

    @tool(tool_name, description=agent_description)
    def handoff_tool(
        task_description: Annotated[
            str,
            "A brief description of the task to hand off to the specialist.",
        ],
        state: Annotated[dict[str, Any], InjectedState()],
        tool_call_id: Annotated[str, InjectedToolCallId],
    ) -> Command[Any]:
        tool_message = ToolMessage(
            content=f"Transferring to {agent_name}: {task_description}",
            tool_call_id=tool_call_id,
        )

        # Propagate reasoning_content from the last AIMessage (DeepSeek thinking
        # mode requires it on ALL assistant messages when enabled).
        rc_kwargs: dict[str, Any] = {}
        for msg in reversed(state.get("messages", [])):
            if isinstance(msg, AIMessage):
                rc = msg.additional_kwargs.get("reasoning_content")
                if rc:
                    rc_kwargs["additional_kwargs"] = {"reasoning_content": rc}
                break

        ai_message = AIMessage(
            content="",
            tool_calls=[
                {
                    "name": tool_name,
                    "args": {"task_description": task_description},
                    "id": tool_call_id,
                    "type": "tool_call",
                }
            ],
            **rc_kwargs,
        )

        # Deterministic briefing update with task assignment
        briefing_data = state.get("briefing_data", {})
        try:
            doc = BriefingDocument.model_validate(briefing_data)
        except Exception:
            doc = BriefingDocument(original_request="(recovered)")
        doc.metadata["current_task"] = {
            "specialist": agent_name,
            "description": task_description,
        }
        updated_briefing = doc.to_markdown()
        updated_data = doc.model_dump()

        return Command(
            goto=agent_name,
            graph=Command.PARENT,
            update={
                "messages": [ai_message, tool_message],
                "active_agent": agent_name,
                "briefing": updated_briefing,
                "briefing_data": updated_data,
            },
        )

    handoff_tool.metadata = {METADATA_KEY_HANDOFF_DESTINATION: agent_name}
    return handoff_tool


def create_all_handoff_tools(
    subagent_configs: list[dict[str, Any]],
) -> list[BaseTool]:
    """Create handoff tools for all configured specialist agents.

    Args:
        subagent_configs: List of subagent configuration dicts, each with
            ``name`` and ``description`` keys.

    Returns:
        List of handoff tool instances, one per specialist.
    """
    tools: list[BaseTool] = []
    for config in subagent_configs:
        name = config.get("name", "")
        description = config.get("description", "")
        if not name:
            continue
        tools.append(
            create_handoff_tool(
                agent_name=name,
                agent_description=(
                    f"Transfer to the {name} specialist. Specializes in: {description}"
                ),
            )
        )
    return tools


__all__ = [
    "METADATA_KEY_HANDOFF_DESTINATION",
    "create_all_handoff_tools",
    "create_handoff_tool",
]
