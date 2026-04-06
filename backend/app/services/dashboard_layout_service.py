"""DashboardLayout service - handles user dashboard configurations.

Provides CRUD and utility operations for managing per-user dashboard
layouts, including templates, defaults, and project-scoped configurations.
"""

from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.domain.dashboard_layout import DashboardLayout


class DashboardLayoutService:
    """Service for managing dashboard layout configurations.

    Provides CRUD operations with user ownership validation, default
    layout management, and template cloning.
    """

    def __init__(self, session: AsyncSession) -> None:
        """Initialize the service.

        Args:
            session: Async database session
        """
        self.session = session

    async def get(self, entity_id: UUID) -> DashboardLayout | None:
        """Get layout by ID.

        Args:
            entity_id: UUID of the dashboard layout

        Returns:
            DashboardLayout if found, None otherwise
        """
        return await self.session.get(DashboardLayout, entity_id)

    async def get_for_user_project(
        self, user_id: UUID, project_id: UUID | None = None
    ) -> list[DashboardLayout]:
        """Get user's non-template layouts for a specific project scope.

        When project_id is provided, returns layouts scoped to that project
        plus global layouts (project_id IS NULL). When project_id is None,
        returns only global layouts.

        Args:
            user_id: UUID of the layout owner
            project_id: Optional UUID of the project to scope results

        Returns:
            List of matching DashboardLayout entities ordered by default
            status then name
        """
        stmt = select(DashboardLayout).where(
            DashboardLayout.user_id == user_id,
            DashboardLayout.is_template == False,  # noqa: E712
        )

        if project_id is not None:
            stmt = stmt.where(
                (DashboardLayout.project_id == project_id)
                | (DashboardLayout.project_id.is_(None))
            )
        else:
            stmt = stmt.where(DashboardLayout.project_id.is_(None))

        stmt = stmt.order_by(
            DashboardLayout.is_default.desc(), DashboardLayout.name.asc()
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_default_for_user_project(
        self, user_id: UUID, project_id: UUID
    ) -> DashboardLayout | None:
        """Get the default layout for a user within a project scope.

        Args:
            user_id: UUID of the layout owner
            project_id: UUID of the project

        Returns:
            Default DashboardLayout if found, None otherwise
        """
        stmt = select(DashboardLayout).where(
            DashboardLayout.user_id == user_id,
            DashboardLayout.project_id == project_id,
            DashboardLayout.is_default == True,  # noqa: E712
            DashboardLayout.is_template == False,  # noqa: E712
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_templates(self) -> list[DashboardLayout]:
        """Get all template layouts.

        Returns:
            List of template DashboardLayout entities ordered by name
        """
        stmt = (
            select(DashboardLayout)
            .where(DashboardLayout.is_template == True)  # noqa: E712
            .order_by(DashboardLayout.name.asc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def create(self, user_id: UUID, **fields: object) -> DashboardLayout:
        """Create a new dashboard layout.

        If the new layout is marked as default, clears any existing default
        for the same user/project scope before creating.

        Args:
            user_id: UUID of the layout owner
            **fields: Field values for the new entity

        Returns:
            Created DashboardLayout entity
        """
        if fields.get("is_default"):
            project_id_val: UUID | None = fields.get("project_id")  # type: ignore[assignment]
            await self._clear_default_for_user_project(
                user_id, project_id_val
            )

        layout = DashboardLayout(user_id=user_id, **fields)
        self.session.add(layout)
        await self.session.flush()
        await self.session.refresh(layout)
        return layout

    async def update(
        self, entity_id: UUID, user_id: UUID, **updates: object
    ) -> DashboardLayout:
        """Update a dashboard layout.

        Verifies user ownership before applying updates. If setting
        is_default to True, clears any existing default for the same
        user/project scope.

        Args:
            entity_id: UUID of the dashboard layout
            user_id: UUID of the requesting user (for ownership check)
            **updates: Field values to update

        Returns:
            Updated DashboardLayout entity

        Raises:
            ValueError: If entity not found or user is not authorized
        """
        layout = await self.get(entity_id)
        if layout is None:
            raise ValueError(
                f"DashboardLayout with id {entity_id} not found"
            )
        if layout.user_id != user_id:
            raise ValueError(
                "Not authorized to update this dashboard layout"
            )

        if updates.get("is_default"):
            await self._clear_default_for_user_project(
                user_id, layout.project_id
            )

        for key, value in updates.items():
            setattr(layout, key, value)

        await self.session.flush()
        await self.session.refresh(layout)
        return layout

    async def delete(self, entity_id: UUID, user_id: UUID) -> bool:
        """Delete a dashboard layout.

        Verifies user ownership before deleting. If the deleted layout
        was the default, auto-promotes the most recently updated layout
        in the same scope.

        Args:
            entity_id: UUID of the dashboard layout
            user_id: UUID of the requesting user (for ownership check)

        Returns:
            True if deleted, False if not found

        Raises:
            ValueError: If user is not authorized to delete this layout
        """
        layout = await self.get(entity_id)
        if layout is None:
            return False
        if layout.user_id != user_id:
            raise ValueError(
                "Not authorized to delete this dashboard layout"
            )

        was_default = layout.is_default
        project_id = layout.project_id

        await self.session.delete(layout)
        await self.session.flush()

        if was_default:
            await self._auto_promote_default(user_id, project_id)

        return True

    async def clone_template(
        self,
        template_id: UUID,
        user_id: UUID,
        project_id: UUID | None = None,
    ) -> DashboardLayout:
        """Clone a template layout for a user.

        Creates a new non-template layout by copying the template's
        widget configuration.

        Args:
            template_id: UUID of the template to clone
            user_id: UUID of the new layout owner
            project_id: Optional project scope for the cloned layout

        Returns:
            Newly created DashboardLayout entity

        Raises:
            ValueError: If template not found or entity is not a template
        """
        template = await self.get(template_id)
        if template is None or not template.is_template:
            raise ValueError("Not a template layout")

        layout = DashboardLayout(
            name=f"Copy of {template.name}",
            description=template.description,
            user_id=user_id,
            project_id=project_id,
            is_template=False,
            is_default=False,
            widgets=template.widgets,
        )
        self.session.add(layout)
        await self.session.flush()
        await self.session.refresh(layout)
        return layout

    async def _clear_default_for_user_project(
        self, user_id: UUID, project_id: UUID | None
    ) -> None:
        """Clear the default flag for all layouts in a user/project scope.

        Args:
            user_id: UUID of the layout owner
            project_id: Optional project scope (NULL for global)
        """
        stmt = (
            update(DashboardLayout)
            .where(
                DashboardLayout.user_id == user_id,
                DashboardLayout.is_default == True,  # noqa: E712
                DashboardLayout.project_id == project_id,
            )
            .values(is_default=False)
        )
        await self.session.execute(stmt)
        await self.session.flush()

    async def _auto_promote_default(
        self, user_id: UUID, project_id: UUID | None
    ) -> None:
        """Promote the most recently updated layout to default.

        Finds the most recently updated non-template layout in the same
        user/project scope and sets it as the new default.

        Args:
            user_id: UUID of the layout owner
            project_id: Optional project scope (NULL for global)
        """
        stmt = select(DashboardLayout).where(
            DashboardLayout.user_id == user_id,
            DashboardLayout.is_template == False,  # noqa: E712
        )

        if project_id is not None:
            stmt = stmt.where(
                (DashboardLayout.project_id == project_id)
                | (DashboardLayout.project_id.is_(None))
            )
        else:
            stmt = stmt.where(DashboardLayout.project_id.is_(None))

        stmt = stmt.order_by(DashboardLayout.updated_at.desc()).limit(1)
        result = await self.session.execute(stmt)
        layout = result.scalar_one_or_none()

        if layout is not None:
            layout.is_default = True
            await self.session.flush()

    def __repr__(self) -> str:
        return "<DashboardLayoutService>"
