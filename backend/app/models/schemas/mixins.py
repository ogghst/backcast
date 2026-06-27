"""Shared mixins for Pydantic schemas.

This module provides reusable mixins for common patterns across Pydantic models.
Mixins are used to share computed fields, configuration, and other model
behaviors without duplication.

Using mixins eliminates the need to duplicate computed_field definitions
across multiple schema files.
"""

from datetime import datetime

from pydantic import computed_field

from app.core.temporal import format_temporal_range_for_api


class EntityMetadataMixin:
    """Mixin exposing the standard entity metadata fields.

    Every versioned entity Read schema surfaces the same three derived fields
    so a consumer can reliably find an entity's creator and timestamps:

    - created_by_name: resolved full_name of the creating user (None = System).
    - created_at: true creation time = MIN(lower(transaction_time)) over all
      versions of the root entity. NOT the current version's lower bound
      (which is the last-modification time).
    - updated_at: last-modification time = MAX(lower(transaction_time)) over
      all versions, including soft-deletes (a soft-delete is the latest
      modification and must be reflected here).

    None of these are stored columns; they are populated by
    `populate_creator_names` / `populate_entity_timestamps` on read paths.
    """

    created_by_name: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class TemporalComputedMixin:
    """Mixin for models with temporal computed fields.

    This mixin provides formatted temporal field properties for any schema
    that has valid_time and transaction_time fields. It eliminates the need
    to duplicate computed_field definitions across multiple Read schemas.

    To use:
        1. Add TemporalComputedMixin to your model's inheritance chain
        2. Ensure your model has valid_time and transaction_time fields
        3. The mixin will provide the formatted computed fields

    Example:
        class MyRead(BaseModel, TemporalComputedMixin):
            id: UUID
            valid_time: str | None = None
            transaction_time: str | None = None

        # Now MyRead instances have valid_time_formatted and
        # transaction_time_formatted properties
    """

    @computed_field  # type: ignore[prop-decorator]
    @property
    def valid_time_formatted(self) -> dict[str, str | bool | None]:
        """Display-ready valid_time temporal data.

        Returns pre-formatted temporal range information including:
        - ISO timestamps for machine processing
        - Formatted display strings for UI
        - Validity status

        This allows the frontend to display dates without parsing
        PostgreSQL range syntax.

        Example:
            {
                "lower": "2026-01-15T10:00:00+00:00",
                "upper": null,
                "lower_formatted": "January 15, 2026",
                "upper_formatted": "Present",
                "is_currently_valid": true
            }

        Returns:
            Dictionary with formatted temporal range information
        """
        return format_temporal_range_for_api(getattr(self, "valid_time", None))

    @computed_field  # type: ignore[prop-decorator]
    @property
    def transaction_time_formatted(self) -> dict[str, str | bool | None]:
        """Display-ready transaction_time temporal data.

        Returns pre-formatted temporal range information for the
        transaction time (when this version was created in the system).

        See valid_time_formatted for response format details.

        Returns:
            Dictionary with formatted temporal range information
        """
        return format_temporal_range_for_api(getattr(self, "transaction_time", None))
