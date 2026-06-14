"""Supervisor orchestrator for the briefing-based agent delegation pattern.

Builds a parent StateGraph where the supervisor routes requests to specialist
agents via handoff tools. Specialists do NOT share message history -- instead,
each receives the compiled briefing document as context and contributes findings
back to the accumulating document.

Graph: START -> initialize_briefing -> planner -> supervisor <-> specialist_nodes -> END
"""

from __future__ import annotations

import logging
import uuid
from collections.abc import Awaitable, Callable
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
from app.ai.exceptions import ExecutionStoppedError
from app.ai.execution.agent_event import AgentEvent
from app.ai.execution.llm_retry import (
    RETRY_BASE_S,
    RETRY_CAP_S,
    RETRY_JITTER_S,
    invoke_with_retry,
)
from app.ai.handoff_tools import create_all_handoff_tools, create_replan_tool
from app.ai.message_utils import (
    extract_final_ai_response,
)
from app.ai.middleware.context_guard import ContextGuardMiddleware
from app.ai.middleware.plan_aware_tools import PlanAwareToolMiddleware
from app.ai.plan import PlanDocument
from app.ai.planner import _MAX_PLAN_STEPS, planner_node
from app.ai.prompt_template import render_prompt
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

# Backoff parameters were extracted to ``app.ai.execution.llm_retry`` as
# the shared ``RETRY_*`` constants.  These specialist-scoped aliases keep
# the historical names importable (``test_specialist_retry.py`` imports
# them under these names) and document the value-equality.
_SPECIALIST_RETRY_BASE_S = RETRY_BASE_S
_SPECIALIST_RETRY_CAP_S = RETRY_CAP_S
_SPECIALIST_RETRY_JITTER_S = RETRY_JITTER_S


async def _invoke_specialist_with_retry(
    invoke: Callable[[], Awaitable[dict[str, Any]]],
    *,
    specialist_name: str,
    max_retries: int,
    timeout: float,
    execution_id: str | None = None,
) -> dict[str, Any]:
    """Invoke a specialist subgraph with a pausable timeout and retry.

    Thin specialist-scoped wrapper around the shared
    :func:`app.ai.execution.llm_retry.invoke_with_retry`.  Behaviour is
    unchanged from the inline implementation: a provider stall is bounded
    by ``timeout`` seconds of ACTIVE time, the deadline PAUSES while the
    specialist is blocked on ``ask_user``, and retryable errors
    (timeout/transient stream) are retried with exponential backoff plus
    jitter.  Kept as a module-private callable so the existing call site
    and tests can use the specialist-named log tag.

    Args:
        invoke: Zero-arg async factory returning the specialist's result.
        specialist_name: Display name used in retry log lines.
        max_retries: Number of retries after the initial attempt.
        timeout: Active (non-paused) seconds for a single invocation.
        execution_id: Optional execution ID used to scope the
            awaiting-user pause check to this execution.

    Returns:
        The specialist result dict on success.

    Raises:
        Exception: The last error when retries are exhausted, or the
            original error if it is not retryable.
    """
    return await invoke_with_retry(
        invoke,
        label=specialist_name,
        max_retries=max_retries,
        timeout=timeout,
        execution_id=execution_id,
    )


_BASE_SUPERVISOR_PROMPT = """You are a supervisor for the Backcast project budget management system.

You coordinate specialist agents who report back through a compiled briefing document.
The user reads the briefing directly — do NOT summarize or repeat findings in your response.

## How It Works
The current briefing is injected into your context as a system message before every turn.
1. Read the briefing to see what has been analyzed
2. If not addressed, hand off to the most relevant specialist
3. After a specialist contributes, the briefing is updated automatically

## Execution Plan
{plan_section}

Follow the plan strictly:
- Delegate ONE step at a time in order
- Each step specifies the specialist and focused task description
- After each specialist completes, check if the next step's dependencies are met
- If a step fails, decide whether to skip it or retry with a different approach

## Rules
- Do NOT write a response summarizing the briefing — the user reads the briefing directly
- Only respond if you need to ask the user a clarification question
- After each step, check the briefing: if the next step is already accomplished or conflicts with findings, revise the remaining plan before continuing
- Always check the briefing before deciding to hand off

## Replanning
After each specialist completes, evaluate whether remaining steps are still valid:
- REDUNDANT: findings already contain what the next step was going to gather → call request_replan
- ALREADY ACCOMPLISHED: the specialist incidentally completed the next step's task → call request_replan
- CONTRADICTORY: findings contradict the plan's assumptions → call request_replan
- Do NOT replan just because a step failed — retry or skip instead

Rules:
- Provide a clear reason when calling request_replan
- Completed steps are preserved — only pending steps are revised
- Maximum 2 replans per execution
- When in doubt, continue with the current plan
"""

