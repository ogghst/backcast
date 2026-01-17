"""Schedule Baseline domain model - Planned Value (PV) calculation schedule.

Schedule Baselines define the time-phased budget plan for cost elements,
supporting Earned Value Management (EVM) calculations via progression types.

Branchable and Versionable - baselines can vary across change orders and time.
"""

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import ENUM as PG_ENUM
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.base.base import EntityBase
from app.models.mixins import BranchableMixin, VersionableMixin

if TYPE_CHECKING:
    pass


# Define PostgreSQL ENUM for progression types
PROGRESSION_TYPE_ENUM = PG_ENUM(
    "LINEAR",
    "GAUSSIAN",
    "LOGARITHMIC",
    name="progression_type",
    create_type=True,
)


class ScheduleBaseline(EntityBase, VersionableMixin, BranchableMixin):
    """Schedule Baseline - time-phased budget plan for EVM Planned Value (PV).

    Schedule Baselines define how budget is planned to be earned over time,
    supporting different progression patterns (Linear, Gaussian S-curve, Logarithmic).

    Branchable (supports change orders) and Versionable (tracks changes).

    Attributes:
        schedule_baseline_id: Root ID for the Schedule Baseline aggregation.
        cost_element_id: Reference to the cost element this baseline applies to.
        name: Human-readable name for the baseline (e.g., "Q1 2026 Baseline").
        start_date: When the schedule begins.
        end_date: When the schedule ends.
        progression_type: Type of progression curve (LINEAR, GAUSSIAN, LOGARITHMIC).
        description: Optional description of the baseline.

    Examples:
        - Linear: "Q1 2026 Baseline" - uniform progress over time
        - Gaussian: "Standard S-curve" - slow start, fast middle, tapering end
        - Logarithmic: "Front-loaded" - rapid initial progress, slow finish

    Satisfies: BranchableProtocol, VersionableProtocol
    """

    __tablename__ = "schedule_baselines"

    # Root ID (stable identity across versions/branches)
    schedule_baseline_id: Mapped[UUID] = mapped_column(
        PG_UUID, nullable=False, index=True
    )

    # Foreign key to cost element
    cost_element_id: Mapped[UUID] = mapped_column(
        PG_UUID,
        ForeignKey("cost_elements.cost_element_id"),
        nullable=False,
        index=True,
    )

    # Identity
    name: Mapped[str] = mapped_column(String(255), nullable=False)

    # Schedule dates
    start_date: Mapped[datetime] = mapped_column(
        nullable=False,
        index=True,
    )
    end_date: Mapped[datetime] = mapped_column(
        nullable=False,
        index=True,
    )

    # Progression type (ENUM)
    progression_type: Mapped[str] = mapped_column(
        PROGRESSION_TYPE_ENUM,
        nullable=False,
        default="LINEAR",
    )

    # Optional description
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Temporal fields inherited from VersionableMixin:
    # - valid_time: TSTZRANGE
    # - transaction_time: TSTZRANGE
    # - deleted_at: datetime | None
    # - created_by: UUID
    # - deleted_by: UUID | None

    # Branching fields inherited from BranchableMixin:
    # - branch: str (default "main")
    # - parent_id: UUID | None
    # - merge_from_branch: str | None

    def __repr__(self) -> str:
        return (
            f"<ScheduleBaseline(id={self.id}, "
            f"schedule_baseline_id={self.schedule_baseline_id}, "
            f"cost_element_id={self.cost_element_id}, "
            f"name='{self.name}', "
            f"start_date={self.start_date}, "
            f"end_date={self.end_date}, "
            f"progression_type={self.progression_type})>"
        )
