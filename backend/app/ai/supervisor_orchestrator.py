"""Supervisor orchestrator for the briefing-based agent delegation pattern.

Builds a parent StateGraph where the supervisor routes requests to specialist
agents via handoff tools. Specialists do NOT share message history -- instead,
each receives the compiled briefing document as context and contributes findings
back to the accumulating document.

Graph: START -> initialize_briefing -> planner -> supervisor <-> specialist_nodes -> END
"""

from __future__ import annotations

import asyncio
import logging
from datetime import UTC, datetime
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
    parse_and_clean,
)
from app.ai.config import AI_DELEGATION_ENFORCED, AgentConfig
from app.ai.event_types import AgentEventType
from app.ai.execution.agent_event import AgentEvent
from app.ai.handoff_tools import create_all_handoff_tools
from app.ai.message_utils import (
    extract_final_ai_response,
    is_transient_stream_error,
)
from app.ai.middleware.context_guard import ContextGuardMiddleware
from app.ai.middleware.plan_aware_tools import PlanAwareToolMiddleware
from app.ai.plan import PlanDocument
from app.ai.planner import planner_node
from app.ai.subagent_compiler import (
    build_backcast_middleware,
    compile_subagents,
    filter_tools_for_context,
)
from app.ai.subagents.db_loader import load_specialists_from_db
from app.ai.supervisor_state import BackcastSupervisorState
from app.ai.tools.briefing_tools import set_briefing
from app.ai.tools.types import ToolContext
from app.core.config import settings

logger = logging.getLogger(__name__)

_BASE_SUPERVISOR_PROMPT = """You are a supervisor for the Backcast project budget management system.

You coordinate specialist agents who report back through a compiled briefing document.
The user reads the briefing directly — do NOT summarize or repeat findings in your response.

## How It Works
The current briefing is injected into your context as a system message before every turn.
1. Read the briefing to see what has been analyzed
2. If not addressed, hand off to the most relevant specialist
3. After a specialist contributes, the briefing is updated automatically

## Execution Plan
Before delegating, review the execution plan in the state (injected as context).
- If a plan exists with multiple steps, delegate ONE step at a time in order
- Each step already specifies the specialist and focused task description
- After each specialist completes, check if the next step's dependencies are met
- If a step fails, decide whether to skip it or retry with a different approach
- For simple single-step plans, delegate normally (current behavior)

## Rules
- Do NOT write a response summarizing the briefing — the user reads the briefing directly
- Only respond if you need to ask the user a clarification question
- Do NOT hand off to the same specialist more than once for the same task
- Always check the briefing before deciding to hand off
"""

_DELEGATION_ENFORCED_SECTION = """
## CRITICAL: Plan-Driven Delegation
When a multi-step execution plan is active:
- You MUST delegate every step to the specialist specified in the plan
- You MUST NOT attempt to execute domain operations yourself
- Your ONLY tools are get_briefing and handoff_to_* -- use them to delegate
- Use get_briefing to review specialist findings between steps
- Use handoff_to_{specialist} with the step_index to assign each step
- NEVER use domain tools like get_project, global_search, find_users, etc.
- NEVER try to answer the user's question yourself -- delegate to specialists
- If you are unsure what to do, call get_briefing first, then delegate the next step
"""


def _build_supervisor_specialist_section(
    specialist_graphs: list[dict[str, Any]],
) -> str:
    """Build the ## Available Specialists section for the supervisor prompt.

    Args:
        specialist_graphs: Compiled specialist dicts with ``name`` and
            ``description`` keys.

    Returns:
        Specialist list formatted for the supervisor prompt, ready to append.
    """
    lines = ["\n\n## Available Specialists"]
    for sg in specialist_graphs:
        name = sg.get("name", "")
        desc = sg.get("presentation_prompt", sg.get("description", ""))
        lines.append(f"- {name} -> {desc}")
    return "\n".join(lines)


_BRIEFING_HANDOFF_SUFFIX = (
    "You do NOT have direct access to Backcast tools. "
    "Delegate all operations to specialists via handoff tools."
)

_BRIEFING_CONTEXT_PREFIX = "## Current Briefing\n\n"


