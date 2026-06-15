"""Safe braced-tag substitution for AI prompt templates.

Single-pass substitution of allowlisted ``{tag}`` placeholders.  This replaces
``str.format()`` and ``str.replace("{tag}", ..., 1)`` at sites that inject
dynamic content (user requests, specialist findings, ``PlanDocument.to_prompt_text``,
``BriefingDocument.to_markdown``, DB-stored admin templates).

Design properties vs ``str.format()``:

- **Never raises.** Stray ``{`` / ``}``, unknown tags, ``{name.attr}``,
  ``{x[0]}``, ``{!r}``, ``{:fmt}`` and unmatched braces are all left verbatim
  instead of raising ``KeyError`` / ``IndexError`` / ``ValueError``.
- **Single pass.** ``re.sub`` scans the *original* template only.  Injected
  values are placed into the output and are *never* re-scanned, so a value
  containing ``{tag}`` or ``{__class__}`` is inert.  This is the core
  robustness property: it makes dynamic content with special characters safe.
- **No ``{{`` escaping** (deliberate divergence from ``str.format``).  No
  current template uses it; ``{{`` is left verbatim as two literal braces.
  Sites that previously used ``.replace()`` never honored ``{{`` either, so
  this is behavior-preserving for them.
- **Unknown tags left verbatim** (logged at ``DEBUG`` only, never raised).
  This enables two-pass resolution -- e.g. the supervisor build resolves
  ``{specialist_section}`` and deliberately leaves ``{plan_section}`` for the
  ``PlanAwareToolMiddleware`` pass -- and makes DB templates with stray or
  unknown braces harmless.

Non-issue note: literal ``handoff_to_{specialist}`` strings that appear in
delegation prompt sections are LLM-facing prose appended via ``+``/``+=``; they
are never passed through :func:`render_prompt`, and ``{specialist}`` is not in
any call site's allowlist, so they are inert.  Do not "fix" them.
"""

from __future__ import annotations

import logging
import re

logger = logging.getLogger(__name__)

# Matches ``{tag}`` where tag is one or more word characters.  Crucially, this
# does NOT match ``{name.attr}``, ``{x[0]}``, ``{!r}``, ``{:fmt}``, or an
# unmatched ``{`` without a closing ``}``, so those are left untouched.
_TAG_PATTERN: re.Pattern[str] = re.compile(r"\{(\w+)\}")


def render_prompt(template: str, **values: str) -> str:
    """Substitute allowlisted ``{tag}`` placeholders in *template*.

    Performs a single pass over *template* (injected values are never
    re-scanned).  For each ``{tag}`` match, if ``tag`` is in *values* the
    match is replaced with the provided value; otherwise the match is left
    verbatim (unknown tags are logged at ``DEBUG`` and never raised).

    Args:
        template: Prompt template possibly containing ``{tag}`` placeholders.
        **values: Mapping of known tags to their substitution strings.

    Returns:
        Rendered prompt string with known tags substituted and every other
        ``{...}`` left exactly as-is.
    """

    def _replace(match: re.Match[str]) -> str:
        tag = match.group(1)
        if tag in values:
            return values[tag]
        logger.debug("render_prompt: unknown tag {%s} left verbatim", tag)
        return match.group(0)

    return _TAG_PATTERN.sub(_replace, template)


__all__ = ["render_prompt"]
