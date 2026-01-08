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

from sqlalchemy import BinaryExpression
from sqlalchemy.orm import DeclarativeMeta


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
    ) -> list[BinaryExpression[Any]]:
        """Build SQLAlchemy filter expressions from parsed filters.

        Args:
            model: SQLAlchemy model class
            filters: Parsed filters dictionary (from parse_filters)
            allowed_fields: Optional list of allowed field names.
                If None, all model attributes are allowed.

        Returns:
            List of SQLAlchemy binary expressions for WHERE clause

        Raises:
            ValueError: If a field name is invalid or not allowed

        Examples:
            >>> from app.models.domain.project import Project
            >>> filters = {"status": ["active"], "branch": ["main", "dev"]}
            >>> expressions = FilterParser.build_sqlalchemy_filters(
            ...     Project, filters, allowed_fields=["status", "branch"]
            ... )
            >>> # Returns: [Project.status == "active", Project.branch.in_(["main", "dev"])]

        Security:
            - Field names are validated against the model
            - Only whitelisted fields (if provided) can be filtered
            - SQL injection is prevented through SQLAlchemy ORM
        """
        expressions: list[BinaryExpression[Any]] = []

        for field_name, values in filters.items():
            # Validate field exists on model
            if not hasattr(model, field_name):
                raise ValueError(
                    f"Invalid filter field '{field_name}' for model {model.__name__}"
                )

            # Validate field is in allowed list (if provided)
            if allowed_fields is not None and field_name not in allowed_fields:
                raise ValueError(
                    f"Filter field '{field_name}' is not allowed. "
                    f"Allowed fields: {', '.join(allowed_fields)}"
                )

            # Get the column from the model
            column = getattr(model, field_name)

            # Build expression based on number of values
            if len(values) == 1:
                # Single value: equality check
                expressions.append(column == values[0])
            else:
                # Multiple values: IN clause
                expressions.append(column.in_(values))

        return expressions
