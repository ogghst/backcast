"""Custom Entity Template Service - versionable entity management.

Mirrors `app/services/cost_element_type_service.py` (Versionable, NOT
Branchable, org-scoped). Two additions over CostElementTypeService:

1. `field_definitions` is validated at create/update time via the OO field
   registry (`build_field`) so malformed specs (unknown type / missing
   code) are rejected at admin-time rather than at first entity write.
2. `target_entity_type` is immutable post-create (analysis P6); an update
   that supplies a different value is rejected with a ValueError -> 400.
"""

from datetime import datetime
from typing import Any, cast
from uuid import UUID, uuid4

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.temporal_queries import is_current_version
from app.core.versioning.commands import (
    CreateVersionCommand,
    SoftDeleteCommand,
    UpdateVersionCommand,
)
from app.core.versioning.enums import BranchMode
from app.core.versioning.service import TemporalService
from app.models.custom_fields.registry import build_field
from app.models.domain.custom_entity_template import CustomEntityTemplate
from app.models.schemas.custom_entity_template import (
    CustomEntityTemplateCreate,
    CustomEntityTemplateUpdate,
)

#: target_entity_type discriminator whitelist (mirrors model + analysis section 3).
_ALLOWED_TARGET_ENTITY_TYPES = frozenset(
    {"PROJECT", "WBS_ELEMENT", "WORK_PACKAGE", "CHANGE_ORDER"}
)


def _validate_field_definitions(field_definitions: Any) -> None:
    """Validate a field_definitions payload via the OO field registry.

    The versioning raw-INSERT JSONB guard requires a DICT, and every spec
    must be reconstructable through `build_field` (rejects unknown types /
    missing code / malformed spec) so admin-time mistakes never reach the
    entity write path. Errors are collected and raised together.
    """
    if not isinstance(field_definitions, dict):
        raise ValueError("field_definitions must be a dict keyed by field code")

    errors: list[str] = []
    for code, spec in field_definitions.items():
        if not isinstance(spec, dict):
            errors.append(f"field '{code}': spec must be a dict")
            continue
        try:
            build_field({**spec, "code": code})
        except (ValueError, TypeError) as exc:
            errors.append(f"field '{code}': {exc}")
    if errors:
        raise ValueError("Invalid field_definitions: " + "; ".join(errors))


