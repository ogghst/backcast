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
from typing import Annotated, Any, NamedTuple

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
from app.ai.config import (
    AI_DELEGATION_ENFORCED,
    AI_MAX_PREMATURE_COMPLETION_REPROMPTS,
    AI_SPECIALIST_MAX_TOOL_ITERATIONS,
    AgentConfig,
)
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
    collect_recent_ask_user_qa,
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

#: Hard cap on how many times a single specialist may be dispatched per plan
#: step in plan mode.  Mirrors the ``_MAX_PLAN_STEPS`` "prompt says it, code
#: enforces it" pattern: the supervisor prompt states "each plan step may be
#: delegated to its specialist at most ONCE", and this constant enforces it so
#: a weak reasoning model cannot drive a Swarm-style infinite re-dispatch loop
#: (supervisor -> specialist -> supervisor -> same specialist -> ...) until the
#: iteration cap force-ends the graph.  When the cap is exceeded the dispatch
#: node routes back to the supervisor with a request_replan nudge instead of
#: running the specialist again.  Set to 1 because one dispatch per step is the
#: contract; a specialist needing a redo must go through request_replan.
_MAX_DISPATCHES_PER_SPECIALIST: int = 1

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
    should_stop: Callable[[], bool] | None = None,
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

    When *should_stop* is provided it is forwarded to the pausable deadline
    so a user-initiated stop interrupts a looping/stalled specialist
    mid-flight (within a single tick window) and surfaces as a
    non-retryable :class:`ExecutionStoppedError`.

    Args:
        invoke: Zero-arg async factory returning the specialist's result.
        specialist_name: Display name used in retry log lines.
        max_retries: Number of retries after the initial attempt.
        timeout: Active (non-paused) seconds for a single invocation.
        execution_id: Optional execution ID used to scope the
            awaiting-user pause check to this execution.
        should_stop: Optional callable returning True when the surrounding
            execution has been asked to stop.

    Returns:
        The specialist result dict on success.

    Raises:
        ExecutionStoppedError: When *should_stop* returns True mid-await
            (non-retryable; propagates immediately).
        Exception: The last error when retries are exhausted, or the
            original error if it is not retryable.
    """
    return await invoke_with_retry(
        invoke,
        label=specialist_name,
        max_retries=max_retries,
        timeout=timeout,
        execution_id=execution_id,
        should_stop=should_stop,
    )


_BASE_SUPERVISOR_PROMPT = """You are a supervisor for the Backcast project budget management system.

You coordinate specialist agents who report back through a compiled briefing document.
The user reads the briefing directly for detail, but your final answer must still be a
CONCISE GROUNDED summary citing the RESOLVED FACTS the specialists established.

## How It Works
The current briefing is injected into your context as a system message before every turn.
1. Call get_briefing / read the briefing to see what has been analyzed
2. If not addressed, hand off to the most relevant specialist
3. After a specialist contributes, the briefing is updated automatically

## Execution Plan
{plan_section}

The plan is the contract:
- Delegate ONE step at a time to EXACTLY the specialist the plan names. Do NOT re-route a step to a different specialist; to re-route, call request_replan.
- Before each turn, read the briefing and REMOVE steps already accomplished — do NOT re-dispatch a specialist whose step is already done.
- After each specialist completes, check if the next step's dependencies are met.
- If a step fails, decide whether to skip it or retry with a different approach.

## Task Briefs (biggest turn-reducer)
When you hand off, write a COMPLETE task brief in the handoff arguments:
- objective: what the specialist must produce
- success criterion: how to know it is done
- inputs: any values carried from earlier steps (dependencies)
- stop condition: when the specialist should stop
- one-line tool hint: the first tool most likely to help (optional)
A specialist with a complete brief finishes in fewer turns.

## Specialist Result Validation
Validate each specialist result by FORMAT/completeness only (was a well-formed
SpecialistOutput returned? are key_findings present?). NEVER re-derive the domain
answer yourself and NEVER second-guess the specialist's content — that wastes
2-3 extra turns. If the format is valid, accept it and move on.

## Clarification discipline
- Before calling ask_user, SCAN the conversation and briefing: NEVER re-ask a question the user has already answered. If an answer exists, USE it.
- ask_user is ONLY for genuinely-missing critical information you cannot infer. Use it sparingly — a few times at most — then proceed.
- If a specialist has been (or is being) dispatched, do NOT interleave clarifications: delegate and let the specialist ask what it needs.
- Prefer acting on gathered information over gathering more.

## Rules
- When all plan steps are complete, give a CONCISE GROUNDED summary citing the
  RESOLVED FACTS (the entity codes/names + project the specialists created).
  Do NOT dump the whole briefing — the user sees the Briefing panel for detail.
  Do NOT re-derive or re-disambiguate identities the specialists already resolved
  (this is the same "Format-only validation, never re-derive" rule above applied
  to your final answer).
- Reserve ask_user for genuinely-missing critical information only; never re-ask
  a question whose answer is already in the conversation or briefing.
- Never report a plan step as done that you have NOT delegated — a step is
  complete only after its specialist returns.
- After each step, check the briefing: if the next step is already accomplished or conflicts with findings, revise the remaining plan before continuing
- Always check the briefing before deciding to hand off
- Each plan step may be delegated to its specialist at most ONCE. If you need the same specialist to redo its step, call request_replan instead of re-dispatching.

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
        "specialist_dispatch_counts": {},
        "specialist_failure_counts": {},
        "premature_reprompts": 0,
        "termination_notice": None,
    }
    if plan_data is not None:
        update["plan_data"] = plan_data
    return update


