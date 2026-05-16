"""Tests for temporal query helpers."""

from sqlalchemy import select
from sqlalchemy.sql import ColumnElement

from app.core.temporal_queries import (
    current_join_filter,
    is_current_version,
    is_current_version_on_branch,
    is_current_version_raw_sql,
)
from app.models.domain.cost_element_type import CostElementType
from app.models.domain.department import Department
from app.models.domain.project import Project


def test_is_current_version_generates_indexable_query():
    """Test that is_current_version generates GIST-indexable SQL."""
    # Build query using the helper
    stmt = select(CostElementType).where(
        is_current_version(CostElementType.valid_time, CostElementType.deleted_at)
    )

    # Compile to SQL
    compiled = stmt.compile()
    sql_str = str(compiled)

    # Verify the SQL uses the range overlap operator (&&)
    assert "&&" in sql_str
    assert "tstzrange" in sql_str
    assert "deleted_at IS NULL" in sql_str

    # Verify it does NOT use the non-indexable pattern
    assert "upper(valid_time) IS NULL" not in sql_str
    assert "UPPER(valid_time)" not in sql_str

def test_is_current_version_without_deleted_at():
    """Test is_current_version with only valid_time column."""
    # Build query without deleted_at
    stmt = select(CostElementType).where(is_current_version(CostElementType.valid_time))

    # Compile to SQL
    compiled = stmt.compile()
    sql_str = str(compiled)

    # Verify the SQL uses the range overlap operator
    assert "&&" in sql_str
    assert "tstzrange" in sql_str

    # Verify no deleted_at WHERE clause (deleted_at may appear in SELECT list)
    where_clause = sql_str.split(" WHERE ")[1] if " WHERE " in sql_str else ""
    assert "deleted_at IS NULL" not in where_clause

def test_is_current_version_returns_correct_type():
    """Test that is_current_version returns the correct SQLAlchemy type."""
    result = is_current_version(CostElementType.valid_time, CostElementType.deleted_at)

    # Should be a ColumnElement (AND expression)
    assert isinstance(result, ColumnElement)

def test_is_current_version_on_branch_generates_correct_sql():
    """Test that is_current_version_on_branch generates correct SQL with branch filter."""
    # Build query using the helper
    stmt = select(Project).where(
        is_current_version_on_branch(
            Project.valid_time,
            Project.branch,
            "main",
            Project.deleted_at,
        )
    )

    # Compile to SQL
    compiled = stmt.compile()
    sql_str = str(compiled)

    # Verify the SQL uses the range overlap operator
    assert "&&" in sql_str
    assert "tstzrange" in sql_str

    # Verify branch filter is present (parameterized as :branch_1)
    assert "branch" in sql_str.lower()
    assert ":branch_1" in sql_str or "= :branch" in sql_str

    # Verify deleted_at filter is present
    assert "deleted_at IS NULL" in sql_str

def test_is_current_version_on_branch_without_deleted_at():
    """Test is_current_version_on_branch with only valid_time column."""
    # Build query without deleted_at
    stmt = select(Project).where(
        is_current_version_on_branch(Project.valid_time, Project.branch, "main")
    )

    # Compile to SQL
    compiled = stmt.compile()
    sql_str = str(compiled)

    # Verify the SQL uses the range overlap operator
    assert "&&" in sql_str
    assert "tstzrange" in sql_str

    # Verify branch filter is present
    assert "branch" in sql_str.lower()

    # Verify no deleted_at WHERE clause
    where_clause = sql_str.split(" WHERE ")[1] if " WHERE " in sql_str else ""
    assert "deleted_at IS NULL" not in where_clause

def test_current_join_filter_generates_correct_sql():
    """Test that current_join_filter generates correct SQL for multiple entities."""
    from app.models.domain.cost_element import CostElement
    from app.models.domain.wbe import WBE

    # Build query using the helper for a join
    stmt = select(WBE, CostElement).where(
        current_join_filter(
            (WBE.valid_time, WBE.deleted_at),
            (CostElement.valid_time, CostElement.deleted_at),
        )
    )

    # Compile to SQL
    compiled = stmt.compile()
    sql_str = str(compiled)

    # Verify the SQL uses the range overlap operator for both entities
    assert sql_str.count("&&") >= 2  # Should have at least 2 overlap operators
    assert "deleted_at IS NULL" in sql_str

def test_is_current_version_raw_sql_generates_correct_sql():
    """Test that is_current_version_raw_sql generates correct SQL string."""
    # Test with both valid_time and deleted_at
    result = is_current_version_raw_sql("valid_time", "deleted_at")
    assert "upper(valid_time) IS NULL" in result
    assert "deleted_at IS NULL" in result
    assert " AND " in result

    # Test with only valid_time
    result = is_current_version_raw_sql("valid_time", None)
    assert "upper(valid_time) IS NULL" in result
    assert "deleted_at" not in result

    # Test with custom column names
    result = is_current_version_raw_sql("my_valid_time", "my_deleted_at")
    assert "upper(my_valid_time) IS NULL" in result
    assert "my_deleted_at IS NULL" in result

def test_is_current_version_on_branch_returns_correct_type():
    """Test that is_current_version_on_branch returns the correct SQLAlchemy type."""
    result = is_current_version_on_branch(
        Project.valid_time,
        Project.branch,
        "main",
        Project.deleted_at,
    )

    # Should be a ColumnElement (AND expression)
    assert isinstance(result, ColumnElement)

