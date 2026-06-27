"""Custom field validation service.

Single service-layer chokepoint (M1) that validates a ``{code: value}`` dict
against a :class:`~app.models.custom_fields.CustomEntityTemplate`'s ``{code:
spec}`` ``field_definitions`` snapshot. Validation is keyed by ``code`` (the
stable field identifier, not the human label) and delegates the per-type
shape/contract checks to the OO :class:`~app.models.custom_fields.FieldDefinition`
hierarchy built via :func:`build_field`.

Unknown keys are rejected (M1), required-null is rejected (D11 directive 3),
and ``formula`` fields are skipped (no stored value, m13).

Phase 1C adds the CREATE chokepoint: :meth:`prepare_for_create` resolves the
template by root id, captures its ``field_definitions`` as an IMMUTABLE
snapshot onto the entity row, and validates the supplied values.
:meth:`prepare_for_update` is the UPDATE chokepoint: it refines frozen
decision D2 — a template binding is IMMUTABLE once set, but the FIRST binding
may happen on edit for a template-less existing entity (so legacy rows can be
bound without a destructive re-create). The CHANGE_ORDER, project, WBS, and
work-package services all funnel through these two paths.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.temporal_queries import is_current_version
from app.models.custom_fields import FieldDefinition, build_field

if TYPE_CHECKING:
    from app.models.domain.custom_entity_template import CustomEntityTemplate


def _custom_field_values_equal(a: Any, b: Any) -> bool:
    """Compare two custom-field values for equality via JSON-normalized form.

    Robust across str-vs-number (``"5"`` vs ``5``) and list/multiselect
    round-trips (``["a","b"]`` ordering vs sets): both sides are serialized
    with ``sort_keys=True`` and a ``str`` fallback default, so structurally
    equivalent values compare equal regardless of incidental type drift
    introduced by JSONB round-tripping or frontend echo.
    """
    return json.dumps(a, sort_keys=True, default=str) == json.dumps(
        b, sort_keys=True, default=str
    )


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
    once and share it with :meth:`prepare_for_create` /
    :meth:`prepare_for_update` for template resolution and the
    :class:`ReferenceField` existence check. Existing no-arg construction
    (``CustomFieldService()``) still works — ``session=None`` means async checks
    (target existence) are skipped, which is the original Phase-0 behavior.
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
        live_statuses: dict[str, str] | None = None,
        stored_values: dict[str, Any] | None = None,
    ) -> list[str]:
        """Validate a ``{code: value}`` dict against a template's ``{code: spec}`` field definitions.

        Single service-layer chokepoint (M1): unknown keys are rejected;
        required-null is rejected (D11 directive 3); per-field type validation
        delegates to the :class:`FieldDefinition` hierarchy. Formula fields are
        skipped (no stored value, m13).

        Phase 3 (M2) — lifecycle gate: when ``live_statuses`` is supplied, a
        field whose LIVE template status is ``"deprecated"`` or ``"retired"``
        may NOT be SET — only omitted or left UNCHANGED. This is the
        status-authority split: value/type are checked against the IMMUTABLE
        captured snapshot, but write permission for a lifecycle-retired/
        deprecated field is checked against the LIVE template (so a field an
        admin deprecates today rejects writes on EXISTING entities whose
        snapshot still says ``active``). The snapshot column is NEVER mutated
        here.

        "is being set" is CHANGE-based (not presence-based): a deprecated/
        retired field is rejected only when ``stored_values`` is given AND the
        incoming value differs from the currently-stored one. Under D11
        whole-map-replace semantics the frontend edit form echoes the ENTIRE
        ``custom_fields`` dict (including locked deprecated/retired fields at
        their stored value); a presence-based gate would reject any edit on an
        entity bound to a template with ANY deprecated/retired field. The
        change-based gate permits the legitimate echo and only rejects an
        actual change. ``stored_values`` is ``None`` on the CREATE path, where
        presence reasserts (a new entity setting a deprecated field IS a set).

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
            live_statuses: Optional ``{code: status}`` map resolved from the
                LIVE current template. When supplied, it overrides the
                snapshot's ``spec["status"]`` for the deprecated/retired write
                gate (M2). ``None`` means "use the snapshot status verbatim"
                (the CREATE path, where the snapshot was just captured from the
                live template and so already reflects it).
            stored_values: Optional ``{code: value}`` map of the entity's
                CURRENTLY-STORED ``custom_fields``, supplied by the UPDATE path
                (``prepare_for_update``). When given, the deprecated/retired
                gate rejects only a CHANGE (incoming != stored); when ``None``
                (CREATE path), the gate is presence-based (``code in values``).

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

            # Phase 3 (M2) — lifecycle write gate. The effective status is the
            # LIVE template's when ``live_statuses`` is supplied, else the
            # snapshot's own ``spec["status"]`` (CREATE path). A deprecated or
            # retired field may NOT be SET — only omitted or left UNCHANGED.
            # "is being set" is CHANGE-based on the UPDATE path
            # (``stored_values`` given: present AND differing from the stored
            # value) and PRESENCE-based on the CREATE path (``stored_values``
            # is None: ``code in values``). The JSON-normalized equality
            # covers str-vs-number and list/multiselect round-trips.
            if live_statuses is not None:
                status = live_statuses.get(code, "active")
            else:
                status = field.status if field.status else "active"
            if status in ("deprecated", "retired"):
                is_being_set = code in values and (
                    stored_values is None
                    or not _custom_field_values_equal(
                        values[code], stored_values.get(code)
                    )
                )
                if is_being_set:
                    errors.append(f"field '{code}' is {status}")
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

    async def list_current_field_codes(
        self,
        entity_type: str,
        org_unit_id: UUID | None = None,
        *,
        flag: str | None = None,
    ) -> dict[str, dict[str, Any]]:
        """Union every CURRENT template's ``field_definitions`` for an entity type.

        Phase 2 queryability chokepoint: resolves which custom-field codes are
        queryable for a given ``target_entity_type`` (``PROJECT`` |
        ``WBS_ELEMENT`` | ``WORK_PACKAGE`` | ``CHANGE_ORDER``). Mirrors the
        current-version predicate used by
        :meth:`CustomEntityTemplateService.get_custom_entity_templates`
        (``upper(valid_time) IS NULL AND deleted_at IS NULL``). An optional
        ``org_unit_id`` further scopes the lookup; ``None`` returns ALL current
        templates of that type (single-org MVP).

        When ``flag`` is supplied (e.g. ``"searchable"`` or ``"ai_visible"``),
        only codes whose spec carries ``spec[flag] is True`` are kept (strict
        truthiness, mirroring :func:`filter_ai_visible_custom_fields`'s D8 gate).
        Returns the FULL ``{code: spec}`` map (not just the flag) so callers can
        read ``spec["type"]`` to pick a JSONB cast.

        Resolution is a per-entity-type UNION across every current template —
        codes are resolved per ``target_entity_type``, NOT per-row-template
        (per-row-template gating is intentionally not performed on the read
        path; keys are guarded by the write chokepoint, not here). When the same
        code appears in multiple templates, the OLDEST current template's spec
        wins via ``setdefault``: rows are read in ascending ``valid_time`` order
        (``valid_time`` is a tstzrange; Postgres orders by its lower bound = the
        version creation timestamp), so the first-seen spec is deterministic.

        Args:
            entity_type: ``target_entity_type`` discriminator.
            org_unit_id: Optional org-unit root id scope.
            flag: Optional spec key that must be strictly ``True`` to keep a code.

        Returns:
            ``{code: spec}`` dict (empty when no matching templates exist).
        """
        from app.models.domain.custom_entity_template import CustomEntityTemplate

        conditions = [
            CustomEntityTemplate.target_entity_type == entity_type,
            is_current_version(
                CustomEntityTemplate.valid_time,
                CustomEntityTemplate.deleted_at,
            ),
        ]
        if org_unit_id is not None:
            conditions.append(
                CustomEntityTemplate.organizational_unit_id == org_unit_id
            )

        # Ascending valid_time makes the cross-template union deterministic:
        # the oldest current template's spec wins via setdefault below.
        stmt = (
            select(CustomEntityTemplate.field_definitions)
            .where(*conditions)
            .order_by(CustomEntityTemplate.valid_time.asc())
        )
        result = await self.session.execute(stmt)  # type: ignore[union-attr]
        rows = result.all()

        merged: dict[str, dict[str, Any]] = {}
        for (field_defs,) in rows:
            if not isinstance(field_defs, dict):
                continue
            for code, spec in field_defs.items():
                if not isinstance(spec, dict):
                    continue
                if flag is not None and spec.get(flag) is not True:
                    continue
                # Oldest current template wins (rows are valid_time-ascending).
                merged.setdefault(code, spec)
        return merged

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
        :meth:`prepare_for_update` rather than re-resolving the template (D11).

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

    async def prepare_for_update(
        self,
        *,
        current_template_root_id: UUID | None,
        incoming_template_root_id: UUID | None,
        current_snapshot: dict[str, Any] | None,
        custom_fields: dict[str, Any] | None,
        actor_id: UUID,
        stored_custom_fields: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Compute the custom-fields update payload fields for an entity UPDATE.

        The UPDATE chokepoint. Refines frozen decision D2 — a template binding
        is IMMUTABLE once set, but the FIRST binding may happen on edit for a
        template-less existing entity (so legacy rows created before custom
        fields shipped can be bound without a destructive re-create).

        Rules:
            * FIRST-TIME BINDING — ``current_template_root_id is None`` AND
              ``incoming_template_root_id`` is set: resolve the template,
              capture ``snapshot = dict(template.field_definitions)``, and set
              BOTH ``custom_entity_template_root_id`` and
              ``custom_field_definitions_snapshot`` on the returned payload.
            * IMMUTABLE ONCE SET — ``current_template_root_id`` is set AND
              ``incoming_template_root_id`` is set AND
              ``incoming != current``: raise
              :class:`CustomFieldValidationError` (templates cannot be switched
              after the first binding).
            * SAME TEMPLATE — ``incoming == current`` (or ``incoming is None``
              with a current binding): the binding is preserved; the snapshot is
              the existing ``current_snapshot`` (NEVER re-captured — D11;
              clone() carries it forward).
            * ``custom_fields`` (when not ``None``) is validated against the
              EFFECTIVE snapshot (the newly-captured one for first-time
              binding, else the existing ``current_snapshot``). D11:
              ``custom_fields is None`` → not included (absent = skip); ``{}`` →
              included as ``{}`` (explicit clear); present dict → validated then
              included.
            * ``custom_fields`` provided without any template (no current AND no
              incoming) → raise :class:`CustomFieldValidationError` (values
              without a template to validate against).

        The deprecated/retired write gate (M2) is CHANGE-based on the UPDATE
        path: ``stored_custom_fields`` (the entity's currently-stored
        ``custom_fields``) is threaded into :meth:`validate_field_values` as
        ``stored_values``, so echoing a locked deprecated/retired field at its
        stored value is allowed and only a genuine change is rejected. If
        ``stored_custom_fields`` is ``None`` (caller did not supply it), the
        gate falls back to presence-based — never hard-failing the update.

        Args:
            current_template_root_id: The current version's
                ``custom_entity_template_root_id`` (``None`` if unbound).
            incoming_template_root_id: The template root id supplied on the
                UPDATE (pulled out of ``update_data`` by the caller).
            current_snapshot: The current version's
                ``custom_field_definitions_snapshot`` (captured at create;
                ``None`` if unbound). Never re-captured for an already-bound
                entity.
            custom_fields: The ``{code: value}`` dict supplied on the UPDATE
                (pulled out of ``update_data`` by the caller). ``None`` means
                the key was absent → skip (D11).
            actor_id: Actor for the async field checks.
            stored_custom_fields: The current version's stored
                ``custom_fields`` ``{code: value}`` dict (``None`` if the
                entity has none or the caller could not load it). Threaded into
                the deprecated/retired gate so an echoed locked field is
                allowed and only a change is rejected.

        Returns:
            A dict to MERGE into the service's ``update_data``. Keys are
            included only as needed: ``custom_entity_template_root_id``,
            ``custom_field_definitions_snapshot``, ``custom_fields``.

        Raises:
            CustomFieldValidationError: template-switch attempt, custom_fields
                without any template, unknown template root, or per-field
                validation errors (joined into one message).
        """
        # The effective snapshot that custom_fields (if any) is validated
        # against, and the payload under construction.
        effective_snapshot: dict[str, Any] | None
        updates: dict[str, Any] = {}

        if current_template_root_id is None and incoming_template_root_id is not None:
            # FIRST-TIME BINDING (D2 refinement): resolve + capture the snapshot.
            template = await self.resolve_template(incoming_template_root_id)
            if template is None:
                raise CustomFieldValidationError(
                    f"CustomEntityTemplate {incoming_template_root_id} not found"
                )
            effective_snapshot = dict(template.field_definitions)
            updates["custom_entity_template_root_id"] = incoming_template_root_id
            updates["custom_field_definitions_snapshot"] = effective_snapshot
        elif (
            current_template_root_id is not None
            and incoming_template_root_id is not None
            and incoming_template_root_id != current_template_root_id
        ):
            # IMMUTABLE ONCE SET (D2): cannot switch templates after creation.
            raise CustomFieldValidationError(
                "Template binding is immutable once set; cannot switch "
                "templates after creation."
            )
        else:
            # SAME TEMPLATE (incoming == current, or incoming is None with a
            # current binding). The binding is preserved unchanged; the snapshot
            # is the existing one — NEVER re-captured (D11; clone() carries it).
            effective_snapshot = current_snapshot

        if custom_fields is None:
            # D11: absent key → skip (do not touch custom_fields on the row).
            return updates

        # custom_fields is present (possibly {}). Validate against the effective
        # snapshot. A template-less entity reaching here with no incoming
        # binding cannot validate anything → reject.
        if effective_snapshot is None:
            raise CustomFieldValidationError(
                "custom_fields require a custom_entity_template_root_id"
            )

        # Phase 3 (M2) — status-authority split: value/type/options are checked
        # against the EFFECTIVE (immutable) snapshot above, but the
        # deprecated/retired write gate must be checked against the LIVE
        # template so a field an admin deprecates today rejects writes on
        # EXISTING entities (whose snapshot still says ``active``). Resolve the
        # live template by the entity's binding and build ``{code: status}``.
        # The binding root id is whichever the entity resolves to: the incoming
        # one on a first-time bind, else the current one. If the live template
        # is unresolvable (deleted/migrated), fall back to the snapshot status
        # rather than hard-failing the update.
        live_binding_root = (
            incoming_template_root_id
            if current_template_root_id is None
            else current_template_root_id
        )
        live_statuses: dict[str, str] | None = None
        if live_binding_root is not None:
            live_template = await self.resolve_template(live_binding_root)
            if live_template is not None and isinstance(
                live_template.field_definitions, dict
            ):
                live_statuses = {
                    code: spec.get("status", "active")
                    for code, spec in live_template.field_definitions.items()
                    if isinstance(spec, dict)
                }

        errors = await self.validate_field_values(
            effective_snapshot,
            custom_fields,
            actor_id=actor_id,
            live_statuses=live_statuses,
            stored_values=stored_custom_fields,
        )
        if errors:
            raise CustomFieldValidationError("; ".join(errors))

        updates["custom_fields"] = custom_fields
        return updates
