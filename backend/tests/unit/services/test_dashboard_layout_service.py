"""Unit tests for DashboardLayoutService.

Tests all service methods: get, get_for_user_project, get_default_for_user_project,
get_templates, create, update, delete, clone_template, and seed_templates.
"""

from uuid import UUID, uuid4

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.dashboard_layout_service import DashboardLayoutService


# ---------------------------------------------------------------------------
# Fixture
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture
async def service(db_session: AsyncSession) -> DashboardLayoutService:
    """Provide a DashboardLayoutService bound to the test session."""
    return DashboardLayoutService(db_session)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _widget_payload() -> list[dict[str, object]]:
    """Return a minimal widget configuration for testing."""
    return [{"typeId": "budget-status", "config": {"entityType": "project"}}]


# ---------------------------------------------------------------------------
# get
# ---------------------------------------------------------------------------


class TestGet:
    """Tests for DashboardLayoutService.get."""

    @pytest.mark.asyncio
    async def test_returns_layout_when_exists(
        self, service: DashboardLayoutService
    ) -> None:
        """get returns the layout matching the given ID."""
        layout = await service.create(
            user_id=uuid4(), name="Findable", widgets=_widget_payload()
        )

        result = await service.get(layout.id)
        assert result is not None
        assert result.id == layout.id
        assert result.name == "Findable"

    @pytest.mark.asyncio
    async def test_returns_none_for_unknown_id(
        self, service: DashboardLayoutService
    ) -> None:
        """get returns None when no layout matches."""
        result = await service.get(uuid4())
        assert result is None


# ---------------------------------------------------------------------------
# get_for_user_project
# ---------------------------------------------------------------------------


class TestGetForUserProject:
    """Tests for DashboardLayoutService.get_for_user_project."""

    @pytest.mark.asyncio
    async def test_returns_empty_when_user_has_no_layouts(
        self, service: DashboardLayoutService
    ) -> None:
        """Returns an empty list for a user with no layouts."""
        result = await service.get_for_user_project(uuid4())
        assert result == []

    @pytest.mark.asyncio
    async def test_returns_only_users_non_template_layouts(
        self, service: DashboardLayoutService
    ) -> None:
        """Excludes other users' layouts and template layouts."""
        user_a = uuid4()
        user_b = uuid4()

        await service.create(user_id=user_a, name="User A Layout")
        await service.create(
            user_id=user_a, name="User A Template", is_template=True
        )
        await service.create(user_id=user_b, name="User B Layout")

        result = await service.get_for_user_project(user_a)
        assert len(result) == 1
        assert result[0].name == "User A Layout"

    @pytest.mark.asyncio
    async def test_global_scope_returns_only_null_project_id(
        self, service: DashboardLayoutService
    ) -> None:
        """Without project_id, returns only layouts with project_id IS NULL."""
        user_id = uuid4()
        project_id = uuid4()

        await service.create(user_id=user_id, name="Global Layout")
        await service.create(
            user_id=user_id, name="Project Layout", project_id=project_id
        )

        result = await service.get_for_user_project(user_id)
        assert len(result) == 1
        assert result[0].name == "Global Layout"

    @pytest.mark.asyncio
    async def test_project_scope_returns_matching_and_global(
        self, service: DashboardLayoutService
    ) -> None:
        """With project_id, returns project-scoped and global layouts."""
        user_id = uuid4()
        project_id = uuid4()
        other_project_id = uuid4()

        await service.create(user_id=user_id, name="Global")
        await service.create(
            user_id=user_id, name="Project A", project_id=project_id
        )
        await service.create(
            user_id=user_id, name="Project B", project_id=other_project_id
        )

        result = await service.get_for_user_project(user_id, project_id)
        names = {layout.name for layout in result}
        assert names == {"Global", "Project A"}

    @pytest.mark.asyncio
    async def test_results_ordered_by_default_desc_then_name(
        self, service: DashboardLayoutService
    ) -> None:
        """Default layouts come first, then sorted alphabetically by name."""
        user_id = uuid4()

        await service.create(user_id=user_id, name="Bravo")
        await service.create(user_id=user_id, name="Alpha", is_default=True)
        await service.create(user_id=user_id, name="Charlie")

        result = await service.get_for_user_project(user_id)
        assert result[0].name == "Alpha"
        assert result[0].is_default is True
        assert result[1].name == "Bravo"
        assert result[2].name == "Charlie"


# ---------------------------------------------------------------------------
# get_default_for_user_project
# ---------------------------------------------------------------------------


