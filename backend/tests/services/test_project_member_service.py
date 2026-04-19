"""Tests for ProjectMemberService.

Uses pytest-asyncio for async test handling.
"""

from datetime import datetime
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.enums import ProjectRole
from app.services.project_member import ProjectMemberService


@pytest.mark.asyncio
async def test_create_project_member(db_session: AsyncSession) -> None:
    """Test creating a new project member assignment."""
    service = ProjectMemberService(db_session)

    user_id = uuid4()
    project_id = uuid4()
    assigned_by = uuid4()

    member = await service.create(
        user_id=user_id,
        project_id=project_id,
        role=ProjectRole.PROJECT_VIEWER.value,
        assigned_at=datetime.now(),
        assigned_by=assigned_by,
    )

    assert member is not None
    assert member.id is not None
    assert member.user_id == user_id
    assert member.project_id == project_id
    assert member.role == ProjectRole.PROJECT_VIEWER.value
    assert member.assigned_by == assigned_by
    assert member.created_at is not None
    assert member.updated_at is not None


@pytest.mark.asyncio
async def test_get_by_user_and_project(db_session: AsyncSession) -> None:
    """Test retrieving a project member by user_id and project_id."""
    service = ProjectMemberService(db_session)

    user_id = uuid4()
    project_id = uuid4()
    assigned_by = uuid4()

    # Create a member
    created = await service.create(
        user_id=user_id,
        project_id=project_id,
        role=ProjectRole.PROJECT_ADMIN.value,
        assigned_at=datetime.now(),
        assigned_by=assigned_by,
    )

    # Retrieve by user and project
    retrieved = await service.get_by_user_and_project(user_id, project_id)

    assert retrieved is not None
    assert retrieved.id == created.id
    assert retrieved.user_id == user_id
    assert retrieved.project_id == project_id
    assert retrieved.role == ProjectRole.PROJECT_ADMIN.value


@pytest.mark.asyncio
async def test_get_by_user_and_project_not_found(db_session: AsyncSession) -> None:
    """Test retrieving a non-existent project member."""
    service = ProjectMemberService(db_session)

    result = await service.get_by_user_and_project(uuid4(), uuid4())

    assert result is None


@pytest.mark.asyncio
async def test_list_by_project(db_session: AsyncSession) -> None:
    """Test listing all members of a project."""
    service = ProjectMemberService(db_session)

    project_id = uuid4()
    assigned_by = uuid4()

    # Create multiple members for the same project
    member1 = await service.create(
        user_id=uuid4(),
        project_id=project_id,
        role=ProjectRole.PROJECT_ADMIN.value,
        assigned_at=datetime.now(),
        assigned_by=assigned_by,
    )
    member2 = await service.create(
        user_id=uuid4(),
        project_id=project_id,
        role=ProjectRole.PROJECT_VIEWER.value,
        assigned_at=datetime.now(),
        assigned_by=assigned_by,
    )

    # List members
    members = await service.list_by_project(project_id)

    assert len(members) == 2
    member_ids = {m.id for m in members}
    assert member1.id in member_ids
    assert member2.id in member_ids


@pytest.mark.asyncio
async def test_list_by_user(db_session: AsyncSession) -> None:
    """Test listing all projects a user is a member of."""
    service = ProjectMemberService(db_session)

    user_id = uuid4()
    assigned_by = uuid4()

    # Create memberships for multiple projects
    member1 = await service.create(
        user_id=user_id,
        project_id=uuid4(),
        role=ProjectRole.PROJECT_MANAGER.value,
        assigned_at=datetime.now(),
        assigned_by=assigned_by,
    )
    member2 = await service.create(
        user_id=user_id,
        project_id=uuid4(),
        role=ProjectRole.PROJECT_EDITOR.value,
        assigned_at=datetime.now(),
        assigned_by=assigned_by,
    )

    # List memberships
    memberships = await service.list_by_user(user_id)

    assert len(memberships) == 2
    membership_ids = {m.id for m in memberships}
    assert member1.id in membership_ids
    assert member2.id in membership_ids


@pytest.mark.asyncio
async def test_update_project_member_role(db_session: AsyncSession) -> None:
    """Test updating a project member's role."""
    service = ProjectMemberService(db_session)

    user_id = uuid4()
    project_id = uuid4()
    assigned_by = uuid4()

    # Create member
    member = await service.create(
        user_id=user_id,
        project_id=project_id,
        role=ProjectRole.PROJECT_VIEWER.value,
        assigned_at=datetime.now(),
        assigned_by=assigned_by,
    )

    # Update role
    updated_member = await service.update(
        entity_id=member.id,
        role=ProjectRole.PROJECT_ADMIN.value,
        assigned_by=assigned_by,
    )

    assert updated_member.role == ProjectRole.PROJECT_ADMIN.value
    assert updated_member.id == member.id


