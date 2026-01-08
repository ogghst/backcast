"""Unit tests for filtering utilities."""

import pytest
from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import declarative_base

from app.core.filtering import FilterParser

# Create a test model
Base = declarative_base()


class TestModel(Base):
    """Test model for filter parser tests."""

    __tablename__ = "test_model"

    id = Column(Integer, primary_key=True)
    status = Column(String)
    branch = Column(String)
    level = Column(Integer)
    name = Column(String)


class TestFilterParserParseFilters:
    """Tests for FilterParser.parse_filters()."""

    def test_parse_single_filter(self) -> None:
        """Test parsing a single filter."""
        result = FilterParser.parse_filters("status:active")
        assert result == {"status": ["active"]}

    def test_parse_multiple_filters(self) -> None:
        """Test parsing multiple filters separated by semicolon."""
        result = FilterParser.parse_filters("status:active;branch:main")
        assert result == {"status": ["active"], "branch": ["main"]}

    def test_parse_multi_value_filter(self) -> None:
        """Test parsing a filter with multiple values."""
        result = FilterParser.parse_filters("branch:main,dev,staging")
        assert result == {"branch": ["main", "dev", "staging"]}

    def test_parse_combined_filters(self) -> None:
        """Test parsing combination of single and multi-value filters."""
        result = FilterParser.parse_filters("status:active;branch:main,dev;level:1,2,3")
        assert result == {
            "status": ["active"],
            "branch": ["main", "dev"],
            "level": ["1", "2", "3"],
        }

    def test_parse_empty_string(self) -> None:
        """Test parsing empty string returns empty dict."""
        result = FilterParser.parse_filters("")
        assert result == {}

    def test_parse_none(self) -> None:
        """Test parsing None returns empty dict."""
        result = FilterParser.parse_filters(None)
        assert result == {}

    def test_parse_whitespace_handling(self) -> None:
        """Test that whitespace is properly trimmed."""
        result = FilterParser.parse_filters(" status : active ; branch : main , dev ")
        assert result == {"status": ["active"], "branch": ["main", "dev"]}

    def test_parse_ignores_malformed_expressions(self) -> None:
        """Test that malformed expressions are ignored."""
        # Missing colon
        result = FilterParser.parse_filters("status:active;invalid;branch:main")
        assert result == {"status": ["active"], "branch": ["main"]}

        # Empty column name
        result = FilterParser.parse_filters(":value;status:active")
        assert result == {"status": ["active"]}

        # Empty value
        result = FilterParser.parse_filters("status:;branch:main")
        assert result == {"branch": ["main"]}

    def test_parse_empty_values_in_list(self) -> None:
        """Test that empty values in comma-separated list are ignored."""
        result = FilterParser.parse_filters("branch:main,,dev,")
        assert result == {"branch": ["main", "dev"]}

    def test_parse_special_characters_in_values(self) -> None:
        """Test parsing values with special characters."""
        result = FilterParser.parse_filters("name:Project-Alpha;status:in-progress")
        assert result == {"name": ["Project-Alpha"], "status": ["in-progress"]}


class TestFilterParserBuildSQLAlchemyFilters:
    """Tests for FilterParser.build_sqlalchemy_filters()."""

    def test_build_single_value_filter(self) -> None:
        """Test building filter with single value (equality check)."""
        filters = {"status": ["active"]}
        expressions = FilterParser.build_sqlalchemy_filters(TestModel, filters)

        assert len(expressions) == 1
        # Check the expression compiles correctly
        expr = expressions[0]
        assert str(expr.compile()) == "test_model.status = :status_1"

    def test_build_multi_value_filter(self) -> None:
        """Test building filter with multiple values (IN clause)."""
        filters = {"branch": ["main", "dev", "staging"]}
        expressions = FilterParser.build_sqlalchemy_filters(TestModel, filters)

        assert len(expressions) == 1
        expr = expressions[0]
        compiled = str(expr.compile())
        assert "test_model.branch IN" in compiled

    def test_build_multiple_filters(self) -> None:
        """Test building multiple filter expressions."""
        filters = {"status": ["active"], "branch": ["main", "dev"]}
        expressions = FilterParser.build_sqlalchemy_filters(TestModel, filters)

        assert len(expressions) == 2

    def test_build_with_allowed_fields(self) -> None:
        """Test building filters with allowed fields whitelist."""
        filters = {"status": ["active"], "branch": ["main"]}
        allowed_fields = ["status", "branch", "level"]

        expressions = FilterParser.build_sqlalchemy_filters(
            TestModel, filters, allowed_fields=allowed_fields
        )

        assert len(expressions) == 2

    def test_build_invalid_field_raises_error(self) -> None:
        """Test that invalid field name raises ValueError."""
        filters = {"invalid_field": ["value"]}

        with pytest.raises(ValueError, match="Invalid filter field 'invalid_field'"):
            FilterParser.build_sqlalchemy_filters(TestModel, filters)

    def test_build_disallowed_field_raises_error(self) -> None:
        """Test that disallowed field raises ValueError."""
        filters = {"status": ["active"], "name": ["test"]}
        allowed_fields = ["status", "branch"]  # 'name' is not allowed

        with pytest.raises(ValueError, match="Filter field 'name' is not allowed"):
            FilterParser.build_sqlalchemy_filters(
                TestModel, filters, allowed_fields=allowed_fields
            )

    def test_build_empty_filters(self) -> None:
        """Test building with empty filters dict."""
        expressions = FilterParser.build_sqlalchemy_filters(TestModel, {})
        assert expressions == []

    def test_build_all_allowed_when_no_whitelist(self) -> None:
        """Test that all model fields are allowed when no whitelist provided."""
        filters = {"status": ["active"], "branch": ["main"], "level": ["1"], "name": ["test"]}

        # Should not raise error
        expressions = FilterParser.build_sqlalchemy_filters(TestModel, filters)
        assert len(expressions) == 4