class TestGetDefaultForUserProject:
    """Tests for DashboardLayoutService.get_default_for_user_project."""

    @pytest.mark.asyncio
    async def test_returns_none_when_no_default_exists(
        self, service: DashboardLayoutService
    ) -> None:
        """Returns None if the user has no default layout for the project."""
        user_id = uuid4()
        project_id = uuid4()
        await service.create(
            user_id=user_id, name="Not Default", project_id=project_id
        )

        result = await service.get_default_for_user_project(user_id, project_id)
        assert result is None

    @pytest.mark.asyncio
    async def test_returns_default_layout(
        self, service: DashboardLayoutService
    ) -> None:
        """Returns the layout marked as default for the user/project."""
        user_id = uuid4()
        project_id = uuid4()

        await service.create(
            user_id=user_id, name="Regular", project_id=project_id
        )
        default_layout = await service.create(
            user_id=user_id,
            name="Default",
            project_id=project_id,
            is_default=True,
        )

        result = await service.get_default_for_user_project(user_id, project_id)
        assert result is not None
        assert result.id == default_layout.id
        assert result.is_default is True

    @pytest.mark.asyncio
    async def test_excludes_templates_from_default(
        self, service: DashboardLayoutService
    ) -> None:
        """A template layout is not returned even if is_default=True."""
        user_id = uuid4()
        project_id = uuid4()
        await service.create(
            user_id=user_id,
            name="Template Default",
            project_id=project_id,
            is_template=True,
            is_default=True,
        )

        result = await service.get_default_for_user_project(user_id, project_id)
        assert result is None

    @pytest.mark.asyncio
    async def test_scoped_to_correct_project(
        self, service: DashboardLayoutService
    ) -> None:
        """Does not return a default from a different project."""
        user_id = uuid4()
        project_a = uuid4()
        project_b = uuid4()

        await service.create(
            user_id=user_id,
            name="Default A",
            project_id=project_a,
            is_default=True,
        )
        await service.create(
            user_id=user_id,
            name="Default B",
            project_id=project_b,
            is_default=True,
        )

        result = await service.get_default_for_user_project(user_id, project_a)
        assert result is not None
        assert result.name == "Default A"


# ---------------------------------------------------------------------------
# get_templates
# ---------------------------------------------------------------------------


class TestGetTemplates:
    """Tests for DashboardLayoutService.get_templates."""

    @pytest.mark.asyncio
    async def test_returns_empty_when_no_templates(
        self, service: DashboardLayoutService
    ) -> None:
        """Returns an empty list when no template layouts exist."""
        assert await service.get_templates() == []

    @pytest.mark.asyncio
    async def test_returns_only_template_layouts(
        self, service: DashboardLayoutService
    ) -> None:
        """Returns layouts with is_template=True only."""
        user_id = uuid4()
        await service.create(user_id=user_id, name="Regular")
        await service.create(
            user_id=user_id, name="Template A", is_template=True
        )
        await service.create(
            user_id=user_id, name="Template B", is_template=True
        )

        result = await service.get_templates()
        assert len(result) == 2
        names = {layout.name for layout in result}
        assert names == {"Template A", "Template B"}

    @pytest.mark.asyncio
    async def test_templates_ordered_by_name(
        self, service: DashboardLayoutService
    ) -> None:
        """Templates are returned ordered alphabetically by name."""
        user_id = uuid4()
        await service.create(
            user_id=user_id, name="Zebra Template", is_template=True
        )
        await service.create(
            user_id=user_id, name="Alpha Template", is_template=True
        )

        result = await service.get_templates()
        assert result[0].name == "Alpha Template"
        assert result[1].name == "Zebra Template"


# ---------------------------------------------------------------------------
# create
# ---------------------------------------------------------------------------