@pytest.mark.asyncio
async def test_remove_member(db_session: AsyncSession) -> None:
    """Test removing a project member."""
    service = ProjectMemberService(db_session)

    user_id = uuid4()
    project_id = uuid4()
    assigned_by = uuid4()

    # Create member
    member = await service.create(
        user_id=user_id,
        project_id=project_id,
        role=ProjectRole.PROJECT_VIEWER.value,
        assigned_at=datetime.now(),
        assigned_by=assigned_by,
    )

    # Remove member
    result = await service.remove_member(member.id)
    assert result is True

    # Verify removal
    retrieved = await service.get_by_user_and_project(user_id, project_id)
    assert retrieved is None


@pytest.mark.asyncio
async def test_remove_nonexistent_member(db_session: AsyncSession) -> None:
    """Test removing a non-existent project member."""
    service = ProjectMemberService(db_session)

    result = await service.remove_member(uuid4())
    assert result is False


@pytest.mark.asyncio
async def test_check_membership_true(db_session: AsyncSession) -> None:
    """Test checking if user is a member of project (positive case)."""
    service = ProjectMemberService(db_session)

    user_id = uuid4()
    project_id = uuid4()
    assigned_by = uuid4()

    # Create membership
    await service.create(
        user_id=user_id,
        project_id=project_id,
        role=ProjectRole.PROJECT_EDITOR.value,
        assigned_at=datetime.now(),
        assigned_by=assigned_by,
    )

    # Check membership
    member = await service.check_membership(user_id, project_id)

    assert member is not None
    assert member.user_id == user_id
    assert member.project_id == project_id


@pytest.mark.asyncio
async def test_check_membership_false(db_session: AsyncSession) -> None:
    """Test checking if user is a member of project (negative case)."""
    service = ProjectMemberService(db_session)

    member = await service.check_membership(uuid4(), uuid4())

    assert member is None


@pytest.mark.asyncio
async def test_unique_constraint_per_user_per_project(db_session: AsyncSession) -> None:
    """Test that a user can only have one role per project."""
    service = ProjectMemberService(db_session)

    user_id = uuid4()
    project_id = uuid4()
    assigned_by = uuid4()

    # Create first membership
    await service.create(
        user_id=user_id,
        project_id=project_id,
        role=ProjectRole.PROJECT_VIEWER.value,
        assigned_at=datetime.now(),
        assigned_by=assigned_by,
    )

    # Attempt to create second membership for same user/project
    # This should violate the unique constraint at database level
    from sqlalchemy.exc import IntegrityError

    with pytest.raises(IntegrityError):
        await service.create(
            user_id=user_id,
            project_id=project_id,
            role=ProjectRole.PROJECT_ADMIN.value,
            assigned_at=datetime.now(),
            assigned_by=assigned_by,
        )


@pytest.mark.asyncio
async def test_pagination_list_by_project(db_session: AsyncSession) -> None:
    """Test pagination when listing project members."""
    service = ProjectMemberService(db_session)

    project_id = uuid4()
    assigned_by = uuid4()

    # Create 5 members
    for _ in range(5):
        await service.create(
            user_id=uuid4(),
            project_id=project_id,
            role=ProjectRole.PROJECT_VIEWER.value,
            assigned_at=datetime.now(),
            assigned_by=assigned_by,
        )

    # Test pagination
    page1 = await service.list_by_project(project_id, skip=0, limit=2)
    page2 = await service.list_by_project(project_id, skip=2, limit=2)
    page3 = await service.list_by_project(project_id, skip=4, limit=2)

    assert len(page1) == 2
    assert len(page2) == 2
    assert len(page3) == 1

    # Verify no duplicates
    all_ids = [m.id for m in page1 + page2 + page3]
    assert len(all_ids) == len(set(all_ids))


@pytest.mark.asyncio
async def test_get_by_id(db_session: AsyncSession) -> None:
    """Test retrieving a project member by ID."""
    service = ProjectMemberService(db_session)

    user_id = uuid4()
    project_id = uuid4()
    assigned_by = uuid4()

    created = await service.create(
        user_id=user_id,
        project_id=project_id,
        role=ProjectRole.PROJECT_MANAGER.value,
        assigned_at=datetime.now(),
        assigned_by=assigned_by,
    )

    retrieved = await service.get(created.id)

    assert retrieved is not None
    assert retrieved.id == created.id
    assert retrieved.user_id == user_id
    assert retrieved.project_id == project_id
