"""Pydantic schemas for Dashboard endpoint."""

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class DashboardActivity(BaseModel):
    """Schema for a single dashboard activity item.

    Represents a recently updated entity with metadata for display.
    """

    entity_id: UUID = Field(..., description="Entity identifier")
    entity_name: str = Field(..., description="Entity name/code")
    entity_type: str = Field(
        ...,
        description="Entity type (project, wbe, cost_element, change_order)",
    )
    action: str = Field(
        ...,
        description="Action performed (created, updated, deleted, merged)",
    )
    timestamp: datetime = Field(..., description="When the action occurred")
    actor_id: UUID | None = Field(None, description="User who performed the action")
    actor_name: str | None = Field(
        None, description="Name of user who performed action"
    )
    project_id: UUID | None = Field(
        None,
        description="Parent project ID (for child entities)",
    )
    project_name: str | None = Field(
        None,
        description="Parent project name (for child entities)",
    )
    branch: str = Field(..., description="Branch where action occurred")

    model_config = ConfigDict(from_attributes=True)


class ProjectMetrics(BaseModel):
    """Schema for project metrics in spotlight."""

    total_budget: Decimal = Field(..., description="Total project budget")
    total_wbes: int = Field(..., description="Total number of WBEs")
    total_cost_elements: int = Field(
        ...,
        description="Total number of cost elements",
    )
    active_change_orders: int = Field(
        ...,
        description="Number of active change orders",
    )
    ev_status: str | None = Field(
        None,
        description="Earned Value status (on_track, at_risk, behind)",
    )

    model_config = ConfigDict(from_attributes=True)


class ProjectSpotlight(BaseModel):
    """Schema for the last edited project spotlight."""

    project_id: UUID = Field(..., description="Project identifier")
    project_name: str = Field(..., description="Project name")
    project_code: str = Field(..., description="Project code")
    last_activity: datetime = Field(
        ...,
        description="Timestamp of most recent activity",
    )
    metrics: ProjectMetrics = Field(..., description="Project metrics")
    branch: str = Field(..., description="Branch of last activity")

    model_config = ConfigDict(from_attributes=True)


class DashboardData(BaseModel):
    """Schema for complete dashboard data response."""

    last_edited_project: ProjectSpotlight | None = Field(
        None,
        description="Most recently edited project with metrics",
    )
    recent_activity: dict[str, list[DashboardActivity]] = Field(
        ...,
        description="Recent activity grouped by entity type",
    )

    model_config = ConfigDict(from_attributes=True)
