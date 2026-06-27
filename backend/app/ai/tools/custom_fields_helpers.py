"""ai_visible filter chokepoint for surfacing custom fields to the LLM (D8).

This module is the SINGLE place that decides which stored custom-field values
reach the AI. A field's value (or label) is surfaced ONLY when its spec in the
entity's captured ``custom_field_definitions_snapshot`` carries
``ai_visible === True``. This is INDEPENDENT of the UI ``searchable`` flag
(analysis decision D8) and closes the confidentiality regression M5: an
admin explicitly opts each field into AI visibility at template-definition
time, default OFF.

The helpers here are pure (no DB / session): callers pass the already-fetched
entity's ``custom_fields`` ({code: value}) and ``custom_field_definitions_snapshot``
({code: spec}). Both are JSONB columns on the versioned entity row.

See ``docs/03-project-plan/iterations/2026-06-24-custom-fields-analysis/``
section 7.2 and decision D8.
"""

from __future__ import annotations

from typing import Any


def filter_ai_visible_custom_fields(
    custom_fields: dict[str, Any] | None,
    snapshot: dict[str, Any] | None,
) -> dict[str, Any]:
    """Return ``{code: value}`` ONLY for codes whose snapshot spec is ai_visible.

    The single chokepoint enforcing D8. Conservative by design:

    * ``snapshot`` is ``None`` or empty → return ``{}`` (nothing is surfaced;
      an entity with no captured definitions has no AI-visible fields).
    * A code present in ``custom_fields`` but absent from the snapshot → not
      surfaced (the snapshot is the authority; orphan values are hidden).
    * A code whose snapshot spec lacks ``ai_visible`` or has it falsy → not
      surfaced.
    * Only ``spec.get("ai_visible") is True`` (strict truthiness on the stored
      JSONB bool) surfaces the value.
    * Phase 3 — a RETIRED field is never surfaced (dead; the LLM must not see
      or set it). DEPRECATED fields stay readable so existing entities keep
      their data and the manifest can flag the deprecation; the write path
      (M2) will reject any attempt to SET a deprecated field.

    Args:
        custom_fields: The entity's stored ``{code: value}`` dict (may be None).
        snapshot: The entity's captured ``{code: spec}`` definitions dict
            (may be None). Each ``spec`` is a plain dict; only its
            ``ai_visible`` key is read here.

    Returns:
        A new ``{code: value}`` dict containing only ai_visible fields.
    """
    if not custom_fields or not snapshot:
        return {}

    surfaced: dict[str, Any] = {}
    for code, value in custom_fields.items():
        spec = snapshot.get(code)
        if not isinstance(spec, dict):
            continue
        if spec.get("ai_visible") is not True:
            continue
        # Phase 3: retired fields never reach the LLM (dead). Deprecated stays
        # readable so existing entities keep surfacing their data; the write
        # gate (M2) blocks any attempt to set a deprecated field.
        if spec.get("status") == "retired":
            continue
        surfaced[code] = value
    return surfaced


def ai_visible_field_manifest(
    snapshot: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    """Project a snapshot's ai_visible field specs into a discovery manifest.

    Used by the ``get_custom_field_definitions`` discovery tool. Returns a list
    of ``{code, label, type, required, status}`` dicts for ONLY the ai_visible
    fields, so the LLM can learn the available fields before creating an entity
    WITHOUT ever seeing non-ai_visible field labels (D8: labels are also gated).

    Phase 3 — RETIRED fields are EXCLUDED entirely (dead; the LLM must not see
    or set them). DEPRECATED fields appear with ``status="deprecated"`` so the
    LLM knows not to set them (the M2 write gate will reject the write anyway,
    but surfacing the status avoids a wasted tool call).

    Args:
        snapshot: A ``{code: spec}`` definitions dict (a template's
            ``field_definitions`` or an entity's captured snapshot).

    Returns:
        List of manifest dicts, one per ai_visible non-retired field, sorted
        by code for deterministic output.
    """
    if not snapshot:
        return []

    manifest: list[dict[str, Any]] = []
    for code, spec in snapshot.items():
        if not isinstance(spec, dict):
            continue
        if spec.get("ai_visible") is not True:
            continue
        # Phase 3: retired fields are dead — never surface them to the LLM.
        if spec.get("status") == "retired":
            continue
        manifest.append(
            {
                "code": code,
                "label": spec.get("label", code),
                "type": spec.get("type"),
                "required": bool(spec.get("required", False)),
                "status": spec.get("status", "active"),
            }
        )
    manifest.sort(key=lambda f: f["code"])
    return manifest
