"""Base classes for all database entities.

Provides:
- Base: SQLAlchemy declarative base
- EntityBase: Abstract base with UUID primary key
- SimpleEntityBase: Non-versioned entities with created_at/updated_at
"""

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, func
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy ORM models."""

    pass


class EntityBase(Base):
    """Abstract base for all entities - provides UUID primary key.

    Satisfies: EntityProtocol
    """

    __abstract__ = True

    id: Mapped[UUID] = mapped_column(PG_UUID, primary_key=True, default=uuid4)


class SimpleEntityBase(EntityBase):
    """Non-versioned entities with created_at/updated_at timestamps.

    Satisfies: SimpleEntityProtocol

    Use for: user preferences, system configuration, lookup tables,
    transient data without audit requirements.
    """

    __abstract__ = True

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