class TestCreate:
    """Tests for DashboardLayoutService.create."""

    @pytest.mark.asyncio
    async def test_creates_layout_with_required_fields(
        self, service: DashboardLayoutService
    ) -> None:
        """Creates a layout with user_id and name."""
        user_id = uuid4()
        layout = await service.create(user_id=user_id, name="My Layout")

        assert layout.id is not None
        assert isinstance(layout.id, UUID)
        assert layout.user_id == user_id
        assert layout.name == "My Layout"
        assert layout.is_template is False
        assert layout.is_default is False
        assert layout.widgets == []

    @pytest.mark.asyncio
    async def test_creates_with_all_optional_fields(
        self, service: DashboardLayoutService
    ) -> None:
        """Creates a layout with description, project_id, and widgets."""
        user_id = uuid4()
        project_id = uuid4()
        widgets = _widget_payload()

        layout = await service.create(
            user_id=user_id,
            name="Full Layout",
            description="A complete layout",
            project_id=project_id,
            widgets=widgets,
        )

        assert layout.description == "A complete layout"
        assert layout.project_id == project_id
        assert layout.widgets == widgets

    @pytest.mark.asyncio
    async def test_create_default_clears_existing_default(
        self, service: DashboardLayoutService
    ) -> None:
        """Creating a default clears the previous default in the same scope."""
        user_id = uuid4()
        project_id = uuid4()

        old_default = await service.create(
            user_id=user_id,
            name="Old Default",
            project_id=project_id,
            is_default=True,
        )
        new_default = await service.create(
            user_id=user_id,
            name="New Default",
            project_id=project_id,
            is_default=True,
        )

        # Refresh old_default from the session to see the updated value
        await service.session.flush()
        await service.session.refresh(old_default)

        assert old_default.is_default is False
        assert new_default.is_default is True

    @pytest.mark.asyncio
    async def test_create_default_in_different_project_does_not_clear(
        self, service: DashboardLayoutService
    ) -> None:
        """Setting default in one project does not affect another project's default."""
        user_id = uuid4()
        project_a = uuid4()
        project_b = uuid4()

        default_a = await service.create(
            user_id=user_id,
            name="Default A",
            project_id=project_a,
            is_default=True,
        )
        await service.create(
            user_id=user_id,
            name="Default B",
            project_id=project_b,
            is_default=True,
        )

        await service.session.flush()
        await service.session.refresh(default_a)
        assert default_a.is_default is True

    @pytest.mark.asyncio
    async def test_create_default_global_does_not_clear_project_default(
        self, service: DashboardLayoutService
    ) -> None:
        """Setting a global default does not clear a project-scoped default."""
        user_id = uuid4()
        project_id = uuid4()

        project_default = await service.create(
            user_id=user_id,
            name="Project Default",
            project_id=project_id,
            is_default=True,
        )
        await service.create(
            user_id=user_id, name="Global Default", is_default=True
        )

        await service.session.flush()
        await service.session.refresh(project_default)
        assert project_default.is_default is True


# ---------------------------------------------------------------------------
# update
# ---------------------------------------------------------------------------


class TestUpdate:
    """Tests for DashboardLayoutService.update."""

    @pytest.mark.asyncio
    async def test_updates_name(
        self, service: DashboardLayoutService
    ) -> None:
        """Update changes the name field."""
        user_id = uuid4()
        layout = await service.create(user_id=user_id, name="Original")

        updated = await service.update(
            layout.id, user_id, name="Updated"
        )
        assert updated.name == "Updated"

    @pytest.mark.asyncio
    async def test_updates_widgets(
        self, service: DashboardLayoutService
    ) -> None:
        """Update replaces the widgets array."""
        user_id = uuid4()
        layout = await service.create(
            user_id=user_id, name="Widget Layout", widgets=_widget_payload()
        )

        new_widgets: list[dict[str, object]] = [
            {"typeId": "evm-summary"},
            {"typeId": "variance-chart"},
        ]
        updated = await service.update(
            layout.id, user_id, widgets=new_widgets
        )
        assert updated.widgets == new_widgets

    @pytest.mark.asyncio
    async def test_raises_not_found_for_missing_id(
        self, service: DashboardLayoutService
    ) -> None:
        """Update raises ValueError when the layout does not exist."""
        with pytest.raises(ValueError, match="not found"):
            await service.update(uuid4(), uuid4(), name="X")

    @pytest.mark.asyncio
    async def test_raises_not_authorized_for_wrong_owner(
        self, service: DashboardLayoutService
    ) -> None:
        """Update raises ValueError when the user does not own the layout."""
        owner = uuid4()
        other = uuid4()
        layout = await service.create(user_id=owner, name="Owned")

        with pytest.raises(ValueError, match="Not authorized"):
            await service.update(layout.id, other, name="Hacked")

    @pytest.mark.asyncio
    async def test_raises_for_template_layout(
        self, service: DashboardLayoutService
    ) -> None:
        """Update raises ValueError when trying to update a template."""
        owner = uuid4()
        template = await service.create(
            user_id=owner, name="Template", is_template=True
        )

        with pytest.raises(ValueError, match="Cannot modify a template layout"):
            await service.update(template.id, owner, name="Hacked Template")

    @pytest.mark.asyncio
    async def test_update_default_clears_previous_default(
        self, service: DashboardLayoutService
    ) -> None:
        """Setting is_default via update clears the existing default."""
        user_id = uuid4()
        project_id = uuid4()

        old_default = await service.create(
            user_id=user_id,
            name="Old",
            project_id=project_id,
            is_default=True,
        )
        other_layout = await service.create(
            user_id=user_id,
            name="Other",
            project_id=project_id,
        )

        await service.update(other_layout.id, user_id, is_default=True)

        await service.session.flush()
        await service.session.refresh(old_default)
        assert old_default.is_default is False