# Max chars of each step's result_summary inlined into the completion nudge.
# Mirrors the [:500] preview used in the pending-step nudge but allows a bit
# more room since the final summary is the supervisor's only grounding source.
_COMPLETION_NUDGE_SUMMARY_LIMIT = 800


def _build_completion_nudge(plan: PlanDocument, cleaned_findings: str) -> str:
    """Build the plan-completion nudge sent to the supervisor when ALL plan
    steps are done and it must answer the user.

    Foregrounds the resolved-identity channel (F2): each completed step's
    ``delegation_notes`` (created-entity code/name + resolved project) is
    inlined FIRST, falling back to ``result_summary``. This is the single
    RESOLVED FACTS block the supervisor must cite — one block, not two
    (two blocks from overlapping fields is context rot).

    Args:
        plan: The active PlanDocument (read-only; its steps carry
            ``delegation_notes`` and ``result_summary``).
        cleaned_findings: The just-completed step's findings string; used as
            a fallback when no completed step recorded a summary.

    Returns:
        The SystemMessage content instructing the supervisor to summarize the
        inlined RESOLVED FACTS for the user without re-deriving identities.
    """
    # Build the RESOLVED FACTS block from completed steps. Source
    # delegation_notes first (the resolved-identity channel); fall back to
    # result_summary. Truncate each to bound prompt size.
    finding_lines: list[str] = []
    for step in plan.steps:
        if step.status != "completed":
            continue
        notes = (step.delegation_notes or "").strip()
        summary = (step.result_summary or "").strip()
        source = notes or summary
        if not source:
            continue
        truncated = source[:_COMPLETION_NUDGE_SUMMARY_LIMIT]
        if len(source) > _COMPLETION_NUDGE_SUMMARY_LIMIT:
            truncated += "..."
        finding_lines.append(
            f"Step {step.step_index + 1} ({step.specialist}): {truncated}"
        )

    if finding_lines:
        findings_block = "\n".join(finding_lines)
    elif cleaned_findings:
        findings_block = (
            f"Step (latest): {cleaned_findings[:_COMPLETION_NUDGE_SUMMARY_LIMIT]}"
        )
    else:
        findings_block = "(no findings recorded)"

    return (
        f"All {len(plan.steps)} plan steps completed. The delegated "
        "specialists have ALREADY executed the work above -- it is done.\n\n"
        "## RESOLVED FACTS (already established by the specialists — do NOT re-derive)\n"
        f"{findings_block}\n\n"
        "Summarize the completed findings above for the user. Do NOT delegate "
        "further. Do NOT claim the work is missing, impossible, or that the "
        "required tools are unavailable -- the work HAS been performed and the "
        "results are shown above. Do NOT re-litigate whether the delegation "
        "was appropriate. The identities/projects in RESOLVED FACTS are "
        "ALREADY RESOLVED. Answer grounded ONLY in RESOLVED FACTS. Do NOT "
        "re-search, re-disambiguate, re-query, or question an identity the "
        "specialists already resolved. Use the exact code/name shown."
    )


