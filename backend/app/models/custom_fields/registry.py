"""Type-code registry and spec -> FieldDefinition factory.

``FIELD_REGISTRY`` maps the stored type discriminator (the ``"type"`` key
of a stored field-definition spec) to the concrete class.
``build_field`` reconstructs a :class:`FieldDefinition` from such a spec.

Built explicitly (not via a comprehension over a class list) so the
discriminator -> class mapping is grep-readable and order-independent.
``AttachmentLinkField`` is intentionally absent (deferred — analysis M13).
"""

from __future__ import annotations

from typing import Any

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

#: Discriminator string -> concrete class. AttachmentLinkField is deferred
#: (its target entity + read/render contract is unspecified — M13).
FIELD_REGISTRY: dict[str, type[FieldDefinition]] = {
    "text": TextField,
    "number": NumberField,
    "decimal": DecimalField,
    "integer": IntegerField,
    "date": DateField,
    "datetime": DateTimeField,
    "boolean": BooleanField,
    "select": SelectField,
    "multiselect": MultiSelectField,
    "indicator": IndicatorField,
    "reference": ReferenceField,
    "formula": FormulaField,
}


def build_field(spec: dict[str, Any]) -> FieldDefinition:
    """Construct a :class:`FieldDefinition` from a stored spec dict.

    ``spec["type"]`` selects the class; ``spec["code"]`` is required and
    ``spec["label"]`` falls back to the code; every other key is forwarded
    as a keyword arg (matching the well-known ctor params and the
    type-specific ``config`` catch-all). A missing ``type`` or ``code``
    raises ``ValueError`` so malformed specs surface as validation errors.
    """
    type_ = spec.get("type")
    if not type_:
        raise ValueError("field spec missing 'type'")
    if type_ not in FIELD_REGISTRY:
        raise ValueError(f"Unknown custom field type: {type_!r}")
    cls = FIELD_REGISTRY[type_]
    code = spec.get("code")
    if not code:
        raise ValueError("field spec missing 'code'")
    label = spec.get("label", code)
    extras = {k: v for k, v in spec.items() if k not in ("type", "code", "label")}
    return cls(code=code, label=label, **extras)