_DELEGATION_ENFORCED_SECTION = """\n
## CRITICAL: Plan-Driven Delegation
When a multi-step execution plan is active:
- You MUST delegate every step to the specialist specified in the plan
- You MUST NOT attempt to execute domain operations yourself
- Your ONLY tools are get_briefing and handoff_to_* -- use them to delegate
- Use get_briefing to review specialist findings between steps
- Use handoff_to_{specialist} with the step_index to assign each step
- NEVER use domain tools like get_project, global_search, find_users, etc.
- NEVER try to answer the user's question yourself -- delegate to specialists
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
    max_iterations: int = 5,
) -> dict[str, Any]:
    """Build the standard state update after briefing initialization.

    Args:
        doc: The briefing document to serialize.
        plan_data: Optional serialized PlanDocument to carry forward.
        max_iterations: Maximum supervisor delegation cycles.
    """
    briefing_md = doc.to_markdown() if doc.sections else "No findings yet."
    update: dict[str, Any] = {
        "briefing_data": doc.model_dump(),
        "supervisor_iterations": 0,
        "max_supervisor_iterations": max_iterations,
        "completed_specialists": set(),
        "messages": [SystemMessage(content=f"{_BRIEFING_CONTEXT_PREFIX}{briefing_md}")],
        "completed_steps": set(),
        "current_step_index": -1,
        "replan_count": 0,
        "max_replan_count": 2,
        "replan_context": "",
    }
    if plan_data is not None:
        update["plan_data"] = plan_data
    return update


class _BriefingSupervisorState(AgentState[Any]):
    """State extension for the briefing supervisor subgraph.

    Adds ``briefing_data`` and ``plan_data`` so LangGraph shares them from
    the parent ``BackcastSupervisorState`` via automatic key-matching state
    sharing.  Also mirrors ``replan_count`` and ``replan_context`` so the
    supervisor subgraph can read/write replan state.
    """

    briefing_data: dict[str, Any]
    plan_data: dict[str, Any]
    replan_count: int
    replan_context: str


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
        specialist_models: dict[str, BaseChatModel] | None = None,
    ) -> None:
        self.model = model
        self.context = context
        self.system_prompt = system_prompt
        self.main_assistant_config = main_assistant_config
        self.specialist_models = specialist_models or {}
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
                logger.error("[SUPERVISOR] DB specialist loading failed: %s", exc)
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
            specialist_models=self.specialist_models,
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
        replan_tool = create_replan_tool()
        supervisor_tools: list[BaseTool] = [get_briefing_tool, replan_tool] + list(
            handoff_tools
        )

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

        # Resolve {specialist_section} placeholder (allowlisting only that tag so
        # the literal {plan_section} placeholder survives verbatim for the
        # PlanAwareToolMiddleware pass that fills it at runtime). render_prompt
        # never raises and never re-scans injected values, so specialist
        # descriptions containing stray braces are safe here.
        specialist_section = _build_supervisor_specialist_section(specialist_graphs)
        if "{specialist_section}" in base_prompt:
            base_prompt = render_prompt(
                base_prompt, specialist_section=specialist_section
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
                f"## Available direct tools\n\nYou have DIRECT access to these tools: [{tool_names}]. "
                "Use them directly for their operations. "
                "ALL other operations must be delegated to specialists "
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

            max_iter = 5
            if self.main_assistant_config and hasattr(
                self.main_assistant_config, "max_supervisor_iterations"
            ):
                val = self.main_assistant_config.max_supervisor_iterations
                if val is not None:
                    max_iter = val

            existing_briefing = state.get("briefing_data")
            if existing_briefing:
                doc = BriefingDocument.from_state(existing_briefing)
                doc.follow_up_requests.append(user_request)
                logger.info(
                    "[SUPERVISOR] Reusing existing briefing with %d sections",
                    len(doc.sections),
                )
                return _briefing_update(
                    doc, plan_data=state.get("plan_data"), max_iterations=max_iter
                )

            doc = initialize_briefing(user_request)
            return _briefing_update(doc, max_iterations=max_iter)

        # --- 6b. Build the planner node ---
        specialist_catalog = [
            {
                "name": sg["name"],
                "description": sg.get("presentation_prompt", sg.get("description", "")),
            }
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
            specialist_names + ["planner", END],
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
            max_iterations = state.get("max_supervisor_iterations", 5)

            # Parse plan data once for both iteration cap and re-dispatch logic
            plan_data = state.get("plan_data")
            plan: PlanDocument | None = None
            has_plan = False
            if plan_data:
                plan = PlanDocument.from_state(plan_data)
                if plan.requires_planning and plan.steps:
                    has_plan = True
                    # Plan steps are capped at _MAX_PLAN_STEPS by the planner,
                    # so plan_max is at most _MAX_PLAN_STEPS + 1; this min() is
                    # a defensive hard ceiling regardless.
                    plan_max = min(len(plan.steps) + 1, _MAX_PLAN_STEPS + 1)
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
                    if tool_name == "request_replan":
                        replan_count = state.get("replan_count", 0)
                        max_replan = state.get("max_replan_count", 2)
                        if replan_count >= max_replan:
                            logger.warning(
                                "[SUPERVISOR] Max replan (%d) reached, forcing END",
                                max_replan,
                            )
                            return END
                        logger.info(
                            "[SUPERVISOR] Replan requested (count=%d)", replan_count
                        )
                        return "planner"
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

            # Re-dispatch guard: prevent running the same specialist twice
            # UNLESS a plan has a pending step for this specialist.  Plans
            # can assign multiple steps to the same specialist; the guard
            # only blocks when there is no matching pending step.
            completed = state.get("completed_specialists", set())
            if active_step is None and plan_data:
                # Debug: why was no matching step found?
                step_debug = (
                    {
                        s.step_index: {
                            "specialist": s.specialist,
                            "status": s.status,
                            "deps": s.dependencies,
                            "deps_met": (
                                active_plan.are_dependencies_met(s.step_index)
                                if active_plan
                                else False
                            ),
                        }
                        for s in active_plan.steps
                    }
                    if active_plan
                    else {}
                )
                completed_step_indices_debug = state.get("completed_steps", set())
                logger.warning(
                    "[SPECIALIST_NODE] No matching step found for '%s' | "
                    "steps=%s | completed_steps=%s | "
                    "completed_specialists=%s",
                    specialist_name,
                    step_debug,
                    completed_step_indices_debug,
                    completed,
                )
            # --- Plan-mode containment: active_step is None in plan mode ---
            # A failed dependency permanently blocks downstream steps
            # (``are_dependencies_met`` requires ``"completed"``).  Without
            # this guard the node would fall through to the non-plan branch
            # and run the specialist with stale task context until the
            # iteration cap force-ends the graph.  Instead, hand control back
            # to the supervisor with explicit guidance.  Runs BEFORE the
            # completed-specialist guard so that a pending step owned by
            # another specialist still produces actionable guidance rather
            # than a silent END.
            if active_step is None and active_plan is not None:
                pending = [s for s in active_plan.steps if s.status == "pending"]
                blocked = active_plan.blocked_step_indices()
                if not pending:
                    guidance = (
                        "All plan steps are resolved (some may have failed). "
                        "Respond to the user with the findings gathered; "
                        "do NOT delegate further."
                    )
                elif blocked:
                    guidance = (
                        f"No dispatchable step for {specialist_name}: "
                        f"step(s) {blocked} are blocked by a failed "
                        "dependency. The plan cannot continue as-is. "
                        "Call request_replan to revise the remaining steps, "
                        "or if the findings so far answer the user, "
                        "respond now without delegating further."
                    )
                else:
                    guidance = (
                        f"No pending plan step is assigned to "
                        f"{specialist_name}. Delegate the next pending "
                        "step's specialist instead."
                    )
                logger.info(
                    "[SPECIALIST_NODE] %s no active step in plan mode -> guidance",
                    specialist_name,
                )
                return Command(
                    update={
                        "active_agent": "supervisor",
                        "supervisor_iterations": state.get("supervisor_iterations", 0)
                        + 1,
                        "messages": [SystemMessage(content=guidance)],
                    },
                    goto="supervisor",
                )

            if specialist_name in completed and active_step is None:
                logger.info(
                    "[SUPERVISOR] Specialist %s already completed, early exit",
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

            _request_context: list[str] = []
            if _original_request:
                _request_context.append(f"Original request: {_original_request}")
                if doc and doc.follow_up_requests:
                    for i, fq in enumerate(doc.follow_up_requests, start=1):
                        _request_context.append(f"Follow-up {i}: {fq}")

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
                if doc and doc.sections:
                    lines.append("## Briefing Context (from prior specialists)")
                    lines.append("")
                    lines.append(doc.to_markdown())
                    lines.append("")
                for ctx_line in _request_context:
                    lines.append("")
                    lines.append(f"**{ctx_line}**")
                assignment_block = "\n".join(lines)
            else:
                assignment_block = f"## Your Assignment\n\n{task_desc}"
                if rationale:
                    assignment_block += f"\n\n**Supervisor's rationale:** {rationale}"
                for ctx_line in _request_context:
                    assignment_block += f"\n\n**{ctx_line}**"
                if doc and doc.sections:
                    assignment_block += (
                        "\n\n## Briefing Context (from prior specialists)"
                        f"\n\n{doc.to_markdown()}"
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
            # Read the invocation_id generated by the handoff tool from the
            # graph state.  A single consistent ID ensures the frontend can
            # correlate SUBAGENT, token_batch, and AGENT_COMPLETE events.
            invocation_id = state.get("current_invocation_id", "") or str(uuid.uuid4())

            # Publish SUBAGENT so the frontend creates the specialist bubble
            # immediately.  astream_events v1 does NOT emit on_chain_start
            # for plain async function nodes, so we publish directly.
            if self._event_bus is not None:
                self._event_bus.publish(
                    AgentEvent(
                        event_type=AgentEventType.SUBAGENT,
                        data={
                            "type": AgentEventType.SUBAGENT,
                            "subagent": specialist_name,
                            "invocation_id": invocation_id,
                        },
                        timestamp=datetime.now(UTC),
                    )
                )

            try:
                result = await _invoke_specialist_with_retry(
                    lambda: specialist_graph.ainvoke(
                        {
                            "messages": isolated_messages,
                            "tool_call_count": 0,
                            "max_tool_iterations": max_iterations,
                            "next": "agent",
                        },
                        config={"recursion_limit": max_iterations},
                    ),
                    specialist_name=specialist_name,
                    max_retries=max_retries,
                    timeout=float(settings.AI_SPECIALIST_STEP_TIMEOUT),
                    execution_id=(
                        self._event_bus.execution_id if self._event_bus else None
                    ),
                )
            except Exception as exc:
                logger.error(
                    "[SPECIALIST_ERROR] %s failed: %s",
                    specialist_name,
                    exc,
                    exc_info=True,
                )
                error_msg = f"Specialist {specialist_name} encountered an error: {exc}"
                updated_data = compile_specialist_output(
                    briefing_data=state.get("briefing_data", {}),
                    specialist_name=specialist_name,
                    task_description=f"Failed: {exc}",
                    specialist_output=error_msg,
                )
                error_update: dict[str, Any] = {
                    "briefing_data": updated_data,
                    "active_agent": "supervisor",
                    "supervisor_iterations": state.get("supervisor_iterations", 0) + 1,
                    "tool_call_count": 0,
                }
                if active_step is not None and active_plan is not None:
                    active_plan.mark_step_failed(
                        active_step.step_index, f"Specialist error: {exc}"
                    )
                    error_update["plan_data"] = active_plan.model_dump()
                    self._publish_plan_update(active_plan)
                    # Inject guidance so the supervisor knows how to proceed
                    # after a failed step (mirrors the success path's
                    # plan_msg injection).  Names blocked dependents, or
                    # confirms the failure is isolated.
                    blocked = [
                        s.step_index
                        for s in active_plan.steps
                        if s.status == "pending"
                        and active_step.step_index in s.dependencies
                    ]
                    if blocked:
                        guidance = (
                            f"Plan step {active_step.step_index + 1} "
                            f"({specialist_name}) FAILED. "
                            f"Step(s) {blocked} depend on it and cannot run. "
                            "Call request_replan to revise the remaining "
                            "steps, or if the findings so far answer the "
                            "user, respond now."
                        )
                    else:
                        guidance = (
                            f"Plan step {active_step.step_index + 1} "
                            f"({specialist_name}) FAILED, but no other plan "
                            "steps depend on it. Continue delegating the "
                            "next pending step, or respond with the "
                            "findings so far."
                        )
                    error_update["messages"] = [SystemMessage(content=guidance)]

                # Publish BRIEFING_UPDATE + AGENT_COMPLETE
                # for the error path — same as success path below.
                if self._event_bus is not None:
                    from app.models.schemas.ai import (
                        BriefingDocumentPublic,
                        BriefingSectionPublic,
                        WSBriefingMessage,
                    )

                    error_doc = BriefingDocument.from_state(updated_data)
                    error_briefing_md = error_doc.to_markdown()
                    if error_briefing_md:
                        self._event_bus.publish(
                            AgentEvent(
                                event_type=AgentEventType.BRIEFING_UPDATE,
                                data=WSBriefingMessage(
                                    type=AgentEventType.BRIEFING_UPDATE,
                                    briefing=BriefingDocumentPublic(
                                        original_request=error_doc.original_request,
                                        follow_up_requests=error_doc.follow_up_requests,
                                        sections=[
                                            BriefingSectionPublic(
                                                specialist_name=s.specialist_name,
                                                summary=s.findings,
                                                key_findings=s.key_findings or [],
                                                open_questions=s.open_questions or [],
                                                delegation_notes=s.delegation_notes
                                                or "",
                                                task_description=s.task_description,
                                                step_index=s.step_index,
                                            )
                                            for s in error_doc.sections
                                        ],
                                        supervisor_analysis=error_doc.supervisor_analysis,
                                        markdown=error_briefing_md,
                                    ),
                                    specialist_name=specialist_name,
                                    completed_specialists=[],
                                ).model_dump(mode="json"),
                                timestamp=datetime.now(UTC),
                            )
                        )
                    self._event_bus.publish(
                        AgentEvent(
                            event_type=AgentEventType.AGENT_COMPLETE,
                            data={
                                "type": AgentEventType.AGENT_COMPLETE,
                                "agent_type": "subagent",
                                "agent_name": specialist_name,
                                "invocation_id": invocation_id,
                            },
                            timestamp=datetime.now(UTC),
                        )
                    )

                return Command(update=error_update, goto="supervisor")

            assert result is not None

            # Prefer LangChain's parsed structured response (SpecialistOutput)
            # when available — avoids the ToolMessage concatenation fallback in
            # extract_final_ai_response() that produces raw JSON tool outputs.
            structured = result.get("structured_response")
            if structured and hasattr(structured, "summary"):
                cleaned_findings = str(structured.summary)
                parsed: dict[str, Any] = {
                    "key_findings": list(structured.key_findings)
                    if structured.key_findings
                    else None,
                    "open_questions": list(structured.open_questions)
                    if structured.open_questions
                    else None,
                    "delegation_notes": structured.delegation_notes or None,
                }
            else:
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
                pending = [s for s in active_plan.steps if s.status == "pending"]
                if pending:
                    next_step = pending[0]
                    result_preview = (
                        cleaned_findings[:500] if cleaned_findings else "(no result)"
                    )
                    plan_msg = (
                        f"Plan step {active_step.step_index + 1}/{len(active_plan.steps)} "
                        f"completed by {specialist_name}.\n"
                        f"Result: {result_preview}\n"
                        f"Next pending step: step {next_step.step_index + 1} "
                        f"({next_step.specialist}): {next_step.task_description}\n"
                        f"{len(pending)} step(s) remaining.\n\n"
                        f"If the result above makes the next step unnecessary or contradictory, "
                        f"call request_replan. Otherwise delegate the next step."
                    )
                else:
                    plan_msg = (
                        f"All {len(active_plan.steps)} plan steps completed. "
                        "Respond to the user with the briefing findings. "
                        "Do NOT delegate further."
                    )
                cmd_update["messages"] = [SystemMessage(content=plan_msg)]

            # Check stop event between specialist runs for graceful cancellation.
            # The stop_event is set externally via AgentService.request_stop()
            # when the user clicks stop or the WebSocket disconnects.
            stop_evt = self.context._stop_event
            if stop_evt is not None and stop_evt.is_set():
                logger.info(
                    "[EXECUTION_STOP] Stop event detected after specialist %s "
                    "completed — raising ExecutionStoppedError",
                    specialist_name,
                )
                raise ExecutionStoppedError(
                    execution_id=str(self.context._event_bus.execution_id)
                    if self.context._event_bus
                    else "unknown",
                )

            # Publish BRIEFING_UPDATE + specialist findings + AGENT_COMPLETE
            # for the success path.  astream_events v1 does NOT emit
            # on_chain_end for plain async function nodes, so we publish
            # directly.
            if self._event_bus is not None:
                from app.models.schemas.ai import (
                    BriefingDocumentPublic,
                    BriefingSectionPublic,
                    WSBriefingMessage,
                )

                success_doc = BriefingDocument.from_state(updated_data)
                success_briefing_md = success_doc.to_markdown()
                if success_briefing_md:
                    completed_set = cmd_update.get("completed_specialists", set())
                    completed_list = (
                        sorted(completed_set) if isinstance(completed_set, set) else []
                    )
                    self._event_bus.publish(
                        AgentEvent(
                            event_type=AgentEventType.BRIEFING_UPDATE,
                            data=WSBriefingMessage(
                                type=AgentEventType.BRIEFING_UPDATE,
                                briefing=BriefingDocumentPublic(
                                    original_request=success_doc.original_request,
                                    follow_up_requests=success_doc.follow_up_requests,
                                    sections=[
                                        BriefingSectionPublic(
                                            specialist_name=s.specialist_name,
                                            summary=s.findings,
                                            key_findings=s.key_findings or [],
                                            open_questions=s.open_questions or [],
                                            delegation_notes=s.delegation_notes or "",
                                            task_description=s.task_description,
                                            step_index=s.step_index,
                                        )
                                        for s in success_doc.sections
                                    ],
                                    supervisor_analysis=success_doc.supervisor_analysis,
                                    markdown=success_briefing_md,
                                ),
                                specialist_name=specialist_name,
                                completed_specialists=completed_list,
                            ).model_dump(mode="json"),
                            timestamp=datetime.now(UTC),
                        )
                    )

                # NOTE: The specialist's text findings are NOT published here
                # because the parent astream_events loop already captures
                # on_chat_model_stream events from inside the specialist's
                # ainvoke call and delivers them as token_batch events via
                # StreamState.flush_tokens().  Publishing cleaned_findings
                # here would duplicate the text in the specialist's chat bubble.

                self._event_bus.publish(
                    AgentEvent(
                        event_type=AgentEventType.AGENT_COMPLETE,
                        data={
                            "type": AgentEventType.AGENT_COMPLETE,
                            "agent_type": "subagent",
                            "agent_name": specialist_name,
                            "invocation_id": invocation_id,
                        },
                        timestamp=datetime.now(UTC),
                    )
                )

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
        direct_tool_names: list[str] = []
        if self.main_assistant_config and self.main_assistant_config.delegation_config:
            direct_tool_names = (
                self.main_assistant_config.delegation_config.get("direct_tools", [])
                or []
            )
        return [
            ContextGuardMiddleware(),
            PlanAwareToolMiddleware(direct_tool_names=direct_tool_names),
            *base,
        ]

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
