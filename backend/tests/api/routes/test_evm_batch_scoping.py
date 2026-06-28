"""G2: EVM /batch route membership scoping test.

The POST /evm/batch route filters ``entity_ids`` to the caller's accessible
projects when ``entity_type == PROJECT`` (mirrors the projects.py RBAC pattern).
This test validates the membership-scoping mechanism directly against the
unified RBAC service, because the default ``client`` fixture authenticates as
the global admin user (which sees all projects — so the filter would be a
no-op and cannot demonstrate scoping end-to-end).

What is validated:
- A user with NO roles and NO project-scoped assignment gets an empty
  accessible-projects list (so the batch filter drops every requested id).
- A user with a project-scoped role assignment gets exactly that project back
  (so the batch filter keeps it and drops the others).
"""

from uuid import UUID, uuid4

import pytest
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.rbac_unified import (
    get_unified_rbac_service,
    set_unified_rbac_session,
)
from app.models.domain.user import User
from app.models.domain.user_role_assignment import UserRoleAssignment
from tests.factories import create_full_hierarchy


@pytest.mark.asyncio
async def test_non_member_user_has_no_accessible_projects(
    db: AsyncSession,
) -> None:
    """A role-less user gets an empty accessible-projects list.

    The G2 batch filter intersects entity_ids with this list, so a non-member
    user's requested project ids are all dropped (cannot read EVM for projects
    they do not belong to).
    """
    # Create a fresh user with NO global role and NO project-scoped assignment.
    lone_user_id = uuid4()
    db.add(
        User(
            id=lone_user_id,
            user_id=lone_user_id,
            email=f"lone-{lone_user_id}@backcast.test",
            hashed_password="x",
            full_name="Lone Nonmember",
            is_active=True,
            created_by=lone_user_id,
        )
    )
    await db.flush()
    try:
        set_unified_rbac_session(db)
        service = get_unified_rbac_service()
        accessible = await service.get_accessible_projects(user_id=lone_user_id)
        set_unified_rbac_session(None)
        assert accessible == []
    finally:
        # Cleanup the persistent row (db fixture commits; see memory note 35).
        await db.execute(delete(User).where(User.user_id == lone_user_id))
        await db.flush()


@pytest.mark.asyncio
async def test_project_scoped_member_is_accessible(
    db: AsyncSession,
    actor_id: UUID,
) -> None:
    """A user with a project-scoped assignment gets that project back only.

    Mirrors the positive side of G2: the batch filter keeps a project id iff the
    caller has a project-scoped role for it.
    """
    h = await create_full_hierarchy(db, actor_id)
    project_id = h["project"].project_id
    await db.commit()

    member_user_id = uuid4()
    db.add(
        User(
            id=member_user_id,
            user_id=member_user_id,
            email=f"member-{member_user_id}@backcast.test",
            hashed_password="x",
            full_name="Project Member",
            is_active=True,
            created_by=member_user_id,
        )
    )
    await db.flush()

    # Grant a project-scoped role (reuse the seeded 'viewer' role id).
    from app.models.domain.rbac import RBACRole
    from app.models.domain.user_role_assignment import ScopeType

    role_id = (
        await db.execute(select(RBACRole.id).where(RBACRole.name == "viewer"))
    ).scalar_one()
    assignment_id = uuid4()
    db.add(
        UserRoleAssignment(
            id=assignment_id,
            user_id=member_user_id,
            role_id=role_id,
            scope_type=ScopeType.PROJECT.value,
            scope_id=project_id,
            granted_by=actor_id,
        )
    )
    await db.flush()

    try:
        set_unified_rbac_session(db)
        service = get_unified_rbac_service()
        accessible = await service.get_accessible_projects(user_id=member_user_id)
        set_unified_rbac_session(None)
        # Exactly the member's project is accessible (not others).
        assert project_id in accessible
    finally:
        await db.execute(
            delete(UserRoleAssignment).where(UserRoleAssignment.id == assignment_id)
        )
        await db.execute(delete(User).where(User.user_id == member_user_id))
        await db.flush()
