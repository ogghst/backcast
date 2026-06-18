"""Per-turn briefing injection middleware for the supervisor agent.

The supervisor's briefing is the single source of truth for what specialists
have established. Previously it was injected ONCE as a persisted ``SystemMessage``
from ``_briefing_update`` at graph start — but the ``messages`` reducer is
``operator.add`` (``BackcastSupervisorState``), so a one-shot message can never
be refreshed in place: it permanently contradicted the live briefing results
(a stale "No findings yet." sitting next to current findings is context rot).

This middleware renders ``state["briefing_data"]`` into the supervisor's
``request.system_message.text`` between stable sentinels
(``<!--BRIEFING_START-->`` / ``<!--BRIEFING_END-->``) on EVERY model call,
replacing that span each turn. It mutates the REQUEST (via
``request.override``), NEVER ``state["messages"]`` — so it is reducer-safe.

The companion ``_render_briefing_block`` helper and the
``_BRIEFING_CONTEXT_PREFIX`` constant live here (rather than in the
orchestrator) so the orchestrator can import them without an import cycle.
"""

from __future__ import annotations

import logging
import re
from typing import Any

from langchain.agents.middleware.types import AgentMiddleware, ModelRequest
from langchain_core.messages import SystemMessage

from app.ai.briefing import BriefingDocument

logger = logging.getLogger(__name__)

#: Header prefix for the rendered briefing block. Re-exported so existing
#: callers that reference it by name can import it from this module.
_BRIEFING_CONTEXT_PREFIX = "## Current Briefing\n\n"

#: Sentinel markers delimiting the briefing span in the system prompt. Using
#: a regex DOTALL span replace (not substring membership) keeps the block
#: refreshed to the CURRENT briefing every turn and never duplicated, even
#: when the briefing text grows or shrinks.
_BRIEFING_START = "<!--BRIEFING_START-->"
_BRIEFING_END = "<!--BRIEFING_END-->"

#: Compiled span regex (non-greedy, DOTALL so the span may include newlines).
_BRIEFING_BLOCK_RE = re.compile(
    rf"{re.escape(_BRIEFING_START)}.*?{re.escape(_BRIEFING_END)}",
    re.DOTALL,
)


def _render_briefing_block(briefing_data: dict[str, Any] | None) -> str:
    """Render the current briefing as the per-turn briefing block text.

    Reuses :meth:`BriefingDocument.from_state` /
    :meth:`BriefingDocument.to_markdown`. When the briefing has no sections
    yet (graph start, before any specialist contributes) renders the
    ``"No findings yet."`` placeholder so the block is never empty.

    Args:
        briefing_data: Serialized ``BriefingDocument`` dict from graph state,
            or ``None``/empty when no briefing exists yet.

    Returns:
        The briefing block text WITHOUT surrounding sentinels (the caller —
        the middleware — wraps it). Always starts with
        ``_BRIEFING_CONTEXT_PREFIX``.
    """
    if not briefing_data:
        return f"{_BRIEFING_CONTEXT_PREFIX}No findings yet."
    doc = BriefingDocument.from_state(briefing_data)
    body = doc.to_markdown() if doc.sections else "No findings yet."
    return f"{_BRIEFING_CONTEXT_PREFIX}{body}"


class BriefingContextMiddleware(AgentMiddleware):
    """Inject the current briefing into the supervisor system prompt per turn.

    On every ``awrap_model_call`` it reads ``state["briefing_data"]``,
    renders it via :func:`_render_briefing_block`, and writes it into
    ``request.system_message.text`` between the briefing sentinels —
    replacing any prior briefing span, or appending a fresh one. Mutates the
    REQUEST only (never ``state["messages"]``), so it is safe under the
    ``operator.add`` messages reducer.
    """

    async def awrap_model_call(
        self,
        request: ModelRequest[Any],
        handler: Any,
    ) -> Any:
        state = dict(request.state) if request.state else {}
        briefing_data_raw = state.get("briefing_data")
        briefing_data: dict[str, Any] | None = (
            briefing_data_raw if isinstance(briefing_data_raw, dict) else None
        )

        block = _render_briefing_block(briefing_data)
        wrapped = f"{_BRIEFING_START}\n{block}\n{_BRIEFING_END}"

        current_prompt = request.system_message.text if request.system_message else ""

        if _BRIEFING_START in current_prompt:
            # Replace the existing briefing span with the current one.
            new_prompt = _BRIEFING_BLOCK_RE.sub(wrapped, current_prompt)
        elif current_prompt:
            new_prompt = current_prompt + "\n\n" + wrapped
        else:
            new_prompt = wrapped

        request = request.override(system_message=SystemMessage(content=new_prompt))
        return await handler(request)


__all__ = [
    "BriefingContextMiddleware",
    "_BRIEFING_CONTEXT_PREFIX",
    "_render_briefing_block",
]