class CustomEntityTemplateService(TemporalService[CustomEntityTemplate]):  # type: ignore[type-var,unused-ignore]
    """Service for Custom Entity Template management (versionable, not branchable)."""

    def __init__(self, db: AsyncSession):
        """Initialize service with database session.

        Args:
            db: Async database session
        """
        super().__init__(CustomEntityTemplate, db)

    async def create(  # type: ignore[override]
        self, type_in: CustomEntityTemplateCreate, actor_id: UUID
    ) -> CustomEntityTemplate:
        """Create new custom entity template using CreateVersionCommand."""
        type_data = type_in.model_dump(exclude_unset=True)
        root_id = type_in.custom_entity_template_id or uuid4()
        type_data["custom_entity_template_id"] = root_id

        # Extract control_date from schema if present (for seeding)
        control_date = getattr(type_in, "control_date", None)

        # Remove control_date from data to avoid duplicate kwarg error
        type_data.pop("control_date", None)

        # 1. Validate target_entity_type
        if type_in.target_entity_type not in _ALLOWED_TARGET_ENTITY_TYPES:
            raise ValueError(
                f"Invalid target_entity_type: {type_in.target_entity_type}. "
                f"Allowed: {sorted(_ALLOWED_TARGET_ENTITY_TYPES)}"
            )

        # 2. Validate field_definitions via the OO field registry
        _validate_field_definitions(type_in.field_definitions)

        # 3. Validate OrganizationalUnit existence (Application-level Integrity)
        from app.models.domain.organizational_unit import OrganizationalUnit

        dept_exists = await self.session.execute(
            select(OrganizationalUnit.id)
            .where(
                OrganizationalUnit.organizational_unit_id
                == type_in.organizational_unit_id,
                is_current_version(
                    OrganizationalUnit.valid_time, OrganizationalUnit.deleted_at
                ),
            )
            .limit(1)
        )
        if not dept_exists.scalar_one_or_none():
            raise ValueError(
                f"OrganizationalUnit {type_in.organizational_unit_id} not found"
            )

        cmd = CreateVersionCommand(
            entity_class=CustomEntityTemplate,  # type: ignore[type-var,unused-ignore]
            root_id=root_id,
            actor_id=actor_id,
            control_date=control_date,
            **type_data,
        )
        return await cmd.execute(self.session)

    async def update(  # type: ignore[override]
        self,
        custom_entity_template_id: UUID,
        type_in: CustomEntityTemplateUpdate,
        actor_id: UUID,
    ) -> CustomEntityTemplate:
        """Update custom entity template using UpdateVersionCommand.

        `target_entity_type` is immutable post-create (analysis P6): a
        different value is rejected with a ValueError (-> 400).
        """
        update_data = type_in.model_dump(exclude_unset=True)

        # Custom command class to handle multi-word entity name
        class CustomEntityTemplateUpdateCommand(
            UpdateVersionCommand[CustomEntityTemplate]  # type: ignore[type-var,unused-ignore]
        ):
            def _root_field_name(self) -> str:
                return "custom_entity_template_id"

        # Extract control_date from schema
        control_date = getattr(type_in, "control_date", None)
        update_data.pop("control_date", None)

        # Enforce target_entity_type immutability
        if "target_entity_type" in update_data:
            existing = await self.get_by_id(custom_entity_template_id)
            if existing is None:
                raise ValueError(
                    f"CustomEntityTemplate {custom_entity_template_id} not found"
                )
            if update_data["target_entity_type"] != existing.target_entity_type:
                raise ValueError("target_entity_type is immutable post-create")
            # Drop the unchanged value so the command sees no-op cleanly.
            update_data.pop("target_entity_type")

        # Validate field_definitions if provided
        if "field_definitions" in update_data:
            _validate_field_definitions(update_data["field_definitions"])

        cmd = CustomEntityTemplateUpdateCommand(
            entity_class=CustomEntityTemplate,  # type: ignore[type-var,unused-ignore]
            root_id=custom_entity_template_id,
            actor_id=actor_id,
            control_date=control_date,
            **update_data,
        )
        return await cmd.execute(self.session)

    async def soft_delete(
        self,
        custom_entity_template_id: UUID,
        actor_id: UUID,
        control_date: datetime | None = None,
    ) -> None:
        """Soft delete custom entity template using SoftDeleteCommand."""

        class CustomEntityTemplateSoftDeleteCommand(
            SoftDeleteCommand[CustomEntityTemplate]  # type: ignore[type-var,unused-ignore]
        ):
            def _root_field_name(self) -> str:
                return "custom_entity_template_id"

        cmd = CustomEntityTemplateSoftDeleteCommand(
            entity_class=CustomEntityTemplate,  # type: ignore[type-var,unused-ignore]
            root_id=custom_entity_template_id,
            actor_id=actor_id,
            control_date=control_date,
        )
        await cmd.execute(self.session)

    async def get_by_id(
        self, custom_entity_template_id: UUID
    ) -> CustomEntityTemplate | None:
        """Get current custom entity template by root ID with creator name."""
        from app.models.domain.user import User

        UserAlias = cast(Any, User)
        creator_subq = (
            select(UserAlias.user_id, UserAlias.full_name)
            .distinct(UserAlias.user_id)
            .order_by(UserAlias.user_id, UserAlias.transaction_time.desc())
            .subquery("creator_lookup")
        )

        stmt = (
            select(
                CustomEntityTemplate,
                creator_subq.c.full_name.label("created_by_name"),
            )
            .outerjoin(
                creator_subq,
                CustomEntityTemplate.created_by == creator_subq.c.user_id,
            )
            .where(
                CustomEntityTemplate.custom_entity_template_id
                == custom_entity_template_id,
                is_current_version(
                    CustomEntityTemplate.valid_time,
                    CustomEntityTemplate.deleted_at,
                ),
            )
            .order_by(CustomEntityTemplate.valid_time.desc())
            .limit(1)
        )
        result = await self.session.execute(stmt)
        row = result.first()
        if row is None:
            return None
        entity = row[0]
        entity.created_by_name = row[1]
        return entity

    async def get_custom_entity_templates(
        self,
        filters: dict[str, Any] | None = None,
        skip: int = 0,
        limit: int = 100000,
        search: str | None = None,
        filter_string: str | None = None,
        sort_field: str | None = None,
        sort_order: str = "asc",
    ) -> tuple[list[CustomEntityTemplate], int]:
        """Get custom entity templates with server-side features."""
        from sqlalchemy import and_, or_

        from app.core.filtering import FilterParser

        stmt = select(CustomEntityTemplate).where(
            is_current_version(
                CustomEntityTemplate.valid_time, CustomEntityTemplate.deleted_at
            )
        )

        if filters:
            if "organizational_unit_id" in filters:
                stmt = stmt.where(
                    CustomEntityTemplate.organizational_unit_id
                    == filters["organizational_unit_id"]
                )
            if "target_entity_type" in filters:
                stmt = stmt.where(
                    CustomEntityTemplate.target_entity_type
                    == filters["target_entity_type"]
                )

        if search:
            search_term = f"%{search}%"
            stmt = stmt.where(
                or_(
                    CustomEntityTemplate.code.ilike(search_term),
                    CustomEntityTemplate.name.ilike(search_term),
                )
            )

        if filter_string:
            allowed_fields = ["code", "name", "target_entity_type"]
            parsed_filters = FilterParser.parse_filters(filter_string)
            filter_expressions = FilterParser.build_sqlalchemy_filters(
                cast(Any, CustomEntityTemplate),
                parsed_filters,
                allowed_fields=allowed_fields,
            )
            if filter_expressions:
                stmt = stmt.where(and_(*filter_expressions))

        # Get total count
        count_stmt = select(func.count()).select_from(stmt.subquery())
        total_result = await self.session.execute(count_stmt)
        total = total_result.scalar_one()

        # Apply sorting
        if sort_field and hasattr(CustomEntityTemplate, sort_field):
            column = getattr(CustomEntityTemplate, sort_field)
            if sort_order.lower() == "desc":
                stmt = stmt.order_by(column.desc())
            else:
                stmt = stmt.order_by(column.asc())
        else:
            stmt = stmt.order_by(CustomEntityTemplate.name.asc())

        stmt = stmt.offset(skip).limit(limit)

        # Build a separate fetch statement with creator-name outerjoin so the
        # count above is unaffected and created_by_name is populated per row.
        from app.models.domain.user import User

        UserAlias = cast(Any, User)
        creator_subq = (
            select(UserAlias.user_id, UserAlias.full_name)
            .distinct(UserAlias.user_id)
            .order_by(UserAlias.user_id, UserAlias.transaction_time.desc())
            .subquery("creator_lookup")
        )
        fetch_stmt = stmt.with_only_columns(
            CustomEntityTemplate,
            creator_subq.c.full_name.label("created_by_name"),
        ).outerjoin(
            creator_subq,
            CustomEntityTemplate.created_by == creator_subq.c.user_id,
        )

        result = await self.session.execute(fetch_stmt)
        items: list[CustomEntityTemplate] = []
        for row in result.all():
            entity = row[0]
            entity.created_by_name = row[1]
            items.append(entity)
        return items, total

    async def list(
        self, filters: dict[str, Any] | None = None, skip: int = 0, limit: int = 100000
    ) -> list[CustomEntityTemplate]:
        """Legacy list method (backward compatibility)."""
        items, _ = await self.get_custom_entity_templates(
            filters=filters, skip=skip, limit=limit
        )
        return items

    async def get_custom_entity_template_as_of(
        self,
        custom_entity_template_id: UUID,
        as_of: datetime,
        branch: str = "main",
        branch_mode: BranchMode | None = None,
    ) -> CustomEntityTemplate | None:
        """Get custom entity template as it was at specific timestamp.

        Provides System Time Travel semantics for single-entity queries.
        Uses ISOLATED mode by default (only searches in specified branch).
        Use BranchMode.MERGED to fall back to main branch if not found.

        Args:
            custom_entity_template_id: The unique identifier of the template
            as_of: Timestamp to query (historical state)
            branch: Branch name to query (default: "main")
            branch_mode: Resolution mode for branches
                - None/ISOLATED: Only return from specified branch (default)
                - MERGED: Fall back to main if not found on branch

        Returns:
            CustomEntityTemplate if found at the specified timestamp,
            None otherwise.
        """
        return await self.get_as_of(
            custom_entity_template_id, as_of, branch, branch_mode
        )
