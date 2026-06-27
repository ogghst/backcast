"""Concrete custom-field subclasses.

Validation/serialization rules per analysis section 6.1 table. Each class
sets a unique ``type_code`` (the stored discriminator) and implements
:meth:`validate`, :meth:`serialize`, and a :meth:`to_widget_spec` that
extends the base projection with type-specific keys.

Stdlib only (``datetime``, ``decimal``, ``uuid``) — no project imports
other than the sibling ``base`` module, keeping the package portable.
"""

from __future__ import annotations

import datetime
import decimal
import uuid
from typing import Any

from sqlalchemy import select

from app.models.custom_fields.base import FieldDefinition

#: Default RYG+B options shared by :class:`IndicatorField` when no override is
#: supplied via config. Matches the analysis section 6.1 contract.
_INDICATOR_DEFAULTS: tuple[str, ...] = ("red", "yellow", "green", "blue")


class TextField(FieldDefinition):
    """Short free-form text, bounded by ``max_length`` (default 255)."""

    type_code = "text"

    def validate(self, value: Any) -> list[str]:
        if value is None:
            return []
        max_length = self.config.get("max_length", 255)
        if isinstance(value, str) and len(value) <= max_length:
            return []
        return [f"{self.label} must be a string of at most {max_length} characters"]

    def serialize(self, value: Any) -> Any:
        return value

    def to_widget_spec(self) -> dict[str, Any]:
        max_length = self.config.get("max_length", 255)
        return {
            **super().to_widget_spec(),
            "widget": "input",
            "max_length": max_length,
        }


class NumberField(FieldDefinition):
    """Numeric (int or float) — but NOT bool (Python ``True`` is an ``int``)."""

    type_code = "number"

    def validate(self, value: Any) -> list[str]:
        if value is None:
            return []
        # bool is a subclass of int in Python; explicitly reject it so a UI
        # checkbox / Python ``True`` does not silently coerce to ``1``.
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            return []
        return [f"{self.label} must be a number"]

    def serialize(self, value: Any) -> Any:
        return value

    def to_widget_spec(self) -> dict[str, Any]:
        return {**super().to_widget_spec(), "widget": "number"}


class DecimalField(FieldDefinition):
    """Monetary / high-precision decimal.

    Accepts :class:`decimal.Decimal` or a numeric string; serialized as a
    STRING to preserve precision across the JSONB round-trip (avoiding
    float's binary rounding). Matches ``DECIMAL(15,2)`` semantics.
    """

    type_code = "decimal"

    def validate(self, value: Any) -> list[str]:
        if value is None:
            return []
        try:
            decimal.Decimal(str(value))
        except (decimal.InvalidOperation, ValueError, TypeError):
            return [f"{self.label} must be a decimal"]
        return []

    def serialize(self, value: Any) -> Any:
        return str(value)

    def to_widget_spec(self) -> dict[str, Any]:
        return {**super().to_widget_spec(), "widget": "number", "step": 0.01}


class IntegerField(FieldDefinition):
    """Whole-number integer — but NOT bool."""

    type_code = "integer"

    def validate(self, value: Any) -> list[str]:
        if value is None:
            return []
        if isinstance(value, int) and not isinstance(value, bool):
            return []
        return [f"{self.label} must be an integer"]

    def serialize(self, value: Any) -> Any:
        return value

    def to_widget_spec(self) -> dict[str, Any]:
        return {**super().to_widget_spec(), "widget": "number"}


class DateField(FieldDefinition):
    """ISO-8601 calendar date (``YYYY-MM-DD``)."""

    type_code = "date"

    def validate(self, value: Any) -> list[str]:
        if value is None:
            return []
        if isinstance(value, str):
            try:
                datetime.date.fromisoformat(value)
                return []
            except ValueError:
                pass
        return [f"{self.label} must be an ISO-8601 date (YYYY-MM-DD)"]

    def serialize(self, value: Any) -> Any:
        return value

    def to_widget_spec(self) -> dict[str, Any]:
        return {**super().to_widget_spec(), "widget": "date"}


class DateTimeField(FieldDefinition):
    """ISO-8601 datetime (time-component allowed)."""

    type_code = "datetime"

    def validate(self, value: Any) -> list[str]:
        if value is None:
            return []
        if isinstance(value, str):
            try:
                datetime.datetime.fromisoformat(value)
                return []
            except ValueError:
                pass
        return [f"{self.label} must be an ISO-8601 datetime"]

    def serialize(self, value: Any) -> Any:
        return value

    def to_widget_spec(self) -> dict[str, Any]:
        return {**super().to_widget_spec(), "widget": "datetime"}


class BooleanField(FieldDefinition):
    """Strict boolean — rejects non-bool truthiness."""

    type_code = "boolean"

    def validate(self, value: Any) -> list[str]:
        if value is None:
            return []
        if isinstance(value, bool):
            return []
        return [f"{self.label} must be a boolean"]

    def serialize(self, value: Any) -> Any:
        return value

    def to_widget_spec(self) -> dict[str, Any]:
        return {**super().to_widget_spec(), "widget": "switch"}


class SelectField(FieldDefinition):
    """Single-choice select; ``config["options"]`` is a ``list[str]``."""

    type_code = "select"

    def validate(self, value: Any) -> list[str]:
        if value is None:
            return []
        options = self.config.get("options")
        if not options:
            return [f"{self.label} has no configured options"]
        if value in options:
            return []
        return [f"{self.label} must be one of {options}"]

    def serialize(self, value: Any) -> Any:
        return value

    def to_widget_spec(self) -> dict[str, Any]:
        return {
            **super().to_widget_spec(),
            "widget": "select",
            "options": self.config["options"],
        }