class TestFilterParserIntegration:
    """Integration tests for parse + build workflow."""

    def test_full_workflow_single_filter(self) -> None:
        """Test complete workflow: parse URL string -> build SQL expressions."""
        filter_string = "status:active"

        # Parse
        filters = FilterParser.parse_filters(filter_string)
        assert filters == {"status": ["active"]}

        # Build
        expressions = FilterParser.build_sqlalchemy_filters(TestModel, filters)
        assert len(expressions) == 1

    def test_full_workflow_complex_filters(self) -> None:
        """Test complete workflow with complex filter string."""
        filter_string = "status:active;branch:main,dev;level:1,2,3"

        # Parse
        filters = FilterParser.parse_filters(filter_string)
        assert len(filters) == 3

        # Build with whitelist
        allowed_fields = ["status", "branch", "level"]
        expressions = FilterParser.build_sqlalchemy_filters(
            TestModel, filters, allowed_fields=allowed_fields
        )
        assert len(expressions) == 3

    def test_full_workflow_with_validation(self) -> None:
        """Test workflow with field validation."""
        filter_string = "status:active;invalid_field:value"

        # Parse (should succeed)
        filters = FilterParser.parse_filters(filter_string)
        assert "invalid_field" in filters

        # Build (should fail on invalid field)
        with pytest.raises(ValueError, match="Invalid filter field"):
            FilterParser.build_sqlalchemy_filters(TestModel, filters)

    def test_sql_injection_prevention(self) -> None:
        """Test that SQL injection attempts are safely handled."""
        # Attempt SQL injection in filter string
        # Note: Semicolons are filter separators, so this gets split
        malicious_string = "status:active'; DROP TABLE users; --"

        # Parse (semicolons split the filters, so we get partial parsing)
        filters = FilterParser.parse_filters(malicious_string)
        # The semicolon splits it, so we only get "status:active'"
        assert filters == {"status": ["active'"]}

        # Build (SQLAlchemy parameterizes, preventing injection)
        expressions = FilterParser.build_sqlalchemy_filters(TestModel, filters)
        assert len(expressions) == 1

        # The value is parameterized, not injected into SQL
        expr = expressions[0]
        compiled = str(expr.compile())
        assert "DROP TABLE" not in compiled
        assert ":status_" in compiled  # Parameterized

    def test_sql_injection_prevention_in_value(self) -> None:
        """Test SQL injection attempts within a value (no special delimiters)."""
        # Malicious value without semicolons or commas
        malicious_string = "name:Robert' OR '1'='1"

        # Parse (treats entire string after colon as value)
        filters = FilterParser.parse_filters(malicious_string)
        assert filters == {"name": ["Robert' OR '1'='1"]}

        # Build (SQLAlchemy parameterizes, preventing injection)
        expressions = FilterParser.build_sqlalchemy_filters(TestModel, filters)
        assert len(expressions) == 1

        # The malicious value is safely parameterized
        expr = expressions[0]
        compiled = str(expr.compile())
        assert "OR '1'='1'" not in compiled  # Not in SQL
        assert ":name_" in compiled  # Parameterized
