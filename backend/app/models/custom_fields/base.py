"""Base ABC for the OO custom-field-class hierarchy.

See `docs/03-project-plan/iterations/2026-06-24-custom-fields-analysis/
functional-analysis.md` section 8 (and section 6.1 for the per-type contract
table). Each concrete subclass in ``fields.py`` owns its sync ``validate``,
its ``serialize`` coercion to a JSONB-safe value, and its
``to_widget_spec`` projection for the form renderer.

This module is PURE PYTHON (no DB / SQLAlchemy / Pydantic) so it can be
reused by services, the AI manifest builder, and the form frontend's
spec payload. Stored custom-field VALUES are a flat ``{code: value}`` dict
JSONB on the entity row; stored field DEFINITIONS are a ``{code: spec}``
dict JSONB on the template row.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class FieldDefinition(ABC):
    """Base contract for a custom field type.

    A ``FieldDefinition`` instance is the in-memory counterpart of one entry
    in a ``CustomEntityTemplate.field_definitions`` dict. It is constructed
    from a plain ``spec`` dict via :func:`build_field`; callers should not
    instantiate subclasses directly unless they are tests.

    Required/None handling is intentionally NOT the field's responsibility:
    a ``None`` value means "absent" and ``validate`` returns ``[]`` for it.
    The :class:`CustomFieldService` decides whether an absent required field
    is an error at write time (so partial / patch writes stay validatable).
    """

    #: Stored type discriminator (the ``"type"`` key of the spec dict).
    type_code: str = "base"

    def __init__(
        self,
        code: str,
        label: str,
        *,
        required: bool = False,
        default: Any = None,
        indexed: bool = False,
        searchable: bool = False,
        ai_visible: bool = False,
        status: str = "active",
        **config: Any,
    ) -> None:
        self.code = code
        self.label = label
        self.required = required
        self.default = default
        self.indexed = indexed
        # D8: fields opt IN to AI visibility (default False).
        self.ai_visible = ai_visible
        # UI search is opt-in (D8 mirrors the AI gating for the form renderer).
        self.searchable = searchable
        # Per-field lifecycle: active | deprecated | retired (analysis section 6.7).
        self.status = status
        # Type-specific extras (max_length, options, target_entity, widget, ...).
        self.config: dict[str, Any] = config

    @abstractmethod
    def validate(self, value: Any) -> list[str]:
        """SYNC shape/type check; return human error strings (empty if valid).

        A ``None`` value is treated as "absent" and returns ``[]`` — the
        service decides whether the absence of a required field is an error.
        """

    async def validate_async(
        self,
        value: Any,
        *,
        session: Any = None,
        actor_id: Any = None,
    ) -> list[str]:
        """Async post-checks (target existence + RBAC).

        Default no-op; :class:`ReferenceField` overrides this (m11). Kept
        async because the real checks need a DB session and an actor for
        the RBAC resolution performed by ``CustomFieldService``.
        """
        return []

    @abstractmethod
    def serialize(self, value: Any) -> Any:
        """Coerce ``value`` to a JSONB-safe representation."""

    def deserialize(self, raw: Any) -> Any:
        """Reverse of :meth:`serialize`. Default identity."""
        return raw

    def to_widget_spec(self) -> dict[str, Any]:
        """Project this definition into a frontend form-widget spec.

        Subclasses extend the base keys with type-specific extras
        (``widget``, ``max_length``, ``options``, ``target``, ...).
        """
        return {
            "code": self.code,
            "label": self.label,
            "type": self.type_code,
            "required": self.required,
            "default": self.default,
            "searchable": self.searchable,
            "ai_visible": self.ai_visible,
            "status": self.status,
        }

    @classmethod
    def from_spec(cls, spec: dict[str, Any]) -> FieldDefinition:
        """Rebuild a definition from a stored spec dict.

        Delegates to :func:`build_field` (imported lazily to avoid a
        registry -> fields -> base -> registry circular import).
        """
        # Local import: registry imports this module.
        from app.models.custom_fields.registry import build_field

        return build_field(spec)