def _build_failure_nudge(
    plan: PlanDocument,
    specialist_name: str,
    error_message: str,
) -> str:
    """Build the nudge sent to the supervisor when a specialist step FAILED.

    The success path uses ``_build_completion_nudge`` to ground the
    supervisor's final answer; the failure path previously sent a weak
    directive ("continue delegating the next pending step, or respond with
    the findings so far") that said nothing about informing the user of the
    failure or quoting the actual error.  On weaker reasoning models the
    supervisor then answered with a stale "awaiting results" message and
    left the failure visible only in the side planning panel.

    This helper forces a grounded failure report.  It distinguishes two
    sub-cases, mirroring the success path's ``if pending: ... else: ...``
    shape:

    * **Pending steps remain:** the failure is isolated.  The supervisor must
      FIRST briefly tell the user that this step failed (so the user is never
      left in the dark mid-plan), then either delegate the next pending step
      or call ``request_replan``.
    * **No pending steps remain:** the plan ended in failure.  The supervisor
      MUST now inform the user, state the error in plain language, report
      what (if anything) was accomplished before the failure, and must NOT
      claim success, say it is "awaiting results", or claim tools are
      missing/unavailable.

    Args:
        plan: The active PlanDocument (read-only); its steps carry status and
            ``result_summary`` values.
        specialist_name: Display name of the specialist that failed.
        error_message: The raw error string from the failed specialist
            (e.g. "invocation exceeded 120s of active time").  May be empty.

    Returns:
        The SystemMessage content instructing the supervisor how to respond
        after a failed step.
    """
    # Find the just-failed step (there should be exactly one freshly-marked
    # failed step; if several exist we report the latest for context).
    failed_steps = [s for s in plan.steps if s.status == "failed"]
    failed_step = failed_steps[-1] if failed_steps else None
    step_num = (failed_step.step_index + 1) if failed_step else 0
    step_label = (
        f"Plan step {step_num} ({specialist_name})" if step_num else specialist_name
    )

    # Normalize the error so it is always printable (never None/blank-silent).
    error_text = (error_message or "").strip()
    if not error_text:
        error_text = "(no error detail recorded)"

    pending = [s for s in plan.steps if s.status == "pending"]

    if pending:
        # The failure is isolated -- other steps can still run.  But the user
        # must be told NOW that this step failed, before any further work.
        next_step = pending[0]
        return (
            f"{step_label} FAILED.\n"
            f"Error: {error_text}\n\n"
            f"{len(pending)} pending step(s) still remain; this failure does "
            f"NOT block them.  Your response MUST do two things, in order:\n"
            "1. FIRST, briefly inform the user that step "
            f"{step_num} ({specialist_name}) failed and state the error in "
            "plain language.  Do NOT stay silent or say you are awaiting "
            "results.\n"
            "2. THEN either delegate the next pending step "
            f"(step {next_step.step_index + 1} ({next_step.specialist})) or "
            "call request_replan if the failure changes the plan.\n"
            "Do NOT claim this step succeeded."
        )

    # No pending steps remain: the plan ended in failure.  Build a block of
    # what was accomplished before the failure (reusing the completion nudge's
    # truncation limit) so the supervisor can report partial progress.
    accomplished_lines: list[str] = []
    for step in plan.steps:
        if step.status != "completed":
            continue
        summary = (step.result_summary or "").strip()
        if not summary:
            continue
        truncated = summary[:_COMPLETION_NUDGE_SUMMARY_LIMIT]
        if len(summary) > _COMPLETION_NUDGE_SUMMARY_LIMIT:
            truncated += "..."
        accomplished_lines.append(
            f"Step {step.step_index + 1} ({step.specialist}): {truncated}"
        )
    accomplished_block = (
        "\n".join(accomplished_lines) if accomplished_lines else "(nothing)"
    )

    return (
        f"{step_label} FAILED and there are NO remaining pending plan steps. "
        "The plan has ended without completing.\n"
        f"Error: {error_text}\n\n"
        "## Completed before the failure\n"
        f"{accomplished_block}\n\n"
        "You MUST now respond to the user. Your message MUST:\n"
        f"- State plainly that step {step_num} ({specialist_name}) FAILED and "
        "report the error above in the user's language.\n"
        "- Summarize what (if anything) was accomplished before the failure, "
        "drawing ONLY from the `Completed before the failure` block above.\n\n"
        "Do NOT delegate further.  Do NOT claim success.  Do NOT say you are "
        "awaiting results / `Attendo i risultati`.  Do NOT claim the required "
        "tools are missing, impossible, or unavailable -- this step failed for "
        "the reason stated above, not because the tools do not exist."
    )


_GATHERED_CONTEXT_HEADER = (
    "## Already-confirmed user inputs "
    "(use these verbatim as inputs; do NOT call ask_user for any of them)"
)

_GATHERED_CONTEXT_DIRECTIVE = (
    "The supervisor already asked the user these questions. Treat each answer "
    "as a confirmed input value. Do not re-ask."
)


def _build_gathered_context_block(
    supervisor_messages: list[Any],
) -> tuple[str | None, list[tuple[str, str]]]:
    """Render recent ask_user Q&A as an imperative context block.

    Returns ``(block, pairs)``.  ``block`` is ``None`` and ``pairs`` is empty
    when there is no usable gathered Q&A.

    Specialists are message-isolated from the supervisor's outer conversation,
    so they never see the supervisor's prior ``ask_user`` Q&A and re-ask
    questions the user already answered.  This collects the most recent
    (question, answer) pairs via :func:`collect_recent_ask_user_qa` (capped at
    6 pairs) and renders them as a markdown block.  The block is rendered with
    an imperative header and directive so a long-context model (e.g. GLM-4.7)
    treats the gathered answers as foreground inputs instead of background
    context appended at the end of the assignment.

    Args:
        supervisor_messages: The supervisor's outer conversation messages
            (``state["messages"]``).

    Returns:
        A ``(block, pairs)`` tuple where ``block`` is the rendered markdown
        string or ``None`` when no usable Q&A exists, and ``pairs`` is the
        underlying ``(question, answer)`` list (oldest-first, capped at 6).
    """
    pairs = collect_recent_ask_user_qa(supervisor_messages)
    if not pairs:
        return None, []
    lines = [
        _GATHERED_CONTEXT_HEADER,
        "",
        _GATHERED_CONTEXT_DIRECTIVE,
    ]
    for question, answer in pairs:
        lines.append("")
        lines.append(f"Q: {question}")
        lines.append(f"A: {answer}")
    return "\n".join(lines), pairs


def _format_gathered_context_block(
    supervisor_messages: list[Any],
) -> str | None:
    """Render recent ask_user Q&A as an assignment context block, or ``None``.

    Thin wrapper over :func:`_build_gathered_context_block` for callers that
    only need the rendered string.  Returns ``None`` when there is no usable
    gathered Q&A.
    """
    block, _pairs = _build_gathered_context_block(supervisor_messages)
    return block


class _NonplanFailureDecision(NamedTuple):
    """Outcome of a non-plan specialist failure.

    Attributes:
        goto: ``"supervisor"`` to continue the loop, or ``"END"`` to
            terminate the graph unconditionally (2nd consecutive failure).
        message: SystemMessage content to inject into the supervisor's
            messages (guidance on the 1st failure, a user-facing final
            message on the 2nd).
        failure_counts_update: The partial state update for
            ``specialist_failure_counts`` (the incremented count for this
            specialist).
    """

    goto: str
    message: str
    failure_counts_update: dict[str, int]


