"""Department domain model with bitemporal versioning.

Single-table pattern for versioned department profiles.
Satisfies VersionableProtocol.
"""

from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import Boolean, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.base.base import EntityBase
from app.models.mixins import VersionableMixin

if TYPE_CHECKING:
    from app.models.domain.user import User


class Department(EntityBase, VersionableMixin):
    """Department entity - versioned with bitemporal tracking.

    Single table storing all department data with version history:
    - Identity: department_id (root ID), code
    - Profile: name, manager_id, is_active
    - Temporal: valid_time, transaction_time, deleted_at

    Note: No branching (Departments are Versionable, not Branchable)

    Satisfies: VersionableProtocol
    """

    __tablename__ = "departments"

    # Root ID (stable identity across versions)
    department_id: Mapped[UUID] = mapped_column(PG_UUID, nullable=False, index=True)

    # Identity
    code: Mapped[str] = mapped_column(String(50), index=True, nullable=False)

    # Profile (versioned)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    manager_id: Mapped[UUID | None] = mapped_column(
        PG_UUID, ForeignKey("users.user_id"), nullable=True
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    description: Mapped[str | None] = mapped_column(String(5000), nullable=True)

    # Temporal fields inherited from VersionableMixin:
    # - valid_time: TSTZRANGE
    # - transaction_time: TSTZRANGE
    # - deleted_at: datetime | None

    # Relationships
    manager: Mapped["User"] = relationship(
        "app.models.domain.user.User", foreign_keys=[manager_id]
    )

    def __repr__(self) -> str:
        return f"<Department(id={self.id}, department_id={self.department_id}, code={self.code}, name={self.name})>"