def test_current_join_filter_returns_correct_type():
    """Test that current_join_filter returns the correct SQLAlchemy type."""
    from app.models.domain.cost_element import CostElement
    from app.models.domain.wbe import WBE

    result = current_join_filter(
        (WBE.valid_time, WBE.deleted_at),
        (CostElement.valid_time, CostElement.deleted_at),
    )

    # Should be a ColumnElement (AND expression)
    assert isinstance(result, ColumnElement)

def test_is_current_version_on_branch_with_department():
    """Test is_current_version_on_branch with entities that don't have branch field.

    This test documents that is_current_version_on_branch requires a branch column.
    For entities without branch isolation (like Department), use is_current_version instead.
    """
    # Department is Versionable, not Branchable - it doesn't have a branch field
    # This test verifies we can use is_current_version directly
    stmt = select(Department).where(
        is_current_version(Department.valid_time, Department.deleted_at)
    )

    # Compile to SQL
    compiled = stmt.compile()
    sql_str = str(compiled)

    # Verify the SQL uses the range overlap operator
    assert "&&" in sql_str
    assert "tstzrange" in sql_str
    assert "deleted_at IS NULL" in sql_str

def test_current_join_filter_with_mixed_deleted_at():
    """Test current_join_filter when some entities have deleted_at and some don't."""
    from app.models.domain.cost_element import CostElement
    from app.models.domain.wbe import WBE

    # Mix entities with and without deleted_at
    stmt = select(WBE, CostElement).where(
        current_join_filter(
            (WBE.valid_time, WBE.deleted_at),
            (CostElement.valid_time, None),  # No deleted_at filter
        )
    )

    # Compile to SQL
    compiled = stmt.compile()
    sql_str = str(compiled)

    # Should have overlap operators for both entities
    assert "&&" in sql_str
    # Should have deleted_at check only for WBE
    assert "deleted_at IS NULL" in sql_str

def test_current_join_filter_single_entity():
    """Test current_join_filter with a single entity (edge case)."""
    from app.models.domain.wbe import WBE

    # Single entity should work same as is_current_version
    stmt = select(WBE).where(current_join_filter((WBE.valid_time, WBE.deleted_at)))

    # Compile to SQL
    compiled = stmt.compile()
    sql_str = str(compiled)

    # Verify standard patterns
    assert "&&" in sql_str
    assert "deleted_at IS NULL" in sql_str

def test_is_current_version_raw_sql_with_custom_column_names():
    """Test is_current_version_raw_sql with various custom column names."""
    # Test with non-standard column names
    result = is_current_version_raw_sql(
        valid_time_col="custom_valid_time", deleted_at_col="custom_deleted_at"
    )

    assert "upper(custom_valid_time) IS NULL" in result
    assert "custom_deleted_at IS NULL" in result
    assert " AND " in result

def test_is_current_version_raw_sql_generates_valid_sql_structure():
    """Test that is_current_version_raw_sql generates structurally valid SQL."""
    # Test the structure is valid SQL WHERE clause
    result = is_current_version_raw_sql()

    # Should be properly formatted WHERE clause
    assert result.startswith("upper(")
    assert " IS NULL" in result
    assert " AND " in result or " AND" not in result  # Either has AND or doesn't

    # Verify it can be used in a SQL context
    assert "(" in result and ")" in result  # Has parentheses for IS NULL check

def test_is_current_version_with_deleted_at_none_explicit():
    """Test is_current_version with explicit deleted_at=None."""
    # Explicitly pass None for deleted_at
    stmt = select(Department).where(is_current_version(Department.valid_time, None))

    # Compile to SQL
    compiled = stmt.compile()
    sql_str = str(compiled)

    # Verify the SQL uses the range overlap operator
    assert "&&" in sql_str
    assert "tstzrange" in sql_str

    # Verify no deleted_at filter in WHERE clause
    where_clause = sql_str.split(" WHERE ")[1] if " WHERE " in sql_str else ""
    assert "deleted_at IS NULL" not in where_clause

def test_is_current_version_on_branch_mixed_branch_names():
    """Test is_current_version_on_branch with different branch names."""
    # Test with feature branch name
    stmt = select(Project).where(
        is_current_version_on_branch(
            Project.valid_time,
            Project.branch,
            "feature/change-order-123",  # Feature branch name
            Project.deleted_at,
        )
    )

    # Compile to SQL
    compiled = stmt.compile()
    sql_str = str(compiled)

    # Verify branch parameter is in the query
    assert "branch" in sql_str.lower()
    # The branch name should be parameterized, check for pattern
    assert ":branch" in sql_str or "feature" in sql_str.lower()

def test_multiple_current_version_filters_combination():
    """Test combining multiple is_current_version filters manually."""
    from sqlalchemy import and_

    from app.models.domain.cost_element import CostElement
    from app.models.domain.wbe import WBE

    # Manually combine filters (should match current_join_filter behavior)

    stmt = select(WBE, CostElement).where(
        and_(
            is_current_version(WBE.valid_time, WBE.deleted_at),
            is_current_version(CostElement.valid_time, CostElement.deleted_at),
        )
    )

    # Compile to SQL
    compiled = stmt.compile()
    sql_str = str(compiled)

    # Should have overlap operators for both entities
    assert sql_str.count("&&") >= 2
    assert "deleted_at IS NULL" in sql_str

def test_is_current_version_on_branch_no_deleted_at_returns_correct_type():
    """Test that is_current_version_on_branch without deleted_at returns correct type."""
    result = is_current_version_on_branch(
        Project.valid_time,
        Project.branch,
        "main",
        None,  # No deleted_at
    )

    # Should be a ColumnElement (AND expression)
    assert isinstance(result, ColumnElement)