def _decide_nonplan_failure_action(
    specialist_name: str,
    failure_counts: dict[str, int],
    error_message: str,
) -> _NonplanFailureDecision:
    """Decide the graph action after a specialist fails in PURE non-plan mode.

    In pure non-plan mode (no active step AND no active plan) a failed/timed-out
    specialist could otherwise be re-dispatched by a weak supervisor until
    ``max_supervisor_iterations`` (~5x120s timeouts).  This bounds the loop:
    the 2nd CONSECUTIVE failure of the SAME specialist force-ends the graph
    (goto END) with a user-facing message, guaranteeing termination; the 1st
    failure returns guidance and continues (goto supervisor).

    Counts are keyed by the bare specialist name (independent of plan-step
    dispatch keys, which are ``"specialist|step"``).

    Args:
        specialist_name: Display name of the specialist that failed.
        failure_counts: Current ``specialist_failure_counts`` mapping.
        error_message: The raw error string from the failed specialist.

    Returns:
        The decision describing the goto target, message, and count update.
    """
    prior_fail = failure_counts.get(specialist_name, 0)
    new_count = prior_fail + 1

    error_text = (error_message or "").strip()
    if not error_text:
        error_text = "(no error detail recorded)"

    if new_count >= 2:
        # GUARANTEED termination: do not let the supervisor re-dispatch.
        message = (
            f"The specialist '{specialist_name}' has failed twice in a row and "
            "cannot complete this task automatically.\n"
            f"Last error: {error_text}\n\n"
            "Respond to the user now: explain that the specialist failed twice, "
            "describe what was attempted, and ask them to retry or rephrase the "
            "request. Do NOT delegate further."
        )
        return _NonplanFailureDecision(
            goto="END",
            message=message,
            failure_counts_update={specialist_name: new_count},
        )

    # 1st failure: nudge the supervisor, do NOT immediately re-dispatch.
    message = (
        f"Specialist '{specialist_name}' failed.\n"
        f"Error: {error_text}\n"
        "Inform the user of the failure. Do NOT immediately re-dispatch the "
        "same specialist; if the request is salvageable, rephrase or try a "
        "different approach, otherwise respond with the findings so far."
    )
    return _NonplanFailureDecision(
        goto="supervisor",
        message=message,
        failure_counts_update={specialist_name: new_count},
    )


class _PrematureCompletionDecision(NamedTuple):
    """Outcome of the F1 premature-completion guard decision.

    Attributes:
        goto: ``"premature_completion_guard"`` to re-prompt the supervisor,
            or ``END`` when the global reprompt cap is exhausted.
        message: SystemMessage content. For the guard branch this is the
            contrastive refutation citing ONE offending step; for the END
            branch a clean intentional termination message.
        iterations_delta: Increment to apply to ``supervisor_iterations``
            (the PRIMARY termination guarantee is the existing force-END
            iteration cap). Always 1 for the guard branch, 0 for END.
        reprompts_delta: Increment to apply to ``premature_reprompts``.
            Always 1 for the guard branch, 0 for END.
    """

    goto: str
    message: str
    iterations_delta: int
    reprompts_delta: int