# ---------------------------------------------------------------------------
# update_template
# ---------------------------------------------------------------------------


class TestUpdateTemplate:
    """Tests for DashboardLayoutService.update_template (admin-only)."""

    @pytest.mark.asyncio
    async def test_updates_template_name(
        self, service: DashboardLayoutService
    ) -> None:
        """update_template changes fields on a template layout."""
        owner = uuid4()
        template = await service.create(
            user_id=owner, name="Original Template", is_template=True
        )

        updated = await service.update_template(
            template.id, name="Updated Template"
        )
        assert updated.name == "Updated Template"

    @pytest.mark.asyncio
    async def test_updates_template_widgets(
        self, service: DashboardLayoutService
    ) -> None:
        """update_template replaces the widgets array on a template."""
        owner = uuid4()
        template = await service.create(
            user_id=owner, name="T", is_template=True, widgets=_widget_payload()
        )

        new_widgets: list[dict[str, object]] = [
            {"typeId": "evm-summary"},
        ]
        updated = await service.update_template(template.id, widgets=new_widgets)
        assert updated.widgets == new_widgets

    @pytest.mark.asyncio
    async def test_raises_not_found_for_missing_id(
        self, service: DashboardLayoutService
    ) -> None:
        """update_template raises ValueError for a nonexistent ID."""
        with pytest.raises(ValueError, match="not found"):
            await service.update_template(uuid4(), name="X")

    @pytest.mark.asyncio
    async def test_raises_for_non_template(
        self, service: DashboardLayoutService
    ) -> None:
        """update_template raises ValueError when the layout is not a template."""
        owner = uuid4()
        layout = await service.create(user_id=owner, name="Regular")

        with pytest.raises(ValueError, match="not a template"):
            await service.update_template(layout.id, name="X")


# ---------------------------------------------------------------------------
# delete
# ---------------------------------------------------------------------------


class TestDelete:
    """Tests for DashboardLayoutService.delete."""

    @pytest.mark.asyncio
    async def test_deletes_existing_layout(
        self, service: DashboardLayoutService
    ) -> None:
        """Delete returns True and the layout is gone."""
        user_id = uuid4()
        layout = await service.create(user_id=user_id, name="Bye")

        result = await service.delete(layout.id, user_id)
        assert result is True
        assert await service.get(layout.id) is None

    @pytest.mark.asyncio
    async def test_returns_false_for_missing_id(
        self, service: DashboardLayoutService
    ) -> None:
        """Delete returns False when the layout does not exist."""
        result = await service.delete(uuid4(), uuid4())
        assert result is False

    @pytest.mark.asyncio
    async def test_raises_not_authorized_for_wrong_owner(
        self, service: DashboardLayoutService
    ) -> None:
        """Delete raises ValueError when the user does not own the layout."""
        owner = uuid4()
        other = uuid4()
        layout = await service.create(user_id=owner, name="Protected")

        with pytest.raises(ValueError, match="Not authorized"):
            await service.delete(layout.id, other)

    @pytest.mark.asyncio
    async def test_auto_promotes_default_after_delete(
        self, service: DashboardLayoutService
    ) -> None:
        """Deleting the default layout promotes another layout in the same scope."""
        user_id = uuid4()
        project_id = uuid4()

        default_layout = await service.create(
            user_id=user_id,
            name="Default",
            project_id=project_id,
            is_default=True,
        )
        await service.create(
            user_id=user_id,
            name="Backup",
            project_id=project_id,
        )

        await service.delete(default_layout.id, user_id)

        # Check that 'Backup' was auto-promoted
        new_default = await service.get_default_for_user_project(
            user_id, project_id
        )
        assert new_default is not None
        assert new_default.name == "Backup"
        assert new_default.is_default is True

    @pytest.mark.asyncio
    async def test_no_auto_promote_when_non_default_deleted(
        self, service: DashboardLayoutService
    ) -> None:
        """Deleting a non-default layout does not change any defaults."""
        user_id = uuid4()
        project_id = uuid4()

        default_layout = await service.create(
            user_id=user_id,
            name="Default",
            project_id=project_id,
            is_default=True,
        )
        non_default = await service.create(
            user_id=user_id,
            name="Extra",
            project_id=project_id,
        )

        await service.delete(non_default.id, user_id)

        await service.session.flush()
        await service.session.refresh(default_layout)
        assert default_layout.is_default is True


