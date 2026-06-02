"""Pydantic schemas for Gantt chart data."""

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class GanttItem(BaseModel):
    """A single item in the Gantt chart (cost element with schedule).

    Supports WBEs without cost elements - cost element fields will be null.
    """

    model_config = ConfigDict(from_attributes=True)

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


class GanttDataResponse(BaseModel):
    """Response containing all Gantt data for a project."""

    items: list[GanttItem]
    project_start: datetime | None = None
    project_end: datetime | None = None