def _decide_premature_completion(
    *,
    plan: PlanDocument | None,
    last_msg_is_text_only: bool,
    supervisor_iterations: int,
    max_iterations: int,
    premature_reprompts: int,
    max_reprompts: int,
) -> _PrematureCompletionDecision:
    """Decide the F1 premature-completion guard action.

    Fires ONLY when a multi-step plan is active (``requires_planning`` and
    non-empty ``steps``), the supervisor's last message is TEXT-ONLY (no
    handoff tool call — meaning it claimed completion without delegating),
    AND a dispatchable pending step still exists.

    Dispatchability is ``plan.get_next_pending_step()`` directly: it already
    excludes steps whose dependencies are not ``completed`` (failed-dep
    blocked steps). Do NOT add a separate blocked filter here.

    The PRIMARY termination guarantee is the supervisor iteration cap (the
    guard node increments ``supervisor_iterations`` on every fire, so the
    existing ``iterations >= max_iterations`` force-END at the router fires
    regardless of model behavior). ``max_reprompts`` is a tighter secondary
    bound: at exhaustion the guard returns END.

    Args:
        plan: The active PlanDocument (or ``None`` in non-plan mode).
        last_msg_is_text_only: True iff the supervisor's last AIMessage had
            no tool_calls (a free-text "done" answer).
        supervisor_iterations: Current ``supervisor_iterations`` value.
        max_iterations: Current ``max_supervisor_iterations`` value.
        premature_reprompts: Current ``premature_reprompts`` value.
        max_reprompts: ``AI_MAX_PREMATURE_COMPLETION_REPROMPTS``.

    Returns:
        The decision describing the goto target, message, and state deltas.
    """
    # --- Fire conditions ----------------------------------------------------
    # When the guard does NOT fire, the router falls through to its normal
    # END (the "No handoff → END" branch). We signal this with an empty
    # END decision (no message, no deltas) that the router ignores.
    if plan is None or not plan.requires_planning or not plan.steps:
        return _PrematureCompletionDecision(
            goto="END", message="", iterations_delta=0, reprompts_delta=0
        )
    if not last_msg_is_text_only:
        return _PrematureCompletionDecision(
            goto="END", message="", iterations_delta=0, reprompts_delta=0
        )

    next_step = plan.get_next_pending_step()
    if next_step is None:
        # All pending steps are either done or blocked by a failed dependency.
        # Nothing to re-prompt for; fall through to the normal END.
        return _PrematureCompletionDecision(
            goto="END", message="", iterations_delta=0, reprompts_delta=0
        )

    # --- Global cap: force END (clean intentional message) -----------------
    if premature_reprompts >= max_reprompts:
        message = (
            "The supervisor repeatedly reported the plan as complete while a "
            "plan step was still pending and un-dispatched, despite corrections. "
            "Terminating to avoid an unbounded loop. Respond to the user now: "
            "state honestly which steps completed and that the remaining step "
            f"(step {next_step.step_index + 1}/{len(plan.steps)}, "
            f"{next_step.specialist}) was NOT executed. Do NOT claim the work "
            "was done."
        )
        logger.warning(
            "[PREMATURE_COMPLETION] Global reprompt cap (%d/%d) reached -> END",
            premature_reprompts,
            max_reprompts,
        )
        return _PrematureCompletionDecision(
            goto="END",
            message=message,
            iterations_delta=0,
            reprompts_delta=0,
        )

    # --- Guard: contrastive refutation citing ONE offending step -----------
    # NOTE: PlanAwareToolMiddleware already injects plan.to_prompt_text() +
    # "NEXT ACTION: call handoff_to_{specialist} for step {k}/{M}" every turn.
    # This message therefore carries ONLY the contrastive delta the system
    # prompt cannot express — the refutation of the model's just-emitted FALSE
    # claim + one line citing the offending step. It deliberately does NOT
    # re-render the plan (no status markers, no NEXT ACTION) to avoid context
    # rot from duplicating the per-turn injection.
    task = (next_step.task_description or "").strip()
    task_preview = task[:160]
    total = len(plan.steps)
    message = (
        "Your last message reported the plan as complete. That is FALSE: "
        f"step {next_step.step_index + 1} ({next_step.specialist}) — "
        f"{task_preview} — is still PENDING and has NOT been executed. "
        f"Call handoff_to_{next_step.specialist} for step "
        f"{next_step.step_index + 1}/{total} now, or call request_replan. "
        "Do NOT report a pending step as done."
    )
    logger.info(
        "[PREMATURE_COMPLETION] Guard firing (reprompts %d/%d) for pending "
        "step %d/%d (%s)",
        premature_reprompts,
        max_reprompts,
        next_step.step_index + 1,
        total,
        next_step.specialist,
    )
    return _PrematureCompletionDecision(
        goto="premature_completion_guard",
        message=message,
        iterations_delta=1,
        reprompts_delta=1,
    )


