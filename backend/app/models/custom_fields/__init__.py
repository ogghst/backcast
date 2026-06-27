"""OO custom-field-class hierarchy (analysis section 8).

Each custom-field type is a Python class owning its sync validation, its
JSONB serialization, and its form-widget spec. A stored
``CustomEntityTemplate.field_definitions`` is a ``{code: spec}`` dict;
:meth:`FieldDefinition.from_spec` (and the underlying :func:`build_field`)
rebuild the class from such a spec. Stored VALUES are a flat
``{code: value}`` dict JSONB on the entity row, validated by
``CustomFieldService`` against the bound template's snapshot.

This package is intentionally pure Python (no DB / SQLAlchemy / Pydantic
imports) so it can be reused across services, the AI manifest builder, and
the form-renderer spec projection.
"""

from __future__ import annotations

from app.models.custom_fields.base import FieldDefinition
from app.models.custom_fields.fields import (
    BooleanField,
    DateField,
    DateTimeField,
    DecimalField,
    FormulaField,
    IndicatorField,
    IntegerField,
    MultiSelectField,
    NumberField,
    ReferenceField,
    SelectField,
    TextField,
)
from app.models.custom_fields.registry import FIELD_REGISTRY, build_field

__all__ = [
    "FieldDefinition",
    "TextField",
    "NumberField",
    "DecimalField",
    "IntegerField",
    "DateField",
    "DateTimeField",
    "BooleanField",
    "SelectField",
    "MultiSelectField",
    "IndicatorField",
    "ReferenceField",
    "FormulaField",
    "FIELD_REGISTRY",
    "build_field",
]