# ---------------------------------------------------------------------------
# clone_template
# ---------------------------------------------------------------------------


class TestCloneTemplate:
    """Tests for DashboardLayoutService.clone_template."""

    @pytest.mark.asyncio
    async def test_clones_template_successfully(
        self, service: DashboardLayoutService
    ) -> None:
        """Clone creates a new non-template layout from the template."""
        owner = uuid4()
        clone_user = uuid4()
        widgets = _widget_payload()

        template = await service.create(
            user_id=owner,
            name="Base Template",
            description="Template desc",
            is_template=True,
            widgets=widgets,
        )

        cloned = await service.clone_template(template.id, clone_user)

        assert cloned.id != template.id
        assert cloned.name == "Copy of Base Template"
        assert cloned.description == "Template desc"
        assert cloned.user_id == clone_user
        assert cloned.project_id is None
        assert cloned.is_template is False
        assert cloned.is_default is False
        assert cloned.widgets == widgets

    @pytest.mark.asyncio
    async def test_clone_with_project_id(
        self, service: DashboardLayoutService
    ) -> None:
        """Clone accepts an optional project_id."""
        user_id = uuid4()
        project_id = uuid4()

        template = await service.create(
            user_id=user_id, name="T", is_template=True
        )
        cloned = await service.clone_template(template.id, user_id, project_id)

        assert cloned.project_id == project_id

    @pytest.mark.asyncio
    async def test_raises_for_non_template(
        self, service: DashboardLayoutService
    ) -> None:
        """Clone raises ValueError if the source is not a template."""
        user_id = uuid4()
        layout = await service.create(user_id=user_id, name="Not Template")

        with pytest.raises(ValueError, match="Not a template layout"):
            await service.clone_template(layout.id, uuid4())

    @pytest.mark.asyncio
    async def test_raises_for_nonexistent_id(
        self, service: DashboardLayoutService
    ) -> None:
        """Clone raises ValueError if the ID does not exist."""
        with pytest.raises(ValueError, match="Not a template layout"):
            await service.clone_template(uuid4(), uuid4())


# ---------------------------------------------------------------------------
# seed_templates
# ---------------------------------------------------------------------------


class TestSeedTemplates:
    """Tests for DashboardLayoutService.seed_templates."""

    @pytest.mark.asyncio
    async def test_seeds_all_templates_on_first_run(
        self, service: DashboardLayoutService
    ) -> None:
        """Seed creates all predefined templates when none exist."""
        system_user = uuid4()
        created = await service.seed_templates(system_user)

        assert created >= 3  # Project Overview, EVM Analysis, Cost Controller

        templates = await service.get_templates()
        template_names = {t.name for t in templates}
        assert "Project Overview" in template_names
        assert "EVM Analysis" in template_names
        assert "Cost Controller" in template_names

    @pytest.mark.asyncio
    async def test_seeded_templates_belong_to_system_user(
        self, service: DashboardLayoutService
    ) -> None:
        """Seeded templates are owned by the given system user."""
        system_user = uuid4()
        await service.seed_templates(system_user)

        templates = await service.get_templates()
        for template in templates:
            assert template.user_id == system_user

    @pytest.mark.asyncio
    async def test_seeded_templates_have_is_template_true(
        self, service: DashboardLayoutService
    ) -> None:
        """All seeded templates have is_template=True."""
        await service.seed_templates(uuid4())

        templates = await service.get_templates()
        for template in templates:
            assert template.is_template is True

    @pytest.mark.asyncio
    async def test_idempotent_seeding(
        self, service: DashboardLayoutService
    ) -> None:
        """Calling seed twice does not create duplicates."""
        system_user = uuid4()
        first_count = await service.seed_templates(system_user)
        second_count = await service.seed_templates(system_user)

        assert second_count == 0

        templates = await service.get_templates()
        assert len(templates) == first_count

    @pytest.mark.asyncio
    async def test_seeded_templates_contain_widgets(
        self, service: DashboardLayoutService
    ) -> None:
        """Each seeded template has a non-empty widgets array."""
        await service.seed_templates(uuid4())

        templates = await service.get_templates()
        for template in templates:
            assert len(template.widgets) > 0

    @pytest.mark.asyncio
    async def test_seeded_templates_have_descriptions(
        self, service: DashboardLayoutService
    ) -> None:
        """Each seeded template has a non-empty description."""
        await service.seed_templates(uuid4())

        templates = await service.get_templates()
        for template in templates:
            assert template.description is not None
            assert len(template.description) > 0
