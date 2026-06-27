"""Generic filtering utilities for server-side table filtering.

This module provides utilities to parse URL filter strings and convert them
to SQLAlchemy filter expressions, enabling consistent server-side filtering
across all entity list endpoints.

URL Filter Format:
    ?filters=column:value;column:value1,value2

Examples:
    - Single filter: "status:active"
    - Multiple filters: "status:active;branch:main"
    - Multi-value filter: "branch:main,dev,staging"
    - Combined: "status:active;branch:main,dev;level:1,2,3"

Security:
    - Field names are validated against the model
    - Only whitelisted fields can be filtered
    - SQL injection is prevented through SQLAlchemy ORM
"""

from typing import Any

from sqlalchemy import BinaryExpression, Numeric, case, literal
from sqlalchemy import cast as sql_cast
from sqlalchemy.orm import DeclarativeMeta

#: numeric custom-field type codes — values are compared after casting the
#: JSONB text extraction to NUMERIC so "10" sorts/equals numerically.
_NUMERIC_CF_TYPES = frozenset({"number", "decimal", "integer"})

#: temporal custom-field type codes — values are compared as timestamps.
_TEMPORAL_CF_TYPES = frozenset({"date", "datetime"})

#: Regex a stored custom-field value must match before it is cast to NUMERIC.
#: Guards the DB-side cast so one corrupt/legacy row yields NULL (excluded
#: from equality/IN; sorts last via nullslast) instead of raising a Postgres
#: DataError that would abort the whole list query.
_NUMERIC_REGEX = r"^[+-]?([0-9]+([.][0-9]*)?|[.][0-9]+)([eE][+-]?[0-9]+)?$"

#: Regex a stored value must match before it is cast to TIMESTAMP (ISO-8601
#: date or datetime). Same defensive rationale as ``_NUMERIC_REGEX``.
_TEMPORAL_REGEX = r"^\d{4}-\d{2}-\d{2}([ T]\d{2}:\d{2}(:\d{2})?([.]\d+)?)?$"

#: ``custom_fields`` JSONB values that mean boolean True / False. JSONB ``->>``
#: on a stored boolean yields the lowercase text "true"/"false".
_BOOLEAN_TRUE = frozenset({"true", "1", "yes", "on"})
_BOOLEAN_FALSE = frozenset({"false", "0", "no", "off"})