def _briefing_update(
    doc: BriefingDocument,
    plan_data: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build the standard state update after briefing initialization.

    Args:
        doc: The briefing document to serialize.
        plan_data: Optional serialized PlanDocument to carry forward.
    """
    briefing_md = doc.to_markdown() if doc.sections else "No findings yet."
    update: dict[str, Any] = {
        "briefing_data": doc.model_dump(),
        "supervisor_iterations": 0,
        "max_supervisor_iterations": 3,
        "completed_specialists": set(),
        "messages": [SystemMessage(content=f"{_BRIEFING_CONTEXT_PREFIX}{briefing_md}")],
        "completed_steps": set(),
        "current_step_index": -1,
    }
    if plan_data is not None:
        update["plan_data"] = plan_data
    return update


class _BriefingSupervisorState(AgentState[Any]):
    """State extension for the briefing supervisor subgraph.

    Adds ``briefing_data`` and ``plan_data`` so LangGraph shares them from
    the parent ``BackcastSupervisorState`` via automatic key-matching state
    sharing.
    """

    briefing_data: dict[str, Any]
    plan_data: dict[str, Any]


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
        doc = BriefingDocument.from_state(briefing_data)
        return doc.to_markdown()

    return get_briefing


class SupervisorOrchestrator:
    """Orchestrator that builds a briefing-room supervisor graph.

    Creates a parent StateGraph where the supervisor routes to specialist
    agents via handoff tools. When a plan is active, the supervisor iterates
    through plan steps sequentially, delegating one step at a time.
    """

    def __init__(
        self,
        model: str | BaseChatModel,
        context: ToolContext,
        system_prompt: str | None = None,
        main_assistant_config: Any | None = None,
    ) -> None:
        self.model = model
        self.context = context
        self.system_prompt = system_prompt
        self.main_assistant_config = main_assistant_config
        self._event_bus = context._event_bus

    def _publish_plan_update(self, plan: PlanDocument) -> None:
        """Emit a PLAN_UPDATE event if an event bus is available."""
        if self._event_bus is None:
            logger.warning(
                "[PLAN_UPDATE] Cannot emit: event_bus is None "
                "(plan has %d steps, %d completed)",
                len(plan.steps),
                sum(1 for s in plan.steps if s.status == "completed"),
            )
            return
        steps = plan.steps
        completed_steps = sum(1 for s in steps if s.status == "completed")
        logger.info(
            "[PLAN_UPDATE] Emitting: %d/%d steps, statuses=%s",
            completed_steps,
            len(steps),
            [s.status for s in steps],
        )
        self._event_bus.publish(
            AgentEvent(
                event_type=AgentEventType.PLAN_UPDATE,
                data={
                    "type": AgentEventType.PLAN_UPDATE,
                    "plan": plan.model_dump(),
                    "plan_markdown": plan.to_prompt_text(),
                    "completed_steps": completed_steps,
                    "total_steps": len(steps),
                },
                timestamp=datetime.now(UTC),
            )
        )

    async def create_supervisor_graph(self, config: AgentConfig | None = None) -> Any:
        """Create the briefing-based supervisor + specialist parent graph."""
        if config is None:
            config = AgentConfig()

        logger.info(
            "[SUPERVISOR_CREATION_START] model=%s | execution_mode=%s",
            self.model,
            self.context.execution_mode.value,
        )

        # --- 1. Tool filtering ---
        all_tools = await filter_tools_for_context(self.context, config)

        # --- 2. Compile specialists ---
        if config.subagents is not None:
            subagent_configs = config.subagents
        else:
            try:
                subagent_configs = await load_specialists_from_db()
            except Exception as exc:
                logger.error(
                    "[SUPERVISOR] DB specialist loading failed: %s", exc
                )
                subagent_configs = []

        # Filter specialists by delegation config
        if self.main_assistant_config and self.main_assistant_config.delegation_config:
            allowed = self.main_assistant_config.delegation_config.get(
                "allowed_specialists"
            )
            if allowed is not None:
                subagent_configs = [
                    s for s in subagent_configs if s.get("name") in allowed
                ]
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
        handoff_tools = create_all_handoff_tools(specialist_graphs)
        supervisor_tools: list[BaseTool] = [get_briefing_tool] + list(handoff_tools)

        direct_tool_names: list[str] = []
        if self.main_assistant_config and self.main_assistant_config.delegation_config:
            direct_tool_names = (
                self.main_assistant_config.delegation_config.get("direct_tools", [])
                or []
            )
        direct_tools: list[BaseTool] = []
        if direct_tool_names:
            tool_map = {t.name: t for t in all_tools}
            for name in direct_tool_names:
                if name in tool_map:
                    direct_tools.append(tool_map[name])
            supervisor_tools.extend(direct_tools)

        # --- 4. Build supervisor agent ---
        base_prompt = self.system_prompt or _BASE_SUPERVISOR_PROMPT

        # Resolve {specialist_section} placeholder BEFORE appending sections
        # that may contain literal {braces} which would collide with .format()
        specialist_section = _build_supervisor_specialist_section(specialist_graphs)
        if "{specialist_section}" in base_prompt:
            base_prompt = base_prompt.replace(
                "{specialist_section}", specialist_section, 1
            )
        else:
            base_prompt = base_prompt + specialist_section

        # Append delegation enforcement section if configured
        if AI_DELEGATION_ENFORCED:
            base_prompt += _DELEGATION_ENFORCED_SECTION

        supervisor_prompt = base_prompt

        # Append direct-tools or handoff suffix
        if direct_tools:
            tool_names = ", ".join(t.name for t in direct_tools)
            direct_tools_suffix = (
                f"\n\nYou have DIRECT access to these Backcast tools: [{tool_names}]. "
                "Use them directly for their operations. "
                "ALL other Backcast operations must be delegated to specialists "
                "via handoff tools."
            )
            supervisor_prompt += direct_tools_suffix
        else:
            supervisor_prompt += "\n\n" + _BRIEFING_HANDOFF_SUFFIX

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
        specialist_wrappers: dict[str, Any] = {}
        for sg in specialist_graphs:
            specialist_wrappers[sg["name"]] = self._create_specialist_wrapper(
                specialist_name=sg["name"],
                specialist_graph=sg["runnable"],
            )

        # --- 6. Build initialize_briefing node ---
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

            existing_briefing = state.get("briefing_data")
            if existing_briefing:
                doc = BriefingDocument.from_state(existing_briefing)
                if doc.original_request != "(recovered)":
                    doc.original_request = user_request
                    logger.info(
                        "[SUPERVISOR] Reusing existing briefing with %d sections",
                        len(doc.sections),
                    )
                    return _briefing_update(doc, plan_data=state.get("plan_data"))

            doc = initialize_briefing(user_request)
            return _briefing_update(doc)

        # --- 6b. Build the planner node ---
        specialist_catalog = [
            {"name": sg["name"], "description": sg.get("presentation_prompt", sg.get("description", ""))}
            for sg in specialist_graphs
        ]

        async def planner_node_fn(
            state: BackcastSupervisorState,
        ) -> dict[str, Any]:
            assert isinstance(self.model, BaseChatModel), (
                "model must be resolved to BaseChatModel"
            )
            planner_template = None
            if self.main_assistant_config and hasattr(
                self.main_assistant_config, "planner_prompt"
            ):
                planner_template = self.main_assistant_config.planner_prompt
            try:
                result = await planner_node(
                    dict(state),
                    self.model,
                    specialist_catalog=specialist_catalog,
                    planner_prompt_template=planner_template,
                )
                plan_data = result.get("plan_data")
                if plan_data:
                    plan = PlanDocument.from_state(plan_data)
                    self._publish_plan_update(plan)
                return result
            except Exception:
                logger.exception(
                    "[PLANNER] planner_node failed, falling back to no-plan mode"
                )
                plan = PlanDocument(original_request="(planner error)")
                self._publish_plan_update(plan)
                return {"plan_data": plan.model_dump()}

        # --- 7. Build parent graph ---
        parent = StateGraph(BackcastSupervisorState)
        parent.add_node("initialize_briefing", initialize_briefing_node)
        parent.add_node("planner", planner_node_fn)
        parent.add_node("supervisor", supervisor_agent)
        for name, wrapper_fn in specialist_wrappers.items():
            parent.add_node(name, wrapper_fn)

        # --- 8. Wire edges ---
        parent.add_edge(START, "initialize_briefing")
        parent.add_edge("initialize_briefing", "planner")
        parent.add_edge("planner", "supervisor")
        parent.add_conditional_edges(
            "supervisor",
            self._make_supervisor_router(specialist_names),
            specialist_names + [END],
        )
        # NOTE: specialist nodes return Command(goto="supervisor") or
        # Command(goto=END) explicitly — no static edge to supervisor.

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
    def _make_supervisor_router(specialist_names: list[str]) -> Any:
        """Create a routing function for the supervisor node.

        Routes based on handoff tool calls. When a multi-step plan is active
        the iteration cap is set to ``len(plan.steps) + 1``. If no handoff
        is called but the plan has pending steps, the supervisor loops back
        to continue delegating.
        """
        from app.ai.handoff_tools import _slugify

        slug_map: dict[str, str] = {}
        for name in specialist_names:
            slug = _slugify(name)
            if slug in slug_map:
                logger.warning(
                    "[SUPERVISOR] Slug collision: '%s' and '%s' both map to '%s'",
                    slug_map[slug],
                    name,
                    slug,
                )
            slug_map[slug] = name

        def router(state: BackcastSupervisorState) -> str:
            iterations = state.get("supervisor_iterations", 0)
            max_iterations = state.get("max_supervisor_iterations", 3)

            # Parse plan data once for both iteration cap and re-dispatch logic
            plan_data = state.get("plan_data")
            plan: PlanDocument | None = None
            has_plan = False
            if plan_data:
                plan = PlanDocument.from_state(plan_data)
                if plan.requires_planning and plan.steps:
                    has_plan = True
                    plan_max = len(plan.steps) + 1
                    if plan_max > max_iterations:
                        max_iterations = plan_max

            if iterations >= max_iterations:
                logger.warning(
                    "[SUPERVISOR] Max iterations (%d) reached, forcing END",
                    max_iterations,
                )
                return END

            messages = state.get("messages", [])
            if not messages:
                return END

            last_msg = messages[-1]
            if isinstance(last_msg, AIMessage) and last_msg.tool_calls:
                completed = state.get("completed_specialists", set())
                specialist_set = set(specialist_names)

                for tc in last_msg.tool_calls:
                    tool_name = tc.get("name", "")
                    if tool_name.startswith("handoff_to_"):
                        slug = tool_name.removeprefix("handoff_to_")
                        spec_name = slug_map.get(slug, slug)

                        # Block re-dispatch only in non-plan mode.
                        # In plan-driven mode the specialist_node handles
                        # the "no pending steps" early exit, so the router
                        # allows re-dispatch to the same specialist.
                        if spec_name in completed and not has_plan:
                            logger.warning(
                                "[SUPERVISOR] Preventing redispatch to "
                                "completed specialist: %s",
                                spec_name,
                            )
                            return END

                        if spec_name in specialist_set:
                            return spec_name

            # No handoff → END.  Multi-step plans continue via the
            # specialist → supervisor edge (line 403): each specialist
            # routes back to the supervisor on completion, which then
            # delegates the next pending step.  A self-loop here would
            # cause the supervisor to run in parallel with an active
            # specialist, producing concurrent writes to briefing_data.
            return END

        return router

    def _create_specialist_wrapper(
        self, specialist_name: str, specialist_graph: Any
    ) -> Any:
        """Create a briefing-specialist wrapper node for a compiled agent.

        Isolates the specialist from the parent graph: constructs fresh messages
        with the briefing (and plan-step context when applicable), invokes the
        specialist graph, then compiles findings back into the briefing.
        Failed specialists are NOT added to ``completed_specialists`` so the
        supervisor can retry them.
        """

        async def specialist_node(
            state: BackcastSupervisorState,
        ) -> dict[str, Any] | Command:  # type: ignore[type-arg]
            # --- Resolve plan step for this specialist ---
            plan_data = state.get("plan_data")
            active_plan: PlanDocument | None = None
            active_step = None
            if plan_data:
                active_plan = PlanDocument.from_state(plan_data)
                completed_step_indices = state.get("completed_steps", set())
                for step in active_plan.steps:
                    if (
                        step.specialist == specialist_name
                        and step.status == "pending"
                        and step.step_index not in completed_step_indices
                        and active_plan.are_dependencies_met(step.step_index)
                    ):
                        active_step = step
                        break

            # Early-exit guard: prevent redundant non-plan re-dispatch.
            # For plan-driven execution, allow re-entry when a pending step
            # exists for this specialist (same specialist may handle multiple
            # plan steps). For non-plan mode, use completed_specialists.
            if active_step is None and active_plan is not None:
                # Plan exists but no pending step for this specialist
                logger.info(
                    "[SUPERVISOR] Specialist %s has no pending plan step, early exit",
                    specialist_name,
                )
                return Command(
                    update={
                        "active_agent": "supervisor",
                        "supervisor_iterations": state.get("supervisor_iterations", 0)
                        + 1,
                    },
                    goto=END,
                )

            if active_plan is None:
                # Non-plan mode: block via completed_specialists
                completed = state.get("completed_specialists", set())
                if specialist_name in completed:
                    logger.info(
                        "[SUPERVISOR] Specialist %s already completed "
                        "(non-plan), early exit",
                        specialist_name,
                    )
                    return Command(
                        update={
                            "active_agent": "supervisor",
                            "supervisor_iterations": state.get(
                                "supervisor_iterations", 0
                            )
                            + 1,
                        },
                        goto=END,
                    )

            task_desc = "Execute specialist task from briefing"
            rationale: str | None = None
            briefing_data_raw = state.get("briefing_data", {})
            doc = (
                BriefingDocument.from_state(briefing_data_raw)
                if briefing_data_raw
                else None
            )

            # Extract original request from briefing or plan (used in both branches)
            _original_request = None
            if doc and doc.original_request:
                _original_request = doc.original_request
            elif active_plan and active_plan.original_request:
                _original_request = active_plan.original_request

            if active_step is not None:
                task_desc = active_step.task_description
            elif doc and doc.task_history:
                latest = doc.task_history[-1]
                task_desc = latest.description
                rationale = latest.rationale

            # --- Build assignment block ---
            if active_step is not None and active_plan is not None:
                total_steps = len(active_plan.steps)
                lines = [
                    f"## Your Assignment (Plan Step {active_step.step_index + 1}/{total_steps})",
                    "",
                    active_step.task_description,
                    "",
                    f"**Expected output:** {active_step.expected_output}",
                ]
                if active_step.input_from_dependencies:
                    lines.append("")
                    lines.append(
                        f"**Context from previous steps:** {active_step.input_from_dependencies}"
                    )
                    for dep_idx in active_step.dependencies:
                        dep_step = active_plan.get_step(dep_idx)
                        if dep_step and dep_step.result_summary:
                            lines.append(
                                f"- Step {dep_idx} result: {dep_step.result_summary}"
                            )
                lines.append("")
                lines.append(
                    "Use the get_briefing tool to review prior specialist findings "
                    "if needed for context."
                )
                if _original_request:
                    lines.append("")
                    lines.append(f"**User's original request:** {_original_request}")
                assignment_block = "\n".join(lines)
            else:
                assignment_block = f"## Your Assignment\n\n{task_desc}"
                if rationale:
                    assignment_block += f"\n\n**Supervisor's rationale:** {rationale}"
                if _original_request:
                    assignment_block += (
                        f"\n\n**User's original request:** {_original_request}"
                    )

            isolated_messages = [
                HumanMessage(content=assignment_block),
            ]

            # Expose structured briefing data to the specialist's get_briefing tool
            set_briefing(briefing_data_raw if briefing_data_raw else None)

            # Mark plan step as in_progress and emit PLAN_UPDATE before invoking
            # the specialist so the frontend shows immediate progress feedback.
            if active_step is not None and active_plan is not None:
                active_step.status = "in_progress"
                logger.info(
                    "Plan step %d (%s) -> in_progress",
                    active_step.step_index,
                    specialist_name,
                )
                self._publish_plan_update(active_plan)

            max_iterations = state.get("max_tool_iterations", 25)
            max_retries = settings.AI_SPECIALIST_MAX_RETRIES
            result = None

            for _attempt in range(max_retries + 1):
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
                    break
                except Exception as exc:
                    if is_transient_stream_error(exc) and _attempt < max_retries:
                        logger.warning(
                            "[SPECIALIST_RETRY] %s transient error (attempt %d/%d): %s",
                            specialist_name,
                            _attempt + 1,
                            max_retries + 1,
                            exc,
                        )
                        await asyncio.sleep(2.0)
                        continue
                    logger.error(
                        "[SPECIALIST_ERROR] %s failed: %s",
                        specialist_name,
                        exc,
                        exc_info=True,
                    )
                    error_msg = (
                        f"Specialist {specialist_name} encountered an error: {exc}"
                    )
                    updated_data = compile_specialist_output(
                        briefing_data=state.get("briefing_data", {}),
                        specialist_name=specialist_name,
                        task_description=f"Failed: {exc}",
                        specialist_output=error_msg,
                    )
                    error_update: dict[str, Any] = {
                        "briefing_data": updated_data,
                        "active_agent": "supervisor",
                        "supervisor_iterations": state.get("supervisor_iterations", 0)
                        + 1,
                        "tool_call_count": 0,
                    }
                    if active_step is not None and active_plan is not None:
                        active_plan.mark_step_failed(
                            active_step.step_index, f"Specialist error: {exc}"
                        )
                        error_update["plan_data"] = active_plan.model_dump()
                        self._publish_plan_update(active_plan)
                    return Command(update=error_update, goto="supervisor")

            assert result is not None
            messages = result.get("messages", [])
            findings = extract_final_ai_response(messages)

            cleaned_findings, parsed = parse_and_clean(findings)

            updated_data = compile_specialist_output(
                briefing_data=state.get("briefing_data", {}),
                specialist_name=specialist_name,
                task_description=task_desc,
                specialist_output=cleaned_findings,
                supervisor_rationale=rationale,
                parsed_findings=parsed,
            )

            logger.info(
                "[SUPERVISOR] Specialist %s completed, briefing sections=%d",
                specialist_name,
                len(updated_data.get("sections", [])),
            )

            cmd_update: dict[str, Any] = {
                "briefing_data": updated_data,
                "active_agent": "supervisor",
                "tool_call_count": result.get("tool_call_count", 0),
                "supervisor_iterations": state.get("supervisor_iterations", 0) + 1,
                "completed_specialists": state.get("completed_specialists", set())
                | {specialist_name},
            }

            # Mark plan step as completed if plan-driven
            if active_step is not None and active_plan is not None:
                summary = cleaned_findings if cleaned_findings else ""
                active_plan.mark_step_completed(active_step.step_index, summary)
                cmd_update["plan_data"] = active_plan.model_dump()
                cmd_update["completed_steps"] = state.get("completed_steps", set()) | {
                    active_step.step_index
                }
                cmd_update["current_step_index"] = active_step.step_index
                self._publish_plan_update(active_plan)
                logger.info(
                    "Plan step %d (%s) -> completed",
                    active_step.step_index,
                    specialist_name,
                )

                # Inject plan completion status so the supervisor LLM knows
                # whether to delegate the next step or wrap up.
                pending = [
                    s for s in active_plan.steps if s.status == "pending"
                ]
                if pending:
                    next_step = pending[0]
                    plan_msg = (
                        f"Plan step {active_step.step_index + 1}/{len(active_plan.steps)} "
                        f"completed by {specialist_name}. "
                        f"Next pending step: step {next_step.step_index + 1} "
                        f"({next_step.specialist}). "
                        f"{len(pending)} step(s) remaining."
                    )
                else:
                    plan_msg = (
                        f"All {len(active_plan.steps)} plan steps completed. "
                        "Respond to the user with the briefing findings. "
                        "Do NOT delegate further."
                    )
                cmd_update["messages"] = [
                    SystemMessage(content=plan_msg)
                ]

            return Command(update=cmd_update, goto="supervisor")

        return specialist_node

    def _build_middleware(self, tools: list[BaseTool]) -> list[Any]:
        """Build middleware stack for the supervisor agent.

        Uses ContextGuardMiddleware for deterministic context trimming (replaces
        older messages with the compiled briefing document).  No secondary
        LLM-summarization middleware — the briefing already serves as the
        structured summary of all specialist work.
        """
        base = build_backcast_middleware(self.context, tools)
        return [ContextGuardMiddleware(), PlanAwareToolMiddleware(), *base]

    def _build_fallback_graph(
        self, all_tools: list[BaseTool], config: AgentConfig
    ) -> Any:
        """Build a simple agent with direct tool access (no specialists)."""
        logger.info("Building fallback graph with direct tool access")
        base_prompt = self.system_prompt or _BASE_SUPERVISOR_PROMPT
        if AI_DELEGATION_ENFORCED:
            base_prompt += _DELEGATION_ENFORCED_SECTION
        return langchain_create_agent(
            model=self.model,
            tools=all_tools,
            system_prompt=base_prompt,
            middleware=self._build_middleware(all_tools),
            checkpointer=config.checkpointer,
            context_schema=config.context_schema,
        )


__all__ = ["SupervisorOrchestrator"]
