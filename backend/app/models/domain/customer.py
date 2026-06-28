"""Customer domain model - non-versioned entity.

Stores customers (clients) for portfolio attribution. A project may reference a
customer via its root-id ``customer_id`` column. Non-versioned reference data —
satisfies SimpleEntityProtocol via SimpleEntityBase.
"""

import sqlalchemy as sa
from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.schema import Index

from app.core.base.base import SimpleEntityBase


class Customer(SimpleEntityBase):
    """Customer entity - non-versioned with audit timestamps.

    Attributes:
        code: Short unique customer code among active customers (e.g. "ACME").
            Soft-deleted/inactive rows may reuse a code, but at most one active
            customer may carry any given code (partial unique index).
        name: Human-readable customer name.
        description: Optional free-text description.
        is_active: Whether this customer is currently active.
    """

    __tablename__ = "customers"

    code: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(
        sa.Boolean,
        nullable=False,
        default=True,
        server_default=sa.text("true"),
    )

    # Active codes are unique (soft-deleted rows may reuse a code). Mirrors the
    # postgresql_where partial-index convention used by the versioned entities
    # (e.g. project.py / work_package.py).
    __table_args__ = (
        Index(
            "uq_customers_code_active",
            "code",
            unique=True,
            postgresql_where=sa.text("is_active"),
        ),
    )

    def __repr__(self) -> str:
        return (
            f"<Customer(id={self.id}, code={self.code!r}, name={self.name!r}, "
            f"is_active={self.is_active})>"
        )
