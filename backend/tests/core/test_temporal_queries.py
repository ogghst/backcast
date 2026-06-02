"""Tests for temporal_queries utility functions.

Covers is_current_version_raw_sql with and without deleted_at.
"""

from app.core.temporal_queries import is_current_version_raw_sql


def test_raw_sql_with_deleted_at() -> None:
    """is_current_version_raw_sql includes deleted_at IS NULL by default."""
    result = is_current_version_raw_sql()
    assert "upper(valid_time) IS NULL" in result
    assert "deleted_at IS NULL" in result
    assert " AND " in result


def test_raw_sql_without_deleted_at() -> None:
    """is_current_version_raw_sql omits deleted_at clause when deleted_at_col=None."""
    result = is_current_version_raw_sql(deleted_at_col=None)
    assert result == "upper(valid_time) IS NULL"


def test_raw_sql_custom_column_names() -> None:
    """is_current_version_raw_sql uses custom column names."""
    result = is_current_version_raw_sql(
        valid_time_col="my_valid_time", deleted_at_col="my_deleted_at"
    )
    assert "upper(my_valid_time) IS NULL" in result
    assert "my_deleted_at IS NULL" in result
