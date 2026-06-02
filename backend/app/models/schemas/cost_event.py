"""Pydantic schemas for Cost Event entity (quality and cost event tracking)."""

from datetime import datetime
from decimal import Decimal
from enum import Enum
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, computed_field

from app.models.schemas.mixins import TemporalComputedMixin
from app.models.schemas.temporal_validators import TemporalRange

# --- Allocation schemas ---


class QualityCostAllocation(BaseModel):
    """A quality cost allocation to a specific cost element."""

    cost_element_id: UUID
    amount: Decimal = Field(..., gt=0)
    description: str | None = None


class QualityCostAllocationRead(BaseModel):
    """A quality cost allocation entry (from CostRegistration)."""

    model_config = ConfigDict(from_attributes=True)

    cost_registration_id: UUID
    cost_element_id: UUID
    amount: Decimal
    description: str | None = None
    cost_element_name: str | None = None
    wbs_element_code: str | None = None
    wbs_element_id: UUID | None = None


# --- Cost Event schemas ---


class CostEventBase(BaseModel):
    """Base schema for Cost Event."""

    name: str = Field(..., min_length=1, max_length=255, description="Event name")
    cost_event_type_id: UUID = Field(
        ..., description="Root ID of the CostEventType category"
    )
    description: str | None = None
    status: str = Field(
        default="open",
        pattern="^(open|closed)$",
        description="Event lifecycle status",
    )

    # External reference identifier (e.g., QMS ID, PO number, work order)
    external_event_id: str | None = Field(
        None,
        max_length=100,
        description="External reference identifier (e.g., QMS ID, PO number, work order)",
    )

    # Quality-specific fields (nullable, used when type is quality)
    event_date: datetime | None = None
    coq_category: str | None = Field(
        None,
        pattern="^(prevention|appraisal|internal_failure|external_failure)$",
        description="Cost of Quality category",
    )
    estimated_impact: Decimal = Field(
        default=Decimal("0"), ge=0, description="Estimated financial impact"
    )
    schedule_impact_days: int | None = Field(
        None, ge=0, description="Days of schedule delay"
    )


class CostEventCreate(CostEventBase):
    """Schema for creating a new Cost Event."""

    cost_event_id: UUID = Field(default_factory=uuid4, description="Root Cost Event ID")
    project_id: UUID = Field(..., description="Parent project root ID")
    wbs_element_id: UUID | None = Field(
        None, description="WBS Element root ID where the event occurred"
    )
    control_date: datetime | None = Field(
        None, description="Optional control date for creation (valid_time start)"
    )
    cost_allocations: list[QualityCostAllocation] | None = None


class CostEventUpdate(BaseModel):
    """Schema for updating an existing Cost Event."""

    name: str | None = Field(None, min_length=1, max_length=255)
    cost_event_type_id: UUID | None = None
    project_id: UUID | None = None
    wbs_element_id: UUID | None = None
    description: str | None = None
    status: str | None = Field(None, pattern="^(open|closed)$")

    # External reference identifier
    external_event_id: str | None = Field(
        None,
        max_length=100,
        description="External reference identifier (e.g., QMS ID, PO number, work order)",
    )

    # Quality-specific fields
    event_date: datetime | None = None
    coq_category: str | None = Field(
        None, pattern="^(prevention|appraisal|internal_failure|external_failure)$"
    )
    estimated_impact: Decimal | None = Field(None, ge=0)
    schedule_impact_days: int | None = Field(None, ge=0)

    control_date: datetime | None = Field(
        None, description="Optional control date for update (valid_time start)"
    )
    cost_allocations: list[QualityCostAllocation] | None = None


class CostEventRead(CostEventBase, TemporalComputedMixin):
    """Schema for reading Cost Event data."""

    id: UUID
    cost_event_id: UUID
    project_id: UUID
    wbs_element_id: UUID | None = None
    created_by: UUID
    created_by_name: str | None = None
    valid_time: TemporalRange = None
    transaction_time: TemporalRange = None
    actual_cost: Decimal | None = None
    # Denormalized type info
    cost_event_type_code: str | None = None
    cost_event_type_name: str | None = None

    @computed_field  # type: ignore[prop-decorator]
    @property
    def event_date_formatted(self) -> dict[str, str | None]:
        """Display-ready event date data."""
        if not self.event_date:
            return {"iso": None, "formatted": "Unknown"}

        return {
            "iso": self.event_date.isoformat(),
            "formatted": self.event_date.strftime("%B %d, %Y"),
        }

    model_config = ConfigDict(from_attributes=True)


# --- COQ Summary schemas ---


class CostEventSummary(BaseModel):
    """Aggregated COQ summary for a project (renamed from WorkPackageSummary)."""

    total_cost: Decimal
    prevention_cost: Decimal = Decimal("0")
    appraisal_cost: Decimal = Decimal("0")
    conformance_cost: Decimal = Decimal("0")
    internal_failure_cost: Decimal = Decimal("0")
    external_failure_cost: Decimal = Decimal("0")
    nonconformance_cost: Decimal = Decimal("0")
    total_schedule_days: int
    impact_count: int
    coq_ratio: Decimal | None = None


class COQMetrics(BaseModel):
    """COQ metrics complementing standard EVM indicators."""

    total_coq: Decimal
    cpq: Decimal  # Cost of Poor Quality (nonconformance only)
    cpq_percentage: Decimal  # CPQ / Total AC * 100
    cpiq: Decimal | None = None  # CPQ / AC (quality's share of cost variance)
    qpi: Decimal | None = None  # Quality Performance Index (normalized from CPQ%)
    qpi_rating: str | None = None  # Human-readable QPI rating
    total_ac: Decimal  # Total Actual Cost for the project (for context)
    coq_ratio: Decimal | None = None  # Total COQ / Project Budget * 100


class COQTrendPoint(BaseModel):
    """Single data point for COQ trend time-series."""

    date: datetime
    # Planned costs (from cost event estimated_impact)
    planned_prevention: Decimal = Decimal("0")
    planned_appraisal: Decimal = Decimal("0")
    planned_internal_failure: Decimal = Decimal("0")
    planned_external_failure: Decimal = Decimal("0")
    total_planned: Decimal = Decimal("0")
    # Actual costs (from cost registrations)
    prevention: Decimal = Decimal("0")
    appraisal: Decimal = Decimal("0")
    internal_failure: Decimal = Decimal("0")
    external_failure: Decimal = Decimal("0")
    total_coq: Decimal = Decimal("0")
    cpq: Decimal = Decimal("0")


class COQTrendGranularity(str, Enum):
    """Time granularity for COQ trend aggregation."""

    WEEK = "week"
    MONTH = "month"


class COQTrendResponse(BaseModel):
    """COQ trend time-series response."""

    granularity: COQTrendGranularity
    points: list[COQTrendPoint]
    start_date: datetime
    end_date: datetime
    total_points: int
