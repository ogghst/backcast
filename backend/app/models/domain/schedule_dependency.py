"""Schedule Dependency domain model - links between schedule baselines.

Defines predecessor/successor relationships between Schedule Baselines,
supporting standard dependency types (FS, SS, FF, SF) with optional lag.

Simple entity - no versioning required. Dependencies are recreated when
baselines change.
"""

from sqlalchemy import Index, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import ENUM as PG_ENUM
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.base.base import SimpleEntityBase

# Define PostgreSQL ENUM for dependency types
DEPENDENCY_TYPE_ENUM = PG_ENUM(
    "FS",
    "SS",
    "FF",
    "SF",
    name="dependency_type",
    create_type=True,
)


class ScheduleDependency(SimpleEntityBase):
    """Schedule Dependency - predecessor/successor link between work packages.

    Defines the relationship between two work packages (via their schedule baselines)
    for Gantt chart rendering and schedule network analysis.

    Attributes:
        schedule_dependency_id: Root ID for the dependency (stable identity).
        predecessor_id: Work Package root ID of the predecessor activity.
        successor_id: Work Package root ID of the successor activity.
        dependency_type: Type of dependency (FS=Finish-Start, SS=Start-Start,
            FF=Finish-Finish, SF=Start-Finish).
        lag_days: Number of days offset between predecessor and successor.
        branch: Branch name for change order isolation.
        project_id: Project root ID (denormalized for fast queries).
    """

    __tablename__ = "schedule_dependencies"

    schedule_dependency_id: Mapped[str] = mapped_column(
        PG_UUID, nullable=False, index=True
    )
    predecessor_id: Mapped[str] = mapped_column(PG_UUID, nullable=False, index=True)
    successor_id: Mapped[str] = mapped_column(PG_UUID, nullable=False, index=True)
    dependency_type: Mapped[str] = mapped_column(
        DEPENDENCY_TYPE_ENUM, nullable=False, default="FS"
    )
    lag_days: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    branch: Mapped[str] = mapped_column(String(100), nullable=False, default="main")
    project_id: Mapped[str] = mapped_column(PG_UUID, nullable=False, index=True)

    __table_args__ = (
        Index(
            "ix_schedule_dependencies_predecessor_branch",
            "predecessor_id",
            "branch",
        ),
        Index(
            "ix_schedule_dependencies_successor_branch",
            "successor_id",
            "branch",
        ),
        Index(
            "ix_schedule_dependencies_project_branch",
            "project_id",
            "branch",
        ),
        UniqueConstraint(
            "predecessor_id",
            "successor_id",
            "dependency_type",
            "branch",
            name="uq_schedule_dependency_link",
        ),
    )

    def __repr__(self) -> str:
        return (
            f"<ScheduleDependency(id={self.id}, "
            f"predecessor_id={self.predecessor_id}, "
            f"successor_id={self.successor_id}, "
            f"dependency_type={self.dependency_type}, "
            f"lag_days={self.lag_days})>"
        )
