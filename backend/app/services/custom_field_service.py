"""Custom field validation service.

Single service-layer chokepoint (M1) that validates a ``{code: value}`` dict
against a :class:`~app.models.custom_fields.CustomEntityTemplate`'s ``{code:
spec}`` ``field_definitions`` snapshot. Validation is keyed by ``code`` (the
stable field identifier, not the human label) and delegates the per-type
shape/contract checks to the OO :class:`~app.models.custom_fields.FieldDefinition`
hierarchy built via :func:`build_field`.

Unknown keys are rejected (M1), required-null is rejected (D11 directive 3),
and ``formula`` fields are skipped (no stored value, m13).

Phase 1C adds the CREATE/UPDATE chokepoint: :meth:`prepare_for_create` resolves
the template by root id, captures its ``field_definitions`` as an IMMUTABLE
snapshot onto the entity row, and validates the supplied values;
:meth:`validate_for_update` validates a subsequent edit against the snapshot
captured at create (the snapshot is never refreshed — D11). The CHANGE_ORDER,
project, WBS, and work-package services all funnel through this one path.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.temporal_queries import is_current_version
from app.models.custom_fields import FieldDefinition, build_field

if TYPE_CHECKING:
    from app.models.domain.custom_entity_template import CustomEntityTemplate


class CustomFieldValidationError(ValueError):
    """A custom-field validation failure.

    Raised by the CREATE/UPDATE chokepoint (unknown key, bad value, missing
    or unknown template, unknown reference). Subclasses :class:`ValueError`
    so existing ``except ValueError`` blocks still catch it; route handlers
    map it to HTTP 400 separately from the entity-not-found ``ValueError``
    path (which maps to 404).
    """


class CustomFieldService:
    """Validates ``{code: value}`` dicts against ``{code: spec}`` definitions.

    The unified async chokepoint for custom fields. ``__init__`` accepts an
    optional ``AsyncSession`` so the per-entity write services can construct it
    once and share it with :meth:`prepare_for_create` / :meth:`validate_for_update`
    for template resolution and the :class:`ReferenceField` existence check.
    Existing no-arg construction (``CustomFieldService()``) still works —
    ``session=None`` means async checks (target existence) are skipped, which is
    the original Phase-0 behavior.
    """

    def __init__(self, session: AsyncSession | None = None) -> None:
        self.session = session

    async def validate_field_values(
        self,
        field_definitions: dict[str, Any],
        values: dict[str, Any],
        *,
        session: AsyncSession | None = None,
        actor_id: UUID | None = None,
    ) -> list[str]:
        """Validate a ``{code: value}`` dict against a template's ``{code: spec}`` field definitions.

        Single service-layer chokepoint (M1): unknown keys are rejected;
        required-null is rejected (D11 directive 3); per-field type validation
        delegates to the :class:`FieldDefinition` hierarchy. Formula fields are
        skipped (no stored value, m13).

        Args:
            field_definitions: A template's ``{code: spec}`` field-definition
                snapshot (each ``spec`` is a dict carrying at least ``"type"``
                and ``"label"``).
            values: The ``{code: value}`` dict to validate.
            session: Optional session threaded into :meth:`FieldDefinition.validate_async`
                for existence checks (e.g. :class:`ReferenceField`). Falls back
                to ``self.session`` when None.
            actor_id: Optional actor for finer RBAC inside the async checks
                (deferred for MVP — existence only).

        Returns:
            Human-readable error strings (empty list if valid).
        """
        errors: list[str] = []

        # Rebuild the FieldDefinition per code. A malformed template spec
        # surfaces as a validation error rather than crashing the write.
        fields: dict[str, FieldDefinition] = {}
        for code, spec in field_definitions.items():
            try:
                fields[code] = build_field({**spec, "code": code})
            except (ValueError, KeyError) as e:
                errors.append(str(e))

        # M1: unknown keys (present in values, absent from definitions) are
        # rejected — values must conform to the bound template's snapshot.
        unknown = set(values) - set(fields)
        if unknown:
            errors.append(f"Unknown custom field keys: {sorted(unknown)}")

        # Resolve the session for async checks: explicit arg wins, else the
        # service's own session (set in __init__ by the write services).
        async_session = session if session is not None else self.session

        for code, field in fields.items():
            # m13: formula fields carry no stored value; skip them entirely.
            if field.type_code == "formula":
                continue

            value = values.get(code)

            # D11 directive 3: a required field with a null/absent value is
            # rejected. ``None`` for an optional field means "absent" and is
            # left to the field's own validate() (which returns [] for None).
            if field.required and value is None:
                errors.append(f"Field '{code}' is required")
                continue

            if value is None:
                continue

            errors.extend(field.validate(value))
            errors.extend(
                await field.validate_async(
                    value, session=async_session, actor_id=actor_id
                )
            )

        return errors

    async def resolve_template(
        self, template_root_id: UUID
    ) -> CustomEntityTemplate | None:
        """Resolve the current (open valid_time, non-deleted) version of a template.

        Mirrors the lookup the CO service used to inline. Used by
        :meth:`prepare_for_create` to both validate the supplied values and
        capture the snapshot at create time. ``None`` is returned when the
        template root id has no current version (deleted or never existed).
        """
        from app.models.domain.custom_entity_template import CustomEntityTemplate

        stmt = (
            select(CustomEntityTemplate)
            .where(
                CustomEntityTemplate.custom_entity_template_id == template_root_id,
                is_current_version(
                    CustomEntityTemplate.valid_time,
                    CustomEntityTemplate.deleted_at,
                ),
            )
            .order_by(CustomEntityTemplate.valid_time.desc())
            .limit(1)
        )
        result = await self.session.execute(stmt)  # type: ignore[union-attr]
        return result.scalar_one_or_none()

    async def prepare_for_create(
        self,
        *,
        template_root_id: UUID | None,
        custom_fields: dict[str, Any] | None,
        actor_id: UUID,
    ) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
        """Resolve the template, validate the supplied values, capture the snapshot.

        The CREATE chokepoint. Returns ``(custom_fields_to_store, snapshot)``
        where ``snapshot`` is the template's ``field_definitions`` dict captured
        at create time. The snapshot is IMMUTABLE thereafter (the EVCS clone()
        carries it forward); update-time validation reuses it via
        :meth:`validate_for_update` rather than re-resolving the template (D11).

        Behavior:
            * ``template_root_id is None``: if ``custom_fields`` is non-empty →
              raise ValueError (values without a template are rejected);
              otherwise return ``(custom_fields, None)`` (no snapshot captured).
            * ``template_root_id`` resolves to no current version → raise
              ValueError (template root id points at a deleted/unknown template).
            * Else: ``snapshot = dict(template.field_definitions)``; if
              ``custom_fields`` is non-empty, validate against the snapshot
              (raise ValueError joining errors); return ``(custom_fields, snapshot)``.

        Args:
            template_root_id: Root id of the bound CustomEntityTemplate.
            custom_fields: The ``{code: value}`` dict supplied at create.
            actor_id: Actor for the async field checks.

        Returns:
            ``(custom_fields_to_store, snapshot)``.

        Raises:
            CustomFieldValidationError: values without a template, unknown
                template root, or validation errors.
        """
        if template_root_id is None:
            if custom_fields:
                raise CustomFieldValidationError(
                    "custom_fields require a custom_entity_template_root_id"
                )
            return custom_fields, None

        template = await self.resolve_template(template_root_id)
        if template is None:
            raise CustomFieldValidationError(
                f"CustomEntityTemplate {template_root_id} not found"
            )

        snapshot = dict(template.field_definitions)

        if custom_fields:
            errors = await self.validate_field_values(
                snapshot, custom_fields, actor_id=actor_id
            )
            if errors:
                raise CustomFieldValidationError("; ".join(errors))

        return custom_fields, snapshot

    async def validate_for_update(
        self,
        *,
        snapshot: dict[str, Any] | None,
        custom_fields: dict[str, Any] | None,
        actor_id: UUID,
    ) -> None:
        """Validate a custom_fields edit against the snapshot captured at create.

        The UPDATE chokepoint. D11: callers only invoke this when the
        ``custom_fields`` key is PRESENT in the update payload (absent = skip).
        A present ``{}`` is trivially valid; a present dict is validated against
        the snapshot. The snapshot is the IMMUTABLE one captured at create — it
        is never refreshed here.

        Args:
            snapshot: The entity row's ``custom_field_definitions_snapshot``
                (captured at create; ``None`` if no template was bound).
            custom_fields: The ``{code: value}`` dict supplied at update.
            actor_id: Actor for the async field checks.

        Raises:
            CustomFieldValidationError: validation errors joined into one message.
        """
        if custom_fields is None:
            return
        if snapshot is None:
            # No snapshot was captured at create (no template was bound). An
            # empty dict is trivially valid; a non-empty dict cannot be
            # validated against anything, so reject it.
            if custom_fields:
                raise CustomFieldValidationError(
                    "custom_fields supplied but no field-definitions snapshot "
                    "was captured at create"
                )
            return

        errors = await self.validate_field_values(
            snapshot, custom_fields, actor_id=actor_id
        )
        if errors:
            raise CustomFieldValidationError("; ".join(errors))
