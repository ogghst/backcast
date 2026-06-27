"""Idempotent seeder for default CustomEntityTemplate rows (custom-fields Phase 0).

Creates the default CHANGE_ORDER template on every application startup, skipping
silently if it already exists. Mirrors the create-or-skip pattern used by
``seed_users_rbac.py``. Safe to call from both the lifespan startup path and the
destructive reseed pipeline.
"""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

SYSTEM_ACTOR = UUID("00000000-0000-0000-0000-000000000001")
GLOBAL_ORG_UNIT_ID = UUID("00000000-0000-4000-8000-000000000001")
DEFAULT_CHANGE_ORDER_TEMPLATE_ROOT = UUID("00000000-0000-4000-8000-000000000201")

# field_definitions MUST be a DICT keyed by field code (NOT a list) -- the
# versioning raw-INSERT JSONB guard only serializes isinstance(dict). Keys are
# field codes; values describe the field's type/validation/labels.
DEFAULT_CHANGE_ORDER_FIELD_DEFINITIONS: dict[str, dict[str, object]] = {
    "reason": {
        "type": "text",
        "label": "Change Reason",
        "required": True,
        "max_length": 500,
    },
    "priority": {
        "type": "select",
        "label": "Priority",
        "options": ["low", "medium", "high"],
        "default": "medium",
    },
}


async def seed_default_custom_templates(session: AsyncSession) -> None:
    """Create-or-skip the default CHANGE_ORDER CustomEntityTemplate.

    Safe on every startup. Skips silently if the GLOBAL org unit is absent (no OU
    to attach the template to -- e.g. a truly empty DB), or if the template root
    already exists.
    """
    from app.models.domain.custom_entity_template import CustomEntityTemplate
    from app.models.domain.organizational_unit import OrganizationalUnit

    # Defensive: only seed if the GLOBAL org unit exists (it does after a reseed;
    # on a truly empty DB there is no OU so we skip rather than violate NOT NULL).
    ou = (
        await session.execute(
            select(OrganizationalUnit).where(
                OrganizationalUnit.organizational_unit_id == GLOBAL_ORG_UNIT_ID
            )
        )
    ).scalar_one_or_none()
    if ou is None:
        return

    existing = (
        await session.execute(
            select(CustomEntityTemplate).where(
                CustomEntityTemplate.custom_entity_template_id
                == DEFAULT_CHANGE_ORDER_TEMPLATE_ROOT
            )
        )
    ).scalar_one_or_none()
    if existing is not None:
        return

    session.add(
        CustomEntityTemplate(
            custom_entity_template_id=DEFAULT_CHANGE_ORDER_TEMPLATE_ROOT,
            organizational_unit_id=GLOBAL_ORG_UNIT_ID,
            target_entity_type="CHANGE_ORDER",
            code="default-change-order",
            name="Default Change Order Template",
            description="Default custom fields for change orders",
            field_definitions=DEFAULT_CHANGE_ORDER_FIELD_DEFINITIONS,
            created_by=SYSTEM_ACTOR,
        )
    )
    await session.flush()