def _build_bounded_termination_notice(plan: PlanDocument | None) -> str:
    """Build a grounded, user-facing notice for a bounded termination.

    Called by the ``bounded_terminate`` node when the supervisor graph hits a
    silent force-END path (max-iterations or max-replan cap). Previously both
    paths returned ``END`` with NO message, so a run that looped on an
    undeliverable specialist (e.g. web_researcher failing on a Tavily quota)
    terminated with ``completed=[]`` and the user received NOTHING about the
    failure/bound.

    The notice is built from plan STATE (not hardcoded payloads and NOT an
    extra supervisor LLM turn — the supervisor may be misbehaving). It
    renders three sections:

    * **Completed:** completed steps with a short ``result_summary``.
    * **Failed:** failed steps WITH their ``result_summary`` (this carries the
      real error, e.g. "web_researcher: Tavily API error: ... usage limit").
    * **Not started:** pending / in-progress / blocked steps with their
      ``task_description``.

    In non-plan mode (``plan is None``) a simpler "reached the execution
    limit without completing" notice is emitted.

    Args:
        plan: The active PlanDocument (read-only), or ``None`` in non-plan mode.

    Returns:
        The termination notice string. Always non-empty.
    """
    if plan is None or not plan.steps:
        return (
            "I reached the execution limit without completing your request. "
            "Please try again — the failure may have been transient — or "
            "simplify the request so it can be completed in fewer steps."
        )

    completed_lines: list[str] = []
    failed_lines: list[str] = []
    not_started_lines: list[str] = []

    for step in plan.steps:
        label = f"Step {step.step_index + 1} ({step.specialist})"
        status = step.status
        if status == "completed":
            summary = (step.result_summary or "").strip() or "(no summary)"
            completed_lines.append(f"- {label}: {summary}")
        elif status == "failed":
            # The result_summary is the error carrier — quote it verbatim so
            # the user sees the real reason (e.g. "Tavily API error: usage limit").
            summary = (
                step.result_summary or ""
            ).strip() or "(no error detail recorded)"
            failed_lines.append(f"- {label}: {summary}")
        else:
            # pending / in_progress / blocked — list the task so the user
            # knows what did NOT run.
            task = (step.task_description or "").strip() or "(no task description)"
            not_started_lines.append(f"- {label}: {task}")

    completed_block = "\n".join(completed_lines) if completed_lines else "(none)"
    failed_block = "\n".join(failed_lines) if failed_lines else "(none)"
    not_started_block = "\n".join(not_started_lines) if not_started_lines else "(none)"

    return (
        "I could not complete your request within the execution limit "
        "(the delegation/replan cap was reached).\n\n"
        "## Completed\n"
        f"{completed_block}\n\n"
        "## Failed\n"
        f"{failed_block}\n\n"
        "## Not started\n"
        f"{not_started_block}\n\n"
        "Please retry — the failure may have been transient — or simplify "
        "the request so it can be completed in fewer steps."
    )


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
        # The planner routes on the STRUCTURED capability contract, which
        # lives in the specialist ``description`` (enriched form:
        # "verbs — entities: ... — use when: ...").  ``presentation_prompt``
        # stays human-readable for the supervisor's specialist list.  Fall
        # back to presentation_prompt when description is absent (legacy).
        specialist_catalog = [
            {
                "name": sg["name"],
                "description": sg.get("description")
                or sg.get("presentation_prompt", ""),
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
        # F1 premature-completion guard node: the router routes here when the
        # supervisor emits a text-only "done" answer while a dispatchable plan
        # step is still PENDING. The node applies the contrastive-refutation
        # Command and returns to "supervisor". It is a plain node (NOT a
        # conditional-edge Command) because Command(update=...) from a
        # conditional-edge fn is broken in LangGraph 1.1.9.
        parent.add_node(
            "premature_completion_guard",
            self._premature_completion_guard_node,
        )
        # Bounded-termination node: the router routes here when a silent
        # force-END path fires (max-iterations or max-replan cap). The node
        # builds a grounded notice from plan state and returns Command(goto=END)
        # so the user is ALWAYS told when a run is bounded. Plain node (not a
        # conditional-edge Command) for the same reason as the F1 guard.
        parent.add_node(
            "bounded_terminate",
            self._bounded_terminate_node,
        )

        # --- 8. Wire edges ---
        parent.add_edge(START, "initialize_briefing")
        parent.add_edge("initialize_briefing", "planner")
        parent.add_edge("planner", "supervisor")
        parent.add_conditional_edges(
            "supervisor",
            self._make_supervisor_router(specialist_names),
            specialist_names
            + ["planner", "premature_completion_guard", "bounded_terminate", END],
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
                    "[SUPERVISOR] Max iterations (%d) reached -> "
                    "bounded_terminate (grounded notice to user)",
                    max_iterations,
                )
                return "bounded_terminate"

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
                                "[SUPERVISOR] Max replan (%d) reached -> "
                                "bounded_terminate (grounded notice to user)",
                                max_replan,
                            )
                            return "bounded_terminate"
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
            #
            # F1 premature-completion guard: BEFORE terminating, check whether
            # the supervisor just emitted a text-only "done" answer while a
            # dispatchable plan step is still PENDING (a confabulation). If so,
            # route to the guard node to re-prompt it instead of baking in the
            # false final answer. Safe here: this branch emitted NO specialist
            # tool_call, so no self-loop/parallel-write hazard. The guard NODE
            # recomputes the decision from state and applies the Command
            # (the router can only return a goto string; Command(update=...)
            # from a conditional-edge fn is broken in LangGraph 1.1.9).
            last_msg_is_text_only = isinstance(last_msg, AIMessage) and not bool(
                last_msg.tool_calls
            )
            decision = _decide_premature_completion(
                plan=plan,
                last_msg_is_text_only=last_msg_is_text_only,
                supervisor_iterations=iterations,
                max_iterations=max_iterations,
                premature_reprompts=state.get("premature_reprompts", 0),
                max_reprompts=AI_MAX_PREMATURE_COMPLETION_REPROMPTS,
            )
            if decision.goto == "premature_completion_guard":
                return "premature_completion_guard"
            return END

        return router

    @staticmethod
    def _premature_completion_guard_node(
        state: BackcastSupervisorState,
    ) -> Command:  # type: ignore[type-arg]
        """F1 guard node: re-prompt the supervisor after a premature completion.

        Recomputes the pure ``_decide_premature_completion`` decision from
        state (the router can only return a goto string) and applies it as a
        Command: injects the contrastive-refutation SystemMessage and bumps
        ``supervisor_iterations`` (the PRIMARY termination guarantee — the
        force-END iteration cap at the router) and ``premature_reprompts``
        (the tighter secondary bound). Returns to ``"supervisor"`` so the
        model sees the correction and re-attempts.

        Mirrors the guard-node-applies-Command pattern used by every other
        guard (nonplan failure, re-dispatch cap, no-active-step containment).
        """
        plan_data = state.get("plan_data")
        plan = PlanDocument.from_state(plan_data) if plan_data else None
        messages = state.get("messages", [])
        last_msg = messages[-1] if messages else None
        last_msg_is_text_only = isinstance(last_msg, AIMessage) and not bool(
            getattr(last_msg, "tool_calls", None)
        )
        decision = _decide_premature_completion(
            plan=plan,
            last_msg_is_text_only=last_msg_is_text_only,
            supervisor_iterations=state.get("supervisor_iterations", 0),
            max_iterations=state.get("max_supervisor_iterations", 5),
            premature_reprompts=state.get("premature_reprompts", 0),
            max_reprompts=AI_MAX_PREMATURE_COMPLETION_REPROMPTS,
        )
        # The router only routes here when the decision is the guard branch;
        # defensively handle END (re-terminate cleanly).
        if decision.goto != "premature_completion_guard":
            if decision.message:
                return Command(
                    update={
                        "messages": [SystemMessage(content=decision.message)],
                    },
                    goto=END,
                )
            return Command(goto=END)
        return Command(
            update={
                "messages": [SystemMessage(content=decision.message)],
                "supervisor_iterations": decision.iterations_delta,
                "premature_reprompts": decision.reprompts_delta,
            },
            goto="supervisor",
        )

    @staticmethod
    def _bounded_terminate_node(
        state: BackcastSupervisorState,
    ) -> Command:  # type: ignore[type-arg]
        """Bounded-termination node: emit a grounded notice and END.

        Replaces the two silent ``return END`` paths in the router
        (max-iterations and max-replan caps). Builds a user-facing notice
        from the plan STATE via :func:`_build_bounded_termination_notice`
        (NOT an extra supervisor LLM turn — the supervisor may be
        misbehaving), sets ``termination_notice`` so ``agent_service`` can
        persist it as a final assistant message, and bumps
        ``supervisor_iterations`` (mirrors the guard-node shape).

        Returns ``Command(goto=END)``. The notice is the ONLY thing that
        reaches the user; the node does NOT inject anything into the
        supervisor's ``messages`` (the graph is terminating).
        """
        plan_data = state.get("plan_data")
        plan = PlanDocument.from_state(plan_data) if plan_data else None
        notice = _build_bounded_termination_notice(plan)
        logger.warning(
            "[BOUNDED_TERMINATE] Graph hit a force-END cap "
            "(iterations=%s/%s, replan=%s/%s) -> emitting termination notice",
            state.get("supervisor_iterations", 0),
            state.get("max_supervisor_iterations", 0),
            state.get("replan_count", 0),
            state.get("max_replan_count", 0),
        )
        return Command(
            update={
                "termination_notice": notice,
                # ``supervisor_iterations`` is an ``operator.add`` reducer, so
                # the value here is a DELTA (mirrors the F1 guard node's
                # ``decision.iterations_delta``). Pass 1, not current+1.
                "supervisor_iterations": 1,
            },
            goto=END,
        )

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

            # --- Code-enforced per-specialist re-dispatch cap (plan mode) ---
            # Tracks dispatches at (specialist, step_index) granularity so the
            # cap is exactly "once per plan step".  A specialist that has
            # already been dispatched for THIS step (e.g. it ran, the
            # supervisor ignored the result, and re-dispatched the same step)
            # is routed to the supervisor with a request_replan nudge instead
            # of running again.  This breaks the Swarm-style infinite
            # re-dispatch loop a weak reasoning model can drive.  A genuine
            # NEW step for the same specialist is unaffected (different key).
            dispatch_counts: dict[str, int] = state.get(
                "specialist_dispatch_counts", {}
            )
            if active_step is not None and active_plan is not None:
                dispatch_key = f"{specialist_name}|{active_step.step_index}"
                prior = dispatch_counts.get(dispatch_key, 0)
                if prior >= _MAX_DISPATCHES_PER_SPECIALIST:
                    logger.warning(
                        "[SPECIALIST_NODE] Re-dispatch cap hit for %s on "
                        "step %d (count=%d, cap=%d) -> routing to replan",
                        specialist_name,
                        active_step.step_index,
                        prior,
                        _MAX_DISPATCHES_PER_SPECIALIST,
                    )
                    guidance = (
                        f"{specialist_name} has already been dispatched for "
                        f"plan step {active_step.step_index + 1} and must not "
                        "be re-dispatched for the same step. The plan as "
                        "written is looping. Call request_replan to revise "
                        "the remaining steps, or if the findings so far "
                        "answer the user, respond now without delegating "
                        "further."
                    )
                    return Command(
                        update={
                            "active_agent": "supervisor",
                            "supervisor_iterations": state.get(
                                "supervisor_iterations", 0
                            )
                            + 1,
                            "messages": [SystemMessage(content=guidance)],
                        },
                        goto="supervisor",
                    )

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
                    nxt = active_plan.get_next_pending_step()
                    if nxt is not None:
                        guidance = (
                            f"No pending plan step is assigned to "
                            f"{specialist_name}. The NEXT plan step is "
                            f"step {nxt.step_index + 1}/{len(active_plan.steps)} "
                            f"assigned to {nxt.specialist}: "
                            f"{nxt.task_description}. "
                            f"Call handoff_to_{nxt.specialist} next."
                        )
                    else:
                        guidance = (
                            "All plan steps are resolved (some may have "
                            "failed). Respond to the user with the findings "
                            "gathered; do NOT delegate further."
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
            # Share recent ask_user Q&A the supervisor already gathered so the
            # message-isolated specialist does NOT re-ask answered questions.
            # Capped (default 6 pairs) to avoid re-opening the specialist
            # context-token bloat regression (memory 20 / commit 58a642c2).
            # Injected at the TOP of the assignment (ahead of "## Your
            # Assignment") with an imperative header: GLM-4.7 was treating the
            # gathered block as background when it sat at the end of a long
            # assignment and re-asking answered questions anyway (e2e
            # regression after FIX A).
            _gathered_qa, _gathered_pairs = _build_gathered_context_block(
                state.get("messages", [])
            )
            if _gathered_pairs:
                # Observability: confirm injection happened + how many pairs.
                logger.info(
                    "[SPECIALIST_ASSIGNMENT] %s: injected %d gathered "
                    "ask_user answer(s) (first: %.60s)",
                    specialist_name,
                    len(_gathered_pairs),
                    _gathered_pairs[0][0],
                )

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

            # Prepend the gathered context so it is the FIRST thing in the
            # specialist's assignment (most prominent position).
            if _gathered_qa is not None:
                assignment_block = f"{_gathered_qa}\n\n{assignment_block}"

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

            # Specialists get their OWN (much lower) tool-iteration budget — NOT
            # the supervisor's.  A specialist does a focused 2-4 tool calls/step;
            # inheriting the supervisor's flat-25 default let its ReAct loop
            # accumulate tool CALL+RESULT mass that drove GLM latency into the
            # 120s active-time timeout.  See AI_SPECIALIST_MAX_TOOL_ITERATIONS
            # (app/ai/config.py).  The supervisor's own budget is unaffected.
            max_iterations = AI_SPECIALIST_MAX_TOOL_ITERATIONS
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
                stop_evt = self.context._stop_event
                result = await _invoke_specialist_with_retry(
                    lambda: specialist_graph.ainvoke(
                        {
                            "messages": isolated_messages,
                            "tool_call_count": 0,
                            "max_tool_iterations": max_iterations,
                            "next": "agent",
                        },
                        # ``recursion_limit`` must exceed ``max_tool_iterations``:
                        # each tool-call cycle (agent -> tools -> agent) plus the
                        # middleware wrapper hooks consumes multiple graph steps,
                        # so a 1:1 ratio would prematurely GraphRecursionError
                        # before the ``should_continue`` tool-count cap binds.
                        # Mirrors the supervisor's ``recursion_limit * 5`` rule
                        # (agent_service.py); ``max_iterations`` is the real cap.
                        config={"recursion_limit": max_iterations * 5},
                    ),
                    specialist_name=specialist_name,
                    max_retries=max_retries,
                    timeout=float(settings.AI_SPECIALIST_STEP_TIMEOUT),
                    execution_id=(
                        self._event_bus.execution_id if self._event_bus else None
                    ),
                    should_stop=(
                        (lambda: bool(stop_evt.is_set()))
                        if stop_evt is not None
                        else None
                    ),
                )
            except ExecutionStoppedError:
                # A user-initiated stop must propagate up so the graph
                # terminates cleanly — do NOT compile it into a briefing
                # error (that would mask the stop and keep the graph alive).
                raise
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
                # Default routing: back to the supervisor.  The pure non-plan
                # branch below may override this to END on the 2nd consecutive
                # failure of the same specialist to guarantee termination.
                _failure_goto = "supervisor"
                if active_step is not None and active_plan is not None:
                    active_plan.mark_step_failed(
                        active_step.step_index, f"Specialist error: {exc}"
                    )
                    error_update["plan_data"] = active_plan.model_dump()
                    # Increment the per-(specialist, step) dispatch counter so a
                    # failed step that gets re-dispatched is caught by the cap.
                    _fkey = f"{specialist_name}|{active_step.step_index}"
                    error_update["specialist_dispatch_counts"] = {
                        _fkey: state.get("specialist_dispatch_counts", {}).get(_fkey, 0)
                        + 1
                    }
                    self._publish_plan_update(active_plan)
                    # Inject guidance so the supervisor knows how to proceed
                    # after a failed step (mirrors the success path's
                    # plan_msg injection).  ``_build_failure_nudge`` decides
                    # between the "pending steps remain" and "plan ended in
                    # failure" branches and always forces the supervisor to
                    # inform the user of the failure -- unlike the old weak
                    # directive which permitted a generic "awaiting results"
                    # answer.
                    guidance = _build_failure_nudge(
                        active_plan, specialist_name, str(exc)
                    )
                    error_update["messages"] = [SystemMessage(content=guidance)]
                elif active_step is None and active_plan is None:
                    # PURE non-plan mode: bound the failure loop.  Track
                    # consecutive failures per specialist in a dedicated field
                    # and force-end the graph on the 2nd failure so a weak
                    # supervisor cannot re-dispatch a failing specialist until
                    # ``max_supervisor_iterations`` (~5x120s timeouts).
                    decision = _decide_nonplan_failure_action(
                        specialist_name=specialist_name,
                        failure_counts=state.get("specialist_failure_counts", {}),
                        error_message=str(exc),
                    )
                    error_update["specialist_failure_counts"] = (
                        decision.failure_counts_update
                    )
                    error_update["messages"] = [SystemMessage(content=decision.message)]
                    _failure_goto = decision.goto

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

                return Command(update=error_update, goto=_failure_goto)

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
                active_plan.mark_step_completed(
                    active_step.step_index,
                    summary,
                    delegation_notes=parsed.get("delegation_notes"),
                )
                cmd_update["plan_data"] = active_plan.model_dump()
                cmd_update["completed_steps"] = state.get("completed_steps", set()) | {
                    active_step.step_index
                }
                cmd_update["current_step_index"] = active_step.step_index
                # Increment the per-(specialist, step) dispatch counter so the
                # re-dispatch cap can detect a repeat dispatch of the same step.
                _dkey = f"{specialist_name}|{active_step.step_index}"
                cmd_update["specialist_dispatch_counts"] = {
                    _dkey: state.get("specialist_dispatch_counts", {}).get(_dkey, 0) + 1
                }
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
                        f"Compare the next step's task to the result above. If the result "
                        f"already covers that task (redundant/already accomplished) or "
                        f"contradicts it, you MUST call request_replan instead of delegating. "
                        f"Only delegate if the next step genuinely needs work the findings do "
                        f"not already provide."
                    )
                else:
                    plan_msg = _build_completion_nudge(active_plan, cleaned_findings)
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
