"""Pydantic schemas for Gantt chart data."""

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class GanttItem(BaseModel):
    """A single item in the Gantt chart (work package with schedule).

    Supports WBEs without work packages - work package fields will be null.
    """

    model_config = ConfigDict(from_attributes=True)

    # NOTE: holds work_package_id despite the field name — retained for API compatibility
    cost_element_id: UUID | None = None
    cost_element_code: str | None = None
    cost_element_name: str | None = None
    wbs_element_id: UUID
    wbe_code: str
    wbe_name: str
    wbe_level: int
    parent_wbs_element_id: UUID | None = None
    budget_amount: Decimal | None = None
    start_date: datetime | None = None
    end_date: datetime | None = None
    progression_type: str | None = None


class GanttDependencyLink(BaseModel):
    """A dependency arrow between two schedule bars in the Gantt chart."""

    dependency_id: UUID
    predecessor_id: UUID  # work_package_id root ID
    successor_id: UUID  # work_package_id root ID
    dependency_type: str  # FS, SS, FF, SF
    lag_days: int


class GanttDataResponse(BaseModel):
    """Response containing all Gantt data for a project."""

    items: list[GanttItem]
    project_start: datetime | None = None
    project_end: datetime | None = None
    dependencies: list[GanttDependencyLink] = []