def _custom_field_expression(
    model: type[DeclarativeMeta],
    key: str,
    spec: dict[str, Any],
    values: list[str],
) -> BinaryExpression[Any]:
    """Build an equality/IN SQLAlchemy expression for a JSONB custom field.

    Phase 2 queryability: the value lives at
    ``model.custom_fields[key]`` (a JSONB dict column). Extraction is via the
    ``->>`` operator (returns TEXT), with a type-aware cast driven by
    ``spec["type"]``:

    * ``number`` / ``decimal`` / ``integer`` -> ``cast(..., Numeric)`` so
      ``"10"`` matches the stored ``10`` and sorts numerically.
    * ``date`` / ``datetime`` -> ``cast(..., TIMESTAMP)`` (text compare on the
      ISO-8601 string also works; cast keeps it consistent and future-proof).
    * ``boolean`` -> incoming values are normalized (``1``/``yes``/``on`` ->
      ``"true"``, ``0``/``no``/``off`` -> ``"false"``) and compared as TEXT.
    * everything else (``text`` / ``select`` / ``indicator`` / ``reference``)
      -> TEXT compare (references are UUID-shaped strings).

    The numeric and temporal casts are GUARDED by a regex precondition: a
    stored value that cannot be cast yields NULL (excluded from ``=``/``IN``)
    rather than raising a Postgres DataError that would 500 the whole list
    query. ``multiselect`` is rejected outright (its ``->>`` yields array JSON
    text that equality can never match).

    The key is bound through the SQLAlchemy accessor (``.op('->>')(key)``) — it
    is NEVER f-stringed into SQL, so only allowlist-resolved keys reach this
    branch (the caller passes ``custom_field_specs`` already gated on
    ``searchable``). NULL semantics: a row missing the key yields NULL from
    ``->>``; NULL != value naturally excludes it (no special handling needed).
    """
    from sqlalchemy.dialects.postgresql import TIMESTAMP  # local: avoid cycle

    type_code = spec.get("type")

    # A multiselect stores a JSON array; ``->>`` yields the array's JSON text,
    # so equality/IN can never match — reject explicitly instead of silently
    # returning zero rows.
    if type_code == "multiselect":
        raise ValueError(f"cannot filter equality/IN on multi-value field '{key}'")

    extracted = model.custom_fields.op("->>")(key)  # type: ignore[attr-defined]

    if type_code in _NUMERIC_CF_TYPES:
        # Defensive cast: only cast rows whose stored text actually parses as
        # a number; anything else yields NULL (excluded from =/IN). Prevents
        # one corrupt/legacy row from raising a DataError that 500s the query.
        safe = case((extracted.op("~")(literal(_NUMERIC_REGEX)), extracted), else_=None)
        casted: Any = sql_cast(safe, Numeric)
        typed_values: list[Any] = [float(v) for v in values]
    elif type_code in _TEMPORAL_CF_TYPES:
        # Same defensive guard as numeric, for the TIMESTAMP cast.
        safe = case(
            (extracted.op("~")(literal(_TEMPORAL_REGEX)), extracted), else_=None
        )
        casted = sql_cast(safe, TIMESTAMP)
        typed_values = list(values)
    elif type_code == "boolean":
        # Normalize incoming values so ``flag:1`` / ``flag:yes`` / ``flag:on``
        # behave like a real boolean-column filter. JSONB ``->>`` on a stored
        # boolean yields lowercase "true"/"false", so a text compare matches.
        normalized: list[str] = []
        for v in values:
            v_lower = v.lower()
            if v_lower in _BOOLEAN_TRUE:
                normalized.append("true")
            elif v_lower in _BOOLEAN_FALSE:
                normalized.append("false")
            else:
                raise ValueError(
                    f"Invalid boolean value '{v}' for custom field '{key}'"
                )
        casted = extracted
        typed_values = list(normalized)
    else:
        casted = extracted
        typed_values = list(values)

    if len(typed_values) == 1:
        return casted == typed_values[0]
    return casted.in_(typed_values)


def _custom_field_order_by(
    model: type[DeclarativeMeta],
    key: str,
    spec: dict[str, Any],
    sort_order: str,
) -> Any:
    """Build a JSONB ORDER BY clause for a custom-field key (NULLs last).

    Phase 2 sort: text-typed keys sort as TEXT; numeric types cast to NUMERIC so
    ``"10"`` sorts after ``"9"``. Sorting on ``multiselect`` is rejected (a
    list value has no total order). The numeric/temporal casts are GUARDED by a
    regex precondition so a corrupt/legacy row yields NULL (sorts last via
    ``nullslast()``) instead of raising a DataError that 500s the query. The
    returned clause element carries ``nullslast()`` so rows missing the key
    sort to the bottom regardless of direction.
    """
    from sqlalchemy.dialects.postgresql import TIMESTAMP  # local: avoid cycle

    type_code = spec.get("type")
    if type_code == "multiselect":
        raise ValueError(f"cannot sort on multi-value field '{key}'")

    extracted = model.custom_fields.op("->>")(key)  # type: ignore[attr-defined]
    if type_code in _NUMERIC_CF_TYPES:
        # Defensive cast: only cast rows whose stored text parses as a number;
        # anything else yields NULL and sorts last via nullslast(). Prevents a
        # corrupt/legacy row from raising a DataError that 500s the sort query.
        safe = case((extracted.op("~")(literal(_NUMERIC_REGEX)), extracted), else_=None)
        ordered: Any = sql_cast(safe, Numeric)
    elif type_code in _TEMPORAL_CF_TYPES:
        safe = case(
            (extracted.op("~")(literal(_TEMPORAL_REGEX)), extracted), else_=None
        )
        ordered = sql_cast(safe, TIMESTAMP)
    else:
        ordered = extracted

    if sort_order.lower() == "desc":
        return ordered.desc().nullslast()
    return ordered.asc().nullslast()


