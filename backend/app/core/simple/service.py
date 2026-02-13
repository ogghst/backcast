"""Service base class for Simple (non-versioned) entities.

Provides generic CRUD operations for entities satisfying SimpleEntityProtocol.
"""

from typing import TypeVar
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.simple.commands import (
    SimpleCreateCommand,
    SimpleDeleteCommand,
    SimpleUpdateCommand,
)
from app.models.protocols import SimpleEntityProtocol

TSimple = TypeVar("TSimple", bound=SimpleEntityProtocol)


class SimpleService[TSimple: SimpleEntityProtocol]:
    """Generic service for non-versioned entities (config, preferences, etc).

    Type parameter TSimple must satisfy SimpleEntityProtocol.
    """

    def __init__(self, session: AsyncSession, entity_class: type[TSimple]) -> None:
        self.session = session
        self.entity_class = entity_class

    async def get(self, entity_id: UUID) -> TSimple | None:
        """Get entity by ID."""
        return await self.session.get(self.entity_class, entity_id)

    async def list_all(self, skip: int = 0, limit: int = 100000) -> list[TSimple]:
        """List entities with pagination."""
        stmt = select(self.entity_class).offset(skip).limit(limit)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def create(self, **fields: object) -> TSimple:
        """Create new entity."""
        cmd = SimpleCreateCommand(self.entity_class, **fields)
        return await cmd.execute(self.session)

    async def update(self, entity_id: UUID, **updates: object) -> TSimple:
        """Update entity in place."""
        cmd = SimpleUpdateCommand(self.entity_class, entity_id, **updates)
        return await cmd.execute(self.session)

    async def delete(self, entity_id: UUID) -> bool:
        """Hard delete entity, returns True if deleted, False if not found."""
        cmd = SimpleDeleteCommand(self.entity_class, entity_id)
        try:
            return await cmd.execute(self.session)
        except ValueError:
            return False
