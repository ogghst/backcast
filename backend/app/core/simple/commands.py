"""Commands for Simple (non-versioned) entities.

Provides generic CRUD commands for entities satisfying SimpleEntityProtocol:
- SimpleCreateCommand: Creates new entity
- SimpleUpdateCommand: Updates entity in place
- SimpleDeleteCommand: Hard deletes entity
"""

from abc import ABC, abstractmethod
from typing import Any, TypeVar
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.protocols import SimpleEntityProtocol

TSimple = TypeVar("TSimple", bound=SimpleEntityProtocol)


class SimpleCommandABC[TSimple: SimpleEntityProtocol](ABC):
    """ABC for non-versioned entity commands.

    Type parameter TSimple must satisfy SimpleEntityProtocol.
    """

    entity_class: type[TSimple]

    @abstractmethod
    async def execute(self, session: AsyncSession) -> TSimple | bool:
        """Execute the command and return the result.

        Returns TSimple for create/update operations, bool for delete.
        """
        ...


class SimpleCreateCommand(SimpleCommandABC[TSimple]):
    """Create a new non-versioned entity."""

    def __init__(self, entity_class: type[TSimple], **fields: Any) -> None:
        self.entity_class = entity_class
        self.fields = fields

    async def execute(self, session: AsyncSession) -> TSimple:
        """Create and persist the entity."""
        entity = self.entity_class(**self.fields)
        session.add(entity)
        await session.flush()
        return entity


class SimpleUpdateCommand(SimpleCommandABC[TSimple]):
    """Update a non-versioned entity in place."""

    def __init__(
        self, entity_class: type[TSimple], entity_id: UUID, **updates: Any
    ) -> None:
        self.entity_class = entity_class
        self.entity_id = entity_id
        self.updates = updates

    async def execute(self, session: AsyncSession) -> TSimple:
        """Update the entity and return it, or raise if not found."""
        entity = await session.get(self.entity_class, self.entity_id)
        if not entity:
            raise ValueError(f"Entity {self.entity_id} not found")
        for key, value in self.updates.items():
            setattr(entity, key, value)
        await session.flush()
        return entity


class SimpleDeleteCommand(SimpleCommandABC[TSimple]):
    """Hard delete a non-versioned entity."""

    def __init__(self, entity_class: type[TSimple], entity_id: UUID) -> None:
        self.entity_class = entity_class
        self.entity_id = entity_id

    async def execute(self, session: AsyncSession) -> bool:
        """Delete the entity and return True if found, False otherwise."""
        entity = await session.get(self.entity_class, self.entity_id)
        if entity:
            await session.delete(entity)
            await session.flush()
            return True
        return False
