"""Supervisor orchestrator for the briefing-based agent delegation pattern.

Builds a parent StateGraph where the supervisor routes requests to specialist
agents via handoff tools. Specialists do NOT share message history -- instead,
each receives the compiled briefing document as context and contributes findings
back to the accumulating document.

The supervisor reads the briefing via ``get_briefing`` and delegates work via
handoff tools. Each specialist runs in isolation with only the briefing as
context, returning structured findings that get compiled back into the document.

Graph: START -> initialize_briefing -> supervisor <-> specialist_nodes -> END
"""

from __future__ import annotations

import logging
from typing import Annotated, Any

from langchain.agents import create_agent as langchain_create_agent
from langchain.agents.middleware.types import AgentState
from langchain.tools import tool as lc_tool
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_core.tools import BaseTool
from langgraph.graph import END, START, StateGraph
from langgraph.prebuilt.tool_node import InjectedState
from langgraph.types import Command

from app.ai.briefing import BriefingDocument
from app.ai.briefing_compiler import (
    compile_specialist_output,
    initialize_briefing,
    parse_structured_findings,
)
from app.ai.config import AgentConfig
from app.ai.handoff_tools import create_all_handoff_tools
from app.ai.middleware.backcast_security import BackcastSecurityMiddleware
from app.ai.middleware.temporal_context import TemporalContextMiddleware
from app.ai.subagent_compiler import DEFAULT_SYSTEM_PROMPT, compile_subagents
from app.ai.subagents import get_all_subagents
from app.ai.supervisor_state import BackcastSupervisorState
from app.ai.tools import (
    create_project_tools,
    filter_tools_by_execution_mode,
    filter_tools_by_role,
)
from app.ai.tools.types import ToolContext

logger = logging.getLogger(__name__)

BRIEFING_ROOM_SUPERVISOR_PROMPT = """You are a supervisor in the Briefing Room for the Backcast project budget management system.

You coordinate specialist agents who analyze data and report back through a compiled briefing document.

## How It Works
1. Use the `get_briefing` tool to read the current compiled findings from all specialists
2. Based on the briefing, decide which specialist to hand off to next
3. After each specialist contributes, review the updated briefing
4. When you have enough information, synthesize the findings into a response

## Available Specialists
- project_manager -> Project CRUD, WBEs, cost elements, cost tracking, progress entries
- evm_analyst -> EVM calculations, performance analysis
- change_order_manager -> Change orders, impact analysis
- user_admin -> User and department management
- visualization_specialist -> Diagrams, visualizations
- forecast_manager -> Forecasts, schedule baselines
- general_purpose -> Unclear or cross-cutting requests

## Guidelines
- Always call get_briefing first to see what's already been analyzed
- CRITICAL: Before handing off to a specialist, check if the briefing already
  contains findings that address the user's request. If the task is complete,
  respond directly instead of handing off again.
- Do NOT hand off to the same specialist more than once for the same task.
- Hand off to the most relevant specialist for each aspect of the request
- After receiving specialist findings, synthesize a clear, concise response
- Do NOT repeat detailed findings -- highlight key insights and actionable information

## CRITICAL COMPLETION RULES
1. Maximum 2 specialist cycles for simple requests. Do NOT over-delegate.
2. Always call get_briefing before deciding to hand off -- check what's already there.
3. If a specialist has completed the requested work, acknowledge completion and summarize.

## MANDATORY PRE-HANDOFF CHECKLIST
Before calling ANY handoff_to_X tool, you MUST:
1. Call get_briefing and check the current findings
2. Check Specialist Contributions section -- if specialist X already has findings, DO NOT handoff to X again
3. Verify the user's request hasn't already been addressed

Failure to check will result in redundant work, wasted API costs, and poor user experience.
"""

_BRIEFING_HANDOFF_SUFFIX = """
IMPORTANT: You do NOT have direct access to Backcast tools.
ALL Backcast operations must be delegated to specialists via handoff tools.

Always start by calling get_briefing to review the current state of knowledge.
"""

_SCOPE_BOUNDARY = (
    "\n\n## SCOPE BOUNDARY\n"
    "Focus ONLY on tasks within your specialist domain. "
    "Do NOT perform work that belongs to another specialist.\n\n"
    "## OUTPUT FORMAT\n"
    "At the end of your response, include these sections if applicable:\n"
    "- **## Key Findings**: Bullet list of your most important discoveries\n"
    "- **## Open Questions**: Questions that need answers from other specialists or the user\n"
    "- **## Delegation Notes**: Context for any specialist who should continue this work "
    "(include relevant IDs, names, partial results)\n\n"
    "These sections help the supervisor coordinate follow-up work."
)