class MultiSelectField(FieldDefinition):
    """Multi-choice select.

    Stored VALUE is a ``list[str]`` nested inside the entity's
    ``custom_fields`` dict — that is safe: only a top-level list-typed
    JSONB *column* breaks the raw-INSERT versioning guard (analysis
    section 6.4 note on nested list values).
    """

    type_code = "multiselect"

    def validate(self, value: Any) -> list[str]:
        if value is None:
            return []
        options = self.config.get("options")
        if not options:
            return [f"{self.label} has no configured options"]
        if isinstance(value, list) and all(item in options for item in value):
            return []
        return [f"{self.label} must be a list with items in {options}"]

    def serialize(self, value: Any) -> Any:
        return value

    def to_widget_spec(self) -> dict[str, Any]:
        return {
            **super().to_widget_spec(),
            "widget": "select",
            "mode": "multiple",
            "options": self.config["options"],
        }


class IndicatorField(FieldDefinition):
    """Status indicator (default red/yellow/green/blue)."""

    type_code = "indicator"

    def validate(self, value: Any) -> list[str]:
        if value is None:
            return []
        options = self.config.get("options", list(_INDICATOR_DEFAULTS))
        if value in options:
            return []
        return [f"{self.label} must be one of {options}"]

    def serialize(self, value: Any) -> Any:
        return value

    def to_widget_spec(self) -> dict[str, Any]:
        return {
            **super().to_widget_spec(),
            "widget": "indicator",
            "options": self.config.get("options", list(_INDICATOR_DEFAULTS)),
        }


class ReferenceField(FieldDefinition):
    """Reference to another entity's ROOT id.

    MVP target is ``'user'`` only (``config["target_entity"] == "user"``);
    other targets are deferred (analysis section 11.2). Stored as the
    target's root-id STRING; no DB-level FK — Backcast enforces integrity
    at the application layer (D6 app-level FK convention, like the
    Project/WBSElement relationships).

    Sync :meth:`validate` checks UUID-shape only; existence + RBAC is an
    async post-check owned by ``CustomFieldService`` at write time.
    """

    type_code = "reference"

    def validate(self, value: Any) -> list[str]:
        if value is None:
            return []
        try:
            uuid.UUID(str(value))
        except (ValueError, AttributeError, TypeError):
            return [f"{self.label} must be a UUID-shaped root id"]
        return []

    async def validate_async(
        self,
        value: Any,
        *,
        session: Any = None,
        actor_id: Any = None,
    ) -> list[str]:
        """User existence check (D6 app-level FK; MVP target = 'user').

        Looks the referenced User up by ROOT id (``user_id``) and rejects a
        non-existent or soft-deleted (``deleted_at IS NOT NULL``) target. RBAC
        beyond existence ("can this actor see this user") is deferred for MVP —
        see the TODO below.

        ``session is None`` → return ``[]`` (can't check, skip). This preserves
        the original Phase-0 no-session behavior so the pure-unit call sites
        (``CustomFieldService().validate_field_values(defs, values)`` without a
        session) keep working unchanged.
        """
        # Only the 'user' target has an existence check in MVP; other targets
        # are deferred (analysis section 11.2) — treat them as shape-only.
        if self.config.get("target_entity") != "user":
            return []
        if session is None:
            return []

        # Local import keeps the field package dependency-free at import time.
        from app.models.domain.user import User

        try:
            target_uuid = uuid.UUID(str(value))
        except (ValueError, AttributeError, TypeError):
            # Sync validate() already enforces UUID shape; defensive guard.
            return [f"{self.label} must be a UUID-shaped root id"]

        stmt = (
            select(User.user_id)
            .where(
                User.user_id == target_uuid,
                User.deleted_at.is_(None),
            )
            .limit(1)
        )
        result = await session.execute(stmt)
        found = result.scalar_one_or_none()
        if found is None:
            return [f"{self.label} references an unknown user"]

        # TODO(deferred RBAC): finer "can actor_id see this user" scoping is
        # intentionally NOT enforced in MVP — existence only (analysis section
        # 6.1 / D6). Wire actor-scoped visibility once the org-unit RBAC
        # resolution is available as a reusable helper.
        return []

    def serialize(self, value: Any) -> Any:
        return str(value)

    def to_widget_spec(self) -> dict[str, Any]:
        return {
            **super().to_widget_spec(),
            "widget": "reference",
            "target": self.config.get("target_entity", "user"),
        }


class FormulaField(FieldDefinition):
    """Computed-on-read placeholder; never stored as a value.

    A formula appears in ``field_definitions`` (so the snapshot and the AI
    manifest know it exists) but has no entry in the entity's
    ``custom_fields`` value dict. ``validate`` is a no-op (the field is
    not user-writable) and ``serialize`` raises: callers reading stored
    values MUST skip ``type_code == "formula"`` (analysis section 6.7, m13).
    """

    type_code = "formula"

    def validate(self, value: Any) -> list[str]:
        # Not user-writable; nothing to validate at write time.
        return []

    def serialize(self, value: Any) -> Any:
        raise NotImplementedError("Formula is computed on read")

    def to_widget_spec(self) -> dict[str, Any]:
        return {
            **super().to_widget_spec(),
            "widget": "formula",
        }
