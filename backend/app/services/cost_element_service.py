"""Cost Element Service - branchable entity management."""

from uuid import UUID, uuid4
from typing import Any, cast

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.versioning.commands import (
    CreateVersionCommand,
    SoftDeleteCommand,
    UpdateVersionCommand,
)
from app.core.versioning.service import TemporalService
from app.models.domain.cost_element import CostElement
from app.models.schemas.cost_element import CostElementCreate, CostElementUpdate


class CostElementService(TemporalService[CostElement]):  # type: ignore[type-var]
    """Service for Cost Element management (branchable + versionable)."""

    def __init__(self, db: AsyncSession):
        """Initialize service with database session.

        Args:
            db: Async database session
        """
        super().__init__(CostElement, db)

    async def create(
        self,
        element_in: CostElementCreate,
        actor_id: UUID,
        branch: str = "main",
    ) -> CostElement:
        """Create new cost element using CreateVersionCommand."""
        element_data = element_in.model_dump()

        # Ensure root cost_element_id exists
        root_id = uuid4()
        element_data["cost_element_id"] = root_id
        element_data["branch"] = branch

        cmd = CreateVersionCommand(
            entity_class=CostElement,  # type: ignore[type-var]
            root_id=root_id,
            actor_id=actor_id,
            **element_data,
        )
        return await cmd.execute(self.session)

    async def update(
        self,
        cost_element_id: UUID,
        element_in: CostElementUpdate,
        actor_id: UUID,
        branch: str = "main",
    ) -> CostElement:
        """Update cost element using UpdateVersionCommand or Fork if new branch."""
        update_data = element_in.model_dump(exclude_unset=True)
        update_data["branch"] = branch

        # Check if version exists in target branch
        # We need to manage the query manually to avoid TemporalService issues and handle branching
        current = await self.get_by_id(cost_element_id, branch=branch)
        
        if current:
            # Linear update in same branch: Close old, Open new
            
            # Custom command class to handle multi-word entity name AND branch filtering
            class CostElementUpdateCommand(UpdateVersionCommand):  # type: ignore[type-var]
                def __init__(self, entity_class, root_id, actor_id, branch="main", **updates):
                    super().__init__(entity_class, root_id, actor_id, **updates)
                    self.branch = branch

                def _root_field_name(self) -> str:
                    return "cost_element_id"
                
                async def _get_current(self, session: AsyncSession) -> Any | None:
                    stmt = (
                        select(self.entity_class)
                        .where(
                            getattr(self.entity_class, self._root_field_name()) == self.root_id,
                            self.entity_class.branch == self.branch,
                            func.upper(cast(Any, self.entity_class).valid_time).is_(None),
                            cast(Any, self.entity_class).deleted_at.is_(None),
                        )
                        .order_by(cast(Any, self.entity_class).valid_time.desc())
                        .limit(1)
                    )
                    result = await session.execute(stmt)
                    return result.scalar_one_or_none()

            cmd = CostElementUpdateCommand(
                entity_class=CostElement,  # type: ignore[type-var]
                root_id=cost_element_id,
                actor_id=actor_id,
                # Branch is passed via update_data unpacking to match signature
                **update_data,
            )
            return await cmd.execute(self.session)
            
        else:
            # Version not found in target branch -> Fork from main (or parent)
            # This handles "Create Branch" scenario implicitly on update
            
            # Try to find source in 'main' to fork from
            # Note: In a real system we might want to let the caller specify the source branch
            source_version = await self.get_by_id(cost_element_id, branch="main")
            if not source_version:
                 # If not found in main either, we can't update a non-existent entity
                 raise ValueError(f"Cost Element {cost_element_id} not found in {branch} or main.")
            
            # Clone data from source
            data = {c.name: getattr(source_version, c.name) for c in source_version.__table__.columns}
            
            # Remove system/audit fields to let DB/Command handle them
            system_fields = [
                'valid_time', 'transaction_time', 
                'created_by', 'deleted_by', 'deleted_at', 
                'id'  # New version needs new ID
            ]
            for field in system_fields:
                data.pop(field, None)
                
            # Apply updates
            data.update(update_data)
            
            # Set branching metadata
            data['branch'] = branch
            data['parent_id'] = source_version.id  # Link to parent version
            
            # Create new version (Insert only, do not close parent)
            cmd = CreateVersionCommand(
                entity_class=CostElement,  # type: ignore[type-var]
                root_id=cost_element_id,
                actor_id=actor_id,
                **data,
            )
            return await cmd.execute(self.session)

    async def soft_delete(
        self, cost_element_id: UUID, actor_id: UUID, branch: str = "main"
    ) -> None:
        """Soft delete cost element using SoftDeleteCommand."""
        
        # Custom command class
        class CostElementSoftDeleteCommand(SoftDeleteCommand):  # type: ignore[type-var]
            def __init__(self, entity_class, root_id, actor_id, branch="main"):
                super().__init__(entity_class, root_id, actor_id)
                self.branch = branch

            def _root_field_name(self) -> str:
                return "cost_element_id"
            
            async def _get_current(self, session: AsyncSession) -> Any | None:
                """Get current active version filtering by branch."""
                stmt = (
                    select(self.entity_class)
                    .where(
                        getattr(self.entity_class, self._root_field_name()) == self.root_id,
                        self.entity_class.branch == self.branch,
                        func.upper(cast(Any, self.entity_class).valid_time).is_(None),
                        cast(Any, self.entity_class).deleted_at.is_(None),
                    )
                    .order_by(cast(Any, self.entity_class).valid_time.desc())
                    .limit(1)
                )
                result = await session.execute(stmt)
                return result.scalar_one_or_none()

        cmd = CostElementSoftDeleteCommand(
            entity_class=CostElement,  # type: ignore[type-var]
            root_id=cost_element_id,
            actor_id=actor_id,
            branch=branch,
        )
        await cmd.execute(self.session)

    async def get_by_id(
        self, cost_element_id: UUID, branch: str = "main"
    ) -> CostElement | None:
        """Get cost element by root ID and branch."""
        # Manual query to avoid 'costelement_id' inference issue in TemporalService
        stmt = (
            select(CostElement)
            .where(
                CostElement.cost_element_id == cost_element_id,
                CostElement.branch == branch,
                func.upper(cast(Any, CostElement).valid_time).is_(None),
                cast(Any, CostElement).deleted_at.is_(None),
            )
            .order_by(cast(Any, CostElement).valid_time.desc())
            .limit(1)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list(
        self, filters: dict | None = None, branch: str = "main", skip: int = 0, limit: int = 100
    ) -> list[CostElement]:
        """Get all cost elements with optional filtering."""
        
        stmt = (
            select(CostElement)
            .where(
                CostElement.branch == branch,
                func.upper(cast(Any, CostElement).valid_time).is_(None),
                cast(Any, CostElement).deleted_at.is_(None),
            )
        )
        
        if filters:
            if "wbe_id" in filters:
                stmt = stmt.where(CostElement.wbe_id == filters["wbe_id"])
            if "cost_element_type_id" in filters:
                stmt = stmt.where(CostElement.cost_element_type_id == filters["cost_element_type_id"])
                
        stmt = stmt.order_by(CostElement.valid_time.desc()).offset(skip).limit(limit)
        
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