class _BriefingSupervisorState(AgentState[Any]):
    """State extension for the briefing supervisor subgraph.

    Adds ``briefing_data`` so LangGraph shares it from the parent
    ``BackcastSupervisorState`` via automatic key-matching state sharing.
    Without this, ``InjectedState`` inside ``get_briefing`` only sees
    ``AgentState`` (messages, jump_to, structured_response) and the
    briefing data field is never passed into the subgraph.
    """

    briefing_data: dict[str, Any]


def _create_get_briefing_tool() -> BaseTool:
    """Create a tool that reads the current briefing from graph state."""

    @lc_tool(
        "get_briefing",
        description=(
            "Get the current compiled briefing document with findings from all "
            "specialists. Call this to review what has been learned before "
            "deciding next steps."
        ),
    )
    def get_briefing(
        state: Annotated[dict[str, Any], InjectedState()],
    ) -> str:
        briefing_data = state.get("briefing_data", {})
        if not briefing_data:
            return "No briefing available yet."
        try:
            doc = BriefingDocument.model_validate(briefing_data)
            return doc.to_markdown()
        except Exception:
            return "No briefing available yet."

    return get_briefing


class SupervisorOrchestrator:
    """Orchestrator that builds a briefing-room supervisor graph.

    Creates a parent StateGraph where the supervisor routes to specialist
    agents via handoff tools. Each specialist receives a compiled briefing
    document instead of shared message history, contributing structured
    findings back to the accumulating document.

    Attributes:
        model: LangChain chat model instance.
        context: ToolContext with user permissions and temporal parameters.
        system_prompt: Optional custom system prompt for the supervisor.
    """

    def __init__(
        self,
        model: str | BaseChatModel,
        context: ToolContext,
        system_prompt: str | None = None,
    ) -> None:
        self.model = model
        self.context = context
        self.system_prompt = system_prompt

    def create_supervisor_graph(self, config: AgentConfig | None = None) -> Any:
        """Create the briefing-based supervisor + specialist parent graph.

        Args:
            config: Optional AgentConfig with tool filtering parameters.

        Returns:
            Compiled StateGraph (parent graph with all specialists as nodes).
        """
        if config is None:
            config = AgentConfig()

        logger.info(
            "[SUPERVISOR_CREATION_START] create_supervisor_graph | "
            "model=%s | execution_mode=%s",
            self.model,
            self.context.execution_mode.value,
        )

        # --- 1. Tool filtering ---
        all_tools = create_project_tools(self.context)
        if config.allowed_tools is not None:
            all_tools = [t for t in all_tools if t.name in config.allowed_tools]

        all_tools = filter_tools_by_execution_mode(
            all_tools, self.context.execution_mode
        )

        if config.assistant_role is not None:
            all_tools = filter_tools_by_role(all_tools, config.assistant_role)

        if config.user_role is not None:
            all_tools = filter_tools_by_role(all_tools, config.user_role)

        # --- 2. Compile specialists ---
        subagent_configs = (
            config.subagents if config.subagents is not None else get_all_subagents()
        )
        specialist_graphs = compile_subagents(
            self.model,
            self.context,
            subagent_configs,
            all_tools,
            allowed_tools=config.allowed_tools,
            label="specialist",
        )

        specialist_names = [sg["name"] for sg in specialist_graphs]

        if not specialist_graphs:
            logger.warning(
                "No valid specialists compiled -- falling back to direct tools"
            )
            return self._build_fallback_graph(all_tools, config)

        # --- 3. Build supervisor tools ---
        get_briefing_tool = _create_get_briefing_tool()
        handoff_tools = create_all_handoff_tools(subagent_configs)

        supervisor_tools: list[BaseTool] = [get_briefing_tool] + list(handoff_tools)

        temporal_context_tool = next(
            (t for t in all_tools if t.name == "get_temporal_context"), None
        )
        if temporal_context_tool:
            supervisor_tools.append(temporal_context_tool)

        # --- 4. Build supervisor agent ---
        base_prompt = self.system_prompt or BRIEFING_ROOM_SUPERVISOR_PROMPT
        supervisor_prompt = base_prompt + _BRIEFING_HANDOFF_SUFFIX

        supervisor_agent = langchain_create_agent(
            model=self.model,
            tools=supervisor_tools,
            system_prompt=supervisor_prompt,
            middleware=self._build_middleware(all_tools),
            state_schema=_BriefingSupervisorState,
            checkpointer=config.checkpointer,
            context_schema=config.context_schema,
            name="supervisor",
        )

        # --- 5. Create specialist wrapper nodes ---
        configs_by_name = {cfg["name"]: cfg for cfg in subagent_configs}
        specialist_wrappers: dict[str, Any] = {}
        for sg in specialist_graphs:
            cfg = configs_by_name.get(sg["name"], {})
            subagent_prompt = cfg.get("system_prompt", DEFAULT_SYSTEM_PROMPT)
            specialist_wrappers[sg["name"]] = self._create_specialist_wrapper(
                specialist_name=sg["name"],
                specialist_graph=sg["runnable"],
                specialist_system_prompt=subagent_prompt,
            )

        # --- 6. Build the initialize_briefing node ---
        async def initialize_briefing_node(
            state: BackcastSupervisorState,
        ) -> dict[str, Any]:
            messages = state.get("messages", [])
            user_request = ""
            for msg in reversed(messages):
                if isinstance(msg, HumanMessage):
                    user_request = (
                        msg.content
                        if isinstance(msg.content, str)
                        else str(msg.content)
                    )
                    break

            briefing_data, _ = initialize_briefing(user_request)

            return {
                "briefing_data": briefing_data,
                "supervisor_iterations": 0,
                "max_supervisor_iterations": 3,
                "completed_specialists": set(),
            }

        # --- 7. Build parent graph ---
        parent = StateGraph(BackcastSupervisorState)
        parent.add_node("initialize_briefing", initialize_briefing_node)
        parent.add_node("supervisor", supervisor_agent)
        for name, wrapper_fn in specialist_wrappers.items():
            parent.add_node(name, wrapper_fn)

        # --- 8. Wire edges ---
        parent.add_edge(START, "initialize_briefing")
        parent.add_edge("initialize_briefing", "supervisor")

        # Supervisor routing: handoff or END
        parent.add_conditional_edges(
            "supervisor",
            self._make_supervisor_router(specialist_names),
            specialist_names + [END],
        )

        # Each specialist always returns to supervisor
        for name in specialist_names:
            parent.add_edge(name, "supervisor")

        # --- 9. Compile and return ---
        compiled = parent.compile(
            checkpointer=config.checkpointer,
            name="backcast_supervisor",
        )

        logger.info(
            "[SUPERVISOR_CREATED] Graph compiled with %d specialists",
            len(specialist_graphs),
        )

        return compiled

    @staticmethod
    def _make_supervisor_router(
        specialist_names: list[str],
    ) -> Any:
        """Create a routing function for the supervisor node.

        After the supervisor produces output, route based on whether
        it called a handoff tool (-> target specialist) or finished
        (-> END). Enforces iteration cap and prevents redispatch
        to already-completed specialists.
        """

        def router(state: BackcastSupervisorState) -> str:
            iterations = state.get("supervisor_iterations", 0)
            max_iterations = state.get("max_supervisor_iterations", 3)
            if iterations >= max_iterations:
                logger.warning(
                    "[SUPERVISOR] Max supervisor iterations (%d) reached, forcing END",
                    max_iterations,
                )
                return END

            messages = state.get("messages", [])
            if not messages:
                return END

            last_msg = messages[-1]
            if isinstance(last_msg, AIMessage) and last_msg.tool_calls:
                for tc in last_msg.tool_calls:
                    tool_name = tc.get("name", "")
                    for spec_name in specialist_names:
                        if tool_name == f"handoff_to_{spec_name}":
                            # Prevent redispatch to completed specialists
                            completed = state.get("completed_specialists", set())
                            if spec_name in completed:
                                logger.warning(
                                    "[SUPERVISOR] Preventing redispatch to "
                                    "already-completed specialist: %s",
                                    spec_name,
                                )
                                return END
                            return spec_name

            # No handoff -- supervisor is done
            return END

        return router

    def _create_specialist_wrapper(
        self,
        specialist_name: str,
        specialist_graph: Any,
        specialist_system_prompt: str,
    ) -> Any:
        """Create a briefing-specialist wrapper node for a compiled agent.

        The returned async function isolates the specialist from the parent
        graph: it constructs fresh messages containing only the briefing,
        invokes the specialist graph, then compiles findings back into the
        briefing document.

        Args:
            specialist_name: Human-readable name for logging and briefing sections.
            specialist_graph: Compiled LangGraph (output of compile_subagents()).
            specialist_system_prompt: System prompt for the specialist agent.

        Returns:
            Async function suitable as a LangGraph node.
        """

        async def specialist_node(
            state: BackcastSupervisorState,
        ) -> dict[str, Any] | Command:  # type: ignore[type-arg]
            completed = state.get("completed_specialists", set())
            if specialist_name in completed:
                logger.info(
                    "[SUPERVISOR] Specialist %s already completed, early exiting",
                    specialist_name,
                )
                return Command(
                    update={
                        "active_agent": "supervisor",
                        "supervisor_iterations": 1,
                    },
                    goto=END,
                )

            briefing_markdown = ""
            briefing_data_raw = state.get("briefing_data", {})
            if briefing_data_raw:
                try:
                    briefing_markdown = BriefingDocument.model_validate(
                        briefing_data_raw
                    ).to_markdown()
                except Exception:
                    briefing_markdown = ""

            # Extract the current task assignment for this specialist
            task_desc = "Execute specialist task from briefing"
            rationale: str | None = None
            try:
                doc = BriefingDocument.model_validate(state.get("briefing_data", {}))
                if doc.task_history:
                    latest = doc.task_history[-1]
                    task_desc = latest.description
                    rationale = latest.rationale
            except Exception:
                pass

            assignment_block = f"## Your Assignment\n\n{task_desc}"
            if rationale:
                assignment_block += f"\n\n**Supervisor's rationale:** {rationale}"

            isolated_messages = [
                SystemMessage(content=specialist_system_prompt),
                HumanMessage(
                    content=(
                        f"{assignment_block}\n\n## Briefing\n\n"
                        f"{briefing_markdown}{_SCOPE_BOUNDARY}"
                    )
                ),
            ]

            max_iterations = state.get("max_tool_iterations", 25)

            try:
                result = await specialist_graph.ainvoke(
                    {
                        "messages": isolated_messages,
                        "tool_call_count": 0,
                        "max_tool_iterations": max_iterations,
                        "next": "agent",
                    },
                    config={"recursion_limit": max_iterations},
                )
            except Exception as exc:
                logger.error(
                    "[SPECIALIST_ERROR] Specialist %s failed: %s",
                    specialist_name,
                    exc,
                    exc_info=True,
                )
                error_msg = f"Specialist {specialist_name} encountered an error: {exc}"
                updated_data, _ = compile_specialist_output(
                    briefing_data=state.get("briefing_data", {}),
                    specialist_name=specialist_name,
                    task_description=f"Failed: {exc}",
                    specialist_output=error_msg,
                    tool_calls_summary=[],
                )
                return {
                    "messages": [AIMessage(content=error_msg)],
                    "briefing_data": updated_data,
                    "active_agent": "supervisor",
                    "tool_call_count": 0,
                    "supervisor_iterations": 1,
                    "completed_specialists": {specialist_name},
                }

            findings = ""
            findings_rc_kwargs: dict[str, Any] = {}
            for msg in reversed(result.get("messages", [])):
                if isinstance(msg, AIMessage) and not msg.tool_calls:
                    findings = str(msg.content)
                    rc = msg.additional_kwargs.get("reasoning_content")
                    if rc:
                        findings_rc_kwargs["additional_kwargs"] = {
                            "reasoning_content": rc,
                        }
                    break

            tool_calls_summary: list[str] = []
            for msg in result.get("messages", []):
                if isinstance(msg, AIMessage) and msg.tool_calls:
                    for tc in msg.tool_calls:
                        args_keys = ", ".join(tc.get("args", {}).keys())
                        tool_calls_summary.append(f"{tc['name']}({args_keys})")

            parsed = parse_structured_findings(findings)

            updated_data, _ = compile_specialist_output(
                briefing_data=state.get("briefing_data", {}),
                specialist_name=specialist_name,
                task_description=task_desc,
                specialist_output=findings,
                tool_calls_summary=tool_calls_summary,
                supervisor_rationale=rationale,
                key_findings=parsed.get("key_findings"),
                open_questions=parsed.get("open_questions"),
                delegation_notes=parsed.get("delegation_notes"),
            )

            logger.info(
                "[SUPERVISOR] Specialist %s completed, briefing sections=%d",
                specialist_name,
                len(updated_data.get("sections", [])),
            )

            return {
                "messages": [
                    AIMessage(
                        content=findings or "Specialist task completed.",
                        **findings_rc_kwargs,
                    )
                ],
                "briefing_data": updated_data,
                "active_agent": "supervisor",
                "tool_call_count": result.get("tool_call_count", 0),
                "supervisor_iterations": 1,
                "completed_specialists": {specialist_name},
            }

        return specialist_node

    def _build_middleware(self, tools: list[BaseTool]) -> list[Any]:
        """Build the middleware stack for the supervisor agent."""
        return [
            TemporalContextMiddleware(self.context),
            BackcastSecurityMiddleware(
                self.context,
                tools=tools,
                interrupt_node=None,
            ),
        ]

    def _build_fallback_graph(
        self,
        all_tools: list[BaseTool],
        config: AgentConfig,
    ) -> Any:
        """Build a simple agent with direct tool access (no specialists).

        Used when no specialists compile successfully.
        """
        logger.info("Building fallback graph with direct tool access")

        base_prompt = self.system_prompt or BRIEFING_ROOM_SUPERVISOR_PROMPT

        return langchain_create_agent(
            model=self.model,
            tools=all_tools,
            system_prompt=base_prompt,
            middleware=self._build_middleware(all_tools),
            checkpointer=config.checkpointer,
            context_schema=config.context_schema,
        )


__all__ = ["SupervisorOrchestrator"]