class FilterParser:
    """Parser for URL filter strings to SQLAlchemy expressions."""

    @staticmethod
    def parse_filters(filter_string: str | None) -> dict[str, list[str]]:
        """Parse URL filter string to dictionary.

        Args:
            filter_string: Filter string in format "column:value;column:value1,value2"

        Returns:
            Dictionary mapping column names to lists of values.
            Example: {"status": ["active"], "branch": ["main", "dev"]}

        Examples:
            >>> FilterParser.parse_filters("status:active")
            {"status": ["active"]}

            >>> FilterParser.parse_filters("status:active;branch:main,dev")
            {"status": ["active"], "branch": ["main", "dev"]}

            >>> FilterParser.parse_filters(None)
            {}

            >>> FilterParser.parse_filters("")
            {}
        """
        if not filter_string:
            return {}

        filters: dict[str, list[str]] = {}

        # Split by semicolon to get individual filter expressions
        for filter_expr in filter_string.split(";"):
            filter_expr = filter_expr.strip()
            if not filter_expr or ":" not in filter_expr:
                continue

            # Split by colon to get column and values
            column, values_str = filter_expr.split(":", 1)
            column = column.strip()
            values_str = values_str.strip()

            if not column or not values_str:
                continue

            # Split values by comma
            values = [v.strip() for v in values_str.split(",") if v.strip()]

            if values:
                filters[column] = values

        return filters

    @staticmethod
    def build_sqlalchemy_filters(
        model: type[DeclarativeMeta],
        filters: dict[str, list[str]],
        allowed_fields: list[str] | None = None,
        custom_field_specs: dict[str, dict[str, Any]] | None = None,
    ) -> list[BinaryExpression[Any]]:
        """Build SQLAlchemy filter expressions from parsed filters.

        ... (docstring) ...
        """
        from app.core.exceptions.filtering import (
            FilterFieldNotAllowedError,
            FilterValueTypeError,
        )

        expressions: list[BinaryExpression[Any]] = []

        for field_name, values in filters.items():
            # PHASE 2: real columns ALWAYS win. A custom field literally named
            # ``status`` MUST NOT shadow the real ``status`` column — so the
            # ``hasattr`` check runs FIRST, and only when the key is NOT a real
            # column do we consult the custom-field specs.
            if not hasattr(model, field_name):
                if custom_field_specs is not None and field_name in custom_field_specs:
                    # JSONB custom-field expression (equality / IN only).
                    # Only allowlist-resolved keys reach this branch — the key
                    # is bound via .op('->>'), never f-stringed into SQL.
                    expressions.append(
                        _custom_field_expression(
                            model,
                            field_name,
                            custom_field_specs[field_name],
                            values,
                        )
                    )
                    continue
                raise ValueError(
                    f"Invalid filter field '{field_name}' for model {model.__name__}"
                )

            # Validate field is in allowed list (if provided)
            if allowed_fields is not None and field_name not in allowed_fields:
                raise FilterFieldNotAllowedError(field_name, allowed_fields)

            # Get the column from the model
            column = getattr(model, field_name)

            # Attempt to cast values based on column type
            col_type = None
            try:
                col_type = column.type.python_type

                # Only cast if not already compatible (e.g. str to int)
                # But we blindly try to cast to ensure safety, except for str which is already what we have
                if col_type is not str:
                    casted_values = []
                    for v in values:
                        if col_type is bool:
                            # Handle boolean strings: "true"/"1" -> True, "false"/"0" -> False
                            v_lower = v.lower()
                            if v_lower in ("true", "1", "yes", "on"):
                                casted_values.append(True)
                            elif v_lower in ("false", "0", "no", "off"):
                                casted_values.append(False)
                            else:
                                raise ValueError("Invalid boolean value")
                        else:
                            casted_values.append(col_type(v))
                    values = casted_values  # type: ignore
            except (ValueError, TypeError, Exception) as e:
                # Catching general Exception here because third-party types (like Decimal)
                # can raise specific errors (decimal.InvalidOperation) that don't inherit from ValueError.
                # In strict mode, we capture this.
                # The `pass` in the original instruction was likely a misunderstanding;
                # we want to catch these errors and then raise our specific FilterValueTypeError.
                type_name = (
                    getattr(col_type, "__name__", "unknown") if col_type else "unknown"
                )
                raise FilterValueTypeError(
                    field=field_name, value=str(values), expected_type=type_name
                ) from e
            except NotImplementedError:
                # Some types like JSON/Array might not support python_type
                pass

            # Build expression based on number of values
            if len(values) == 1:
                # Single value: equality check
                expressions.append(column == values[0])
            else:
                # Multiple values: IN clause
                expressions.append(column.in_(values))

        return expressions
