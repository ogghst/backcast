"""Custom-field discovery tool for the AI assistant (analysis section 7.2, D8).

Surfaces the manifest of ai_visible custom-field definitions for a target
entity type (or a specific template) so a specialist can learn the available
fields BEFORE creating an entity — without baking field names into static
system prompts. Only ai_visible fields are returned (D8: labels are also
gated; a non-ai_visible field's existence is never disclosed to the LLM).

Read-only: resolves CustomEntityTemplate(s) via CustomEntityTemplateService /
CustomFieldService and projects each template's field_definitions through
``ai_visible_field_manifest``.
"""

import logging
from datetime import UTC, datetime
from typing import Annotated, Any

from langchain_core.tools import InjectedToolArg

from app.ai.tools.custom_fields_helpers import ai_visible_field_manifest
from app.ai.tools.decorator import ai_tool
from app.ai.tools.types import RiskLevel, ToolContext

logger = logging.getLogger(__name__)

#: target_entity_type discriminator whitelist (mirrors the template service).
_ALLOWED_ENTITY_TYPES = frozenset(
    {"PROJECT", "WBS_ELEMENT", "WORK_PACKAGE", "CHANGE_ORDER"}
)


@ai_tool(
    name="get_custom_field_definitions",
    description=(
        "Discover the ai_visible custom-field definitions for an entity type "
        "(or a specific template) before creating an entity. Returns each "
        "field's code/label/type/required — only fields the admin marked "
        "ai_visible. Use this to learn which custom_fields codes to pass to "
        "create_project / create_wbs_element / create_work_package / "
        "create_change_order."
    ),
    permissions=["custom-entity-template-read"],
    category="projects",
    risk_level=RiskLevel.LOW,
)
async def get_custom_field_definitions(
    entity_type: str,
    template_root_id: str | None = None,
    context: Annotated[ToolContext, InjectedToolArg] = None,  # type: ignore[assignment]
) -> dict[str, Any]:
    """Return the ai_visible custom-field manifest for an entity type.

    Resolves the template(s) and projects ONLY their ai_visible field specs
    into ``{code, label, type, required}`` entries (D8: non-ai_visible fields
    are hidden — their labels are never surfaced to the LLM).

    Args:
        entity_type: One of PROJECT, WBS_ELEMENT, WORK_PACKAGE, CHANGE_ORDER.
        template_root_id: Optional UUID of a specific CustomEntityTemplate. When
            omitted, the current (non-deleted) template(s) for the entity_type
            are returned.
        context: Injected tool execution context.

    Returns:
        Dictionary with:
            - entity_type: the resolved entity type
            - templates: list of {template_id, code, name, fields: [...]} where
              each field is {code, label, type, required} and ONLY ai_visible
              fields appear
            - total: number of templates surfaced

    Raises:
        ValueError: If entity_type is not one of the allowed discriminators.
    """
    try:
        from uuid import UUID

        from app.services.custom_entity_template_service import (
            CustomEntityTemplateService,
        )

        entity_type_upper = entity_type.strip().upper()
        if entity_type_upper not in _ALLOWED_ENTITY_TYPES:
            return {
                "error": (
                    f"Invalid entity_type: {entity_type!r}. "
                    f"Allowed: {sorted(_ALLOWED_ENTITY_TYPES)}"
                )
            }

        service = CustomEntityTemplateService(context.session)

        if template_root_id:
            # Single specific template by root id (current version).
            template = await service.get_custom_entity_template_as_of(
                UUID(template_root_id),
                # Resolve the current version: as_of now, main branch.
                as_of=datetime.now(tz=UTC),
                branch="main",
            )
            templates = [template] if template is not None else []
        else:
            # All current templates for the entity type.
            templates, _ = await service.get_custom_entity_templates(
                filters={"target_entity_type": entity_type_upper},
            )

        manifest: list[dict[str, Any]] = []
        for tpl in templates:
            fields = ai_visible_field_manifest(tpl.field_definitions)
            # Skip templates that expose no ai_visible fields — the LLM has no
            # reason to know about a template whose fields are all hidden.
            if not fields:
                continue
            manifest.append(
                {
                    "template_id": str(tpl.custom_entity_template_id),
                    "code": tpl.code,
                    "name": tpl.name,
                    "fields": fields,
                }
            )

        return {
            "entity_type": entity_type_upper,
            "templates": manifest,
            "total": len(manifest),
        }
    except ValueError as e:
        return {"error": f"Invalid input: {e}"}
    except Exception as e:
        logger.error(f"Error in get_custom_field_definitions: {e}")
        return {"error": str(e)}
