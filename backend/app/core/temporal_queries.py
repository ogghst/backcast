"""Temporal query helpers for PostgreSQL TSTZRANGE fields.

This module provides reusable query builders for temporal entities.

The range overlap operator (``&&``) plus ``upper_inf()`` predicate used here is
GIST-indexable IF a GIST index on ``valid_time`` is defined for the table.
Most temporal tables currently LACK such an index, so the predicate degrades
to a sequential scan. The alternative form ``upper(valid_time) IS NULL`` (used
by :func:`is_current_version_raw_sql`) is NEVER GIST-indexable because it
applies a function to the column.
"""

from typing import Any

from sqlalchemy import and_, cast, func
from sqlalchemy.dialects.postgresql import TIMESTAMP
from sqlalchemy.orm import InstrumentedAttribute
from sqlalchemy.sql import ColumnElement, literal


def is_current_version(
    valid_time_column: ColumnElement[Any] | InstrumentedAttribute[Any],
    deleted_at_column: Any
    | None = None,  # InstrumentedAttribute[datetime | None] is compatible
) -> ColumnElement[Any]:
    """Build WHERE clause for current temporal versions.

    This function creates a WHERE condition that filters for currently valid
    versions using the range overlap operator (``&&``) combined with an
    unbounded range, then narrows with ``upper_inf()`` to exclude closed ranges.

    The predicate is equivalent to ``upper(valid_time) IS NULL`` but, unlike that
    form, is GIST-indexable IF a GIST index on ``valid_time`` is defined for the
    table.

    Args:
        valid_time_column: The TSTZRANGE column to check (e.g., CostElementType.valid_time)
        deleted_at_column: Optional deleted_at column for soft-delete filtering

    Returns:
        SQLAlchemy WHERE clause that filters for current versions

    Examples:
        >>> from app.models.domain.cost_element_type import CostElementType
        >>> stmt = select(CostElementType).where(
        ...     is_current_version(CostElementType.valid_time, CostElementType.deleted_at)
        ... )

        >>> # For entities without soft delete
        >>> stmt = select(Department).where(
        ...     is_current_version(Department.valid_time)
        ... )

    Performance:
        The ``&&`` + ``upper_inf()`` predicate is GIST-indexable IF a GIST index on
        ``valid_time`` is defined for the table. Most temporal tables currently LACK
        such an index, so this degrades to a sequential scan. ``upper(valid_time) IS NULL``
        (used by :func:`is_current_version_raw_sql`) is NEVER GIST-indexable.
    """
    conditions: list[ColumnElement[Any]] = [
        # Use range overlap operator with unbounded range for GIST index narrowing
        # Then add upper_inf check to exclude closed ranges (overlap matches too broadly)
        # Together: index-friendly initial filter + precise upper-bound check
        valid_time_column.op("&&")(
            func.tstzrange(
                cast(literal("-infinity"), TIMESTAMP(timezone=True)),
                cast(literal("infinity"), TIMESTAMP(timezone=True)),
                literal("[]"),
            )
        ),
        func.upper_inf(valid_time_column),
    ]

    # Add soft-delete check if column provided
    if deleted_at_column is not None:
        conditions.append(deleted_at_column.is_(None))

    return and_(*conditions)


def is_current_version_on_branch(
    valid_time_column: ColumnElement[Any] | InstrumentedAttribute[Any],
    branch_column: ColumnElement[Any] | InstrumentedAttribute[Any],
    branch_name: str,
    deleted_at_column: Any | None = None,
) -> ColumnElement[Any]:
    """Current version filter with branch isolation.

    Combines temporal current version filtering with branch isolation
    for branchable entities. This is the standard filter for queries
    that need both temporal and branch filtering.

    Args:
        valid_time_column: The TSTZRANGE column to check
        branch_column: The branch column for filtering
        branch_name: Branch name to filter by
        deleted_at_column: Optional deleted_at column for soft-delete filtering

    Returns:
        SQLAlchemy WHERE clause that filters for current versions on specified branch

    Examples:
        >>> from app.models.domain.project import Project
        >>> stmt = select(Project).where(
        ...     is_current_version_on_branch(
        ...         Project.valid_time,
        ...         Project.branch,
        ...         "main",
        ...         Project.deleted_at
        ...     )
        ... )

    Performance:
        Inherits the GIST-indexability characteristics of :func:`is_current_version`:
        index-accelerated only if a GIST index on ``valid_time`` is defined; otherwise
        a sequential scan.
    """
    conditions = [
        is_current_version(valid_time_column, deleted_at_column),
        branch_column == branch_name,
    ]
    return and_(*conditions)


def current_join_filter(
    *entity_valid_time_pairs: tuple[
        ColumnElement[Any] | InstrumentedAttribute[Any], Any | None
    ],
) -> ColumnElement[Any]:
    """Generate filters for multiple temporal entities in joins.

    When querying with joins involving multiple temporal entities, this helper
    ensures all entities are filtered to their current versions consistently.

    Args:
        *entity_valid_time_pairs: Variable number of (valid_time, deleted_at) tuples
                                 for each entity in the join

    Returns:
        SQLAlchemy WHERE clause with all current version filters combined

    Examples:
        >>> from app.models.domain.wbs_element import WBSElement
        >>> from app.models.domain.cost_element import CostElement
        >>> stmt = select(WBE, CostElement).where(
        ...     current_join_filter(
        ...         (WBE.valid_time, WBE.deleted_at),
        ...         (CostElement.valid_time, CostElement.deleted_at)
        ...     )
        ... )
    """
    conditions = []
    for valid_time, deleted_at in entity_valid_time_pairs:
        conditions.append(is_current_version(valid_time, deleted_at))
    return and_(*conditions)


def is_current_version_raw_sql(
    valid_time_col: str = "valid_time",
    deleted_at_col: str | None = "deleted_at",
) -> str:
    """Return SQL WHERE clause for raw text() queries.

    For use in raw SQL queries using SQLAlchemy's text() construct.
    Provides the same filtering logic as is_current_version() but
    returns a SQL string instead of a ColumnElement.

    Args:
        valid_time_col: Name of the valid_time column (default: "valid_time")
        deleted_at_col: Name of the deleted_at column, or None if no soft delete (default: "deleted_at")

    Returns:
        SQL WHERE clause as string

    Examples:
        >>> from sqlalchemy import text
        >>> where_clause = is_current_version_raw_sql()
        >>> stmt = text("SELECT * FROM projects WHERE " + where_clause)

        >>> # For entities without soft delete
        >>> where_clause = is_current_version_raw_sql(deleted_at_col=None)
    """
    parts = [f"upper({valid_time_col}) IS NULL"]
    if deleted_at_col:
        parts.append(f"{deleted_at_col} IS NULL")
    return " AND ".join(parts)
