"""Unit tests for FilterParser range operators (G4).

Pure unit tests on the parser/builder — no DB session required. Covers:

- parse_filters: eq (default), gte, lte, between, date_range, comma-IN, combined.
- build_sqlalchemy_filters: real-column dispatch for gte/lte/between/date_range,
  backward-compat eq / .in_(), FilterOperatorNotAllowedError on a forbidden op,
  custom-field eq still works and custom-field range raises.
"""

from __future__ import annotations

from typing import Any

import pytest
from sqlalchemy import BinaryExpression

from app.core.exceptions.filtering import (
    FilterOperatorNotAllowedError,
)
from app.core.filtering import RANGE_OPERATORS, FilterParser
from app.models.domain.project import Project

# ---------------------------------------------------------------------------
# parse_filters
# ---------------------------------------------------------------------------


class TestParseFilters:
    """parse_filters returns a dict keyed by (column, operator)."""

    def test_plain_eq_is_default(self) -> None:
        result = FilterParser.parse_filters("status:active")
        assert result == {("status", "eq"): ["active"]}

    def test_multiple_eq_filters(self) -> None:
        result = FilterParser.parse_filters("status:active;branch:main")
        assert result == {
            ("status", "eq"): ["active"],
            ("branch", "eq"): ["main"],
        }

    def test_comma_values_produce_eq_in(self) -> None:
        # comma-separated values still parse as eq with multiple values (-> IN)
        result = FilterParser.parse_filters("code:a,b")
        assert result == {("code", "eq"): ["a", "b"]}

    def test_gte_suffix(self) -> None:
        result = FilterParser.parse_filters("contract_value__gte:1000")
        assert result == {("contract_value", "gte"): ["1000"]}

    def test_lte_suffix(self) -> None:
        result = FilterParser.parse_filters("contract_value__lte:5000")
        assert result == {("contract_value", "lte"): ["5000"]}

    def test_between_suffix_two_values(self) -> None:
        result = FilterParser.parse_filters("progress__between:10,90")
        assert result == {("progress", "between"): ["10", "90"]}

    def test_date_range_suffix_two_values(self) -> None:
        result = FilterParser.parse_filters(
            "start_date__date_range:2026-01-01,2026-12-31"
        )
        assert result == {("start_date", "date_range"): ["2026-01-01", "2026-12-31"]}

    def test_combined_eq_and_range(self) -> None:
        result = FilterParser.parse_filters(
            "status:active;contract_value__gte:1000;code:a,b"
        )
        assert result == {
            ("status", "eq"): ["active"],
            ("contract_value", "gte"): ["1000"],
            ("code", "eq"): ["a", "b"],
        }

    def test_unrecognized_suffix_treated_as_eq(self) -> None:
        # A column literally named ``foo__bar`` with a NON-operator suffix
        # parses as (column='foo__bar', op='eq') — not split.
        result = FilterParser.parse_filters("foo__bar:baz")
        assert result == {("foo__bar", "eq"): ["baz"]}

    def test_none_and_empty_return_empty_dict(self) -> None:
        assert FilterParser.parse_filters(None) == {}
        assert FilterParser.parse_filters("") == {}

    def test_all_operators_in_registry(self) -> None:
        # Sanity: the suffixes tested above are in RANGE_OPERATORS.
        assert {"gte", "lte", "between", "date_range", "eq"} <= set(RANGE_OPERATORS)


# ---------------------------------------------------------------------------
# build_sqlalchemy_filters
# ---------------------------------------------------------------------------


def _compile(expr: BinaryExpression[Any]) -> str:
    """Render an expression to SQL text for assertion (dialect-agnostic-ish)."""
    compiled = expr.compile(compile_kwargs={"literal_binds": True})
    return str(compiled)


class TestBuildSqlAlchemyFilters:
    """build_sqlalchemy_filters dispatches by operator on real columns."""

    def test_eq_single_emits_equality(self) -> None:
        filters = FilterParser.parse_filters("status:active")
        exprs = FilterParser.build_sqlalchemy_filters(Project, filters)
        assert len(exprs) == 1
        assert "= " in _compile(exprs[0])

    def test_eq_multi_emits_in(self) -> None:
        filters = FilterParser.parse_filters("status:a,b,c")
        exprs = FilterParser.build_sqlalchemy_filters(Project, filters)
        assert len(exprs) == 1
        assert "IN" in _compile(exprs[0]).upper()

    def test_gte_emits_ge(self) -> None:
        filters = FilterParser.parse_filters("contract_value__gte:1000")
        exprs = FilterParser.build_sqlalchemy_filters(Project, filters)
        assert len(exprs) == 1
        assert ">=" in _compile(exprs[0])

    def test_lte_emits_le(self) -> None:
        filters = FilterParser.parse_filters("contract_value__lte:5000")
        exprs = FilterParser.build_sqlalchemy_filters(Project, filters)
        assert len(exprs) == 1
        assert "<=" in _compile(exprs[0])

    def test_between_emits_between(self) -> None:
        filters = FilterParser.parse_filters("contract_value__between:100,500")
        exprs = FilterParser.build_sqlalchemy_filters(Project, filters)
        assert len(exprs) == 1
        assert "BETWEEN" in _compile(exprs[0]).upper()

    def test_date_range_emits_and_pair(self) -> None:
        filters = FilterParser.parse_filters(
            "start_date__date_range:2026-01-01,2026-12-31"
        )
        exprs = FilterParser.build_sqlalchemy_filters(Project, filters)
        assert len(exprs) == 1
        sql = _compile(exprs[0]).upper()
        assert ">=" in sql and "<=" in sql and "AND" in sql

    def test_backward_compat_plain_dict_shape(self) -> None:
        # Legacy callers may still pass a plain column->values dict (no tuple
        # keys). build_sqlalchemy_filters must accept it as eq.
        legacy: dict[str, list[str]] = {"status": ["active"]}
        exprs = FilterParser.build_sqlalchemy_filters(Project, legacy)
        assert len(exprs) == 1

    def test_allowed_operators_forbids_op(self) -> None:
        # contract_value__gte is allowed by URL grammar, but the route may
        # restrict it to eq only via allowed_operators.
        filters = FilterParser.parse_filters("contract_value__gte:1000")
        with pytest.raises(FilterOperatorNotAllowedError):
            FilterParser.build_sqlalchemy_filters(
                Project,
                filters,
                allowed_operators={"contract_value": ["eq"]},
            )

    def test_allowed_operators_permits_listed_op(self) -> None:
        filters = FilterParser.parse_filters("contract_value__gte:1000")
        exprs = FilterParser.build_sqlalchemy_filters(
            Project,
            filters,
            allowed_operators={"contract_value": ["eq", "gte"]},
        )
        assert len(exprs) == 1

    def test_custom_field_eq_still_works(self) -> None:
        # A JSONB custom field on the eq path must still build an expression.
        filters = FilterParser.parse_filters("priority:high")
        exprs = FilterParser.build_sqlalchemy_filters(
            Project,
            filters,
            custom_field_specs={"priority": {"type": "select"}},
        )
        assert len(exprs) == 1

    def test_custom_field_range_raises(self) -> None:
        # G4 scope: custom-field range filtering is out of scope -> error.
        filters = FilterParser.parse_filters("priority__gte:5")
        with pytest.raises(FilterOperatorNotAllowedError):
            FilterParser.build_sqlalchemy_filters(
                Project,
                filters,
                custom_field_specs={"priority": {"type": "number"}},
            )
