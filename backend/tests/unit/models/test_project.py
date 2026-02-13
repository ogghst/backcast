from uuid import uuid4

from app.models.domain.project import Project


class TestProjectModel:
    """Test Project model behavior and Mixin composition."""

    def test_project_initialization(self):
        """Test basic initialization and mixin defaults."""
        root_id = uuid4()
        project = Project(
            project_id=root_id, name="Test Project", budget=1000.00, branch="main"
        )

        assert project.project_id == root_id
        assert project.name == "Test Project"
        assert project.branch == "main"  # Default from BranchableMixin
        assert project.parent_id is None
        assert project.merge_from_branch is None
        assert project.deleted_at is None

    def test_project_clone(self):
        """Test cloning behavior from BranchableMixin."""
        root_id = uuid4()
        original = Project(project_id=root_id, name="Original", branch="main")

        # Simulate saved state
        original.id = uuid4()

        # Clone
        cloned = original.clone(branch="feature/new", name="Cloned")

        assert cloned.project_id == root_id
        assert cloned.branch == "feature/new"
        assert cloned.name == "Cloned"
        assert (
            cloned.id != original.id
        )  # Should stay None until saved or new ID generated
        # Note: clone() pops ID, so it relies on DB or default factory to generate new one on insert
