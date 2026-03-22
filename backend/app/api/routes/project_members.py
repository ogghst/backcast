"""Project Member API routes with RBAC.

Provides endpoints for managing project-level role assignments.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import ProjectRoleChecker
from app.db.session import get_db
from app.models.domain.user import User
from app.models.schemas.project_member import (
    ProjectMemberCreate,
    ProjectMemberPublic,
    ProjectMemberUpdate,
)
from app.services.project_member import ProjectMemberService

router = APIRouter()


def get_project_member_service(
    session: AsyncSession = Depends(get_db),
) -> ProjectMemberService:
    """Get ProjectMemberService instance."""
    return ProjectMemberService(session)


@router.get(
    "/projects/{project_id}/members",
    response_model=list[ProjectMemberPublic],
    operation_id="get_project_members",
)
async def list_project_members(
    project_id: UUID,
    current_user: User = Depends(
        ProjectRoleChecker(required_permission="project-read")
    ),
    service: ProjectMemberService = Depends(get_project_member_service),
) -> list[ProjectMemberPublic]:
    """List all members of a project.

    Requires project-read permission for the project.
    """
    members = await service.list_by_project_with_details(project_id=project_id)
    return [ProjectMemberPublic.model_validate(m) for m in members]


@router.post(
    "/projects/{project_id}/members",
    response_model=ProjectMemberPublic,
    status_code=status.HTTP_201_CREATED,
    operation_id="add_project_member",
)
async def add_project_member(
    project_id: UUID,
    member_in: ProjectMemberCreate,
    current_user: User = Depends(
        ProjectRoleChecker(required_permission="project-admin")
    ),
    service: ProjectMemberService = Depends(get_project_member_service),
) -> ProjectMemberPublic:
    """Add a member to a project.

    Requires project-admin permission for the project.
    """
    # Validate project_id matches
    if member_in.project_id != project_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="project_id in path must match project_id in body",
        )

    # Check if user is already a member
    existing = await service.get_by_user_and_project(
        user_id=member_in.user_id, project_id=project_id
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is already a member of this project",
        )

    # Set the assigner to current user
    member_in.assigned_by = current_user.user_id

    try:
        member = await service.create(**member_in.model_dump())
        return ProjectMemberPublic.model_validate(member)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e


@router.delete(
    "/projects/{project_id}/members/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    operation_id="remove_project_member",
)
async def remove_project_member(
    project_id: UUID,
    user_id: UUID,
    current_user: User = Depends(
        ProjectRoleChecker(required_permission="project-admin")
    ),
    service: ProjectMemberService = Depends(get_project_member_service),
) -> None:
    """Remove a member from a project.

    Requires project-admin permission for the project.
    """
    # Find the membership record
    member = await service.get_by_user_and_project(
        user_id=user_id, project_id=project_id
    )

    if not member:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User is not a member of this project",
        )

    await service.delete(entity_id=member.id)


@router.patch(
    "/projects/{project_id}/members/{user_id}",
    response_model=ProjectMemberPublic,
    operation_id="update_project_member_role",
)
async def update_project_member_role(
    project_id: UUID,
    user_id: UUID,
    member_update: ProjectMemberUpdate,
    current_user: User = Depends(
        ProjectRoleChecker(required_permission="project-admin")
    ),
    service: ProjectMemberService = Depends(get_project_member_service),
) -> ProjectMemberPublic:
    """Update a project member's role.

    Requires project-admin permission for the project.
    """
    # Find the membership record
    member = await service.get_by_user_and_project(
        user_id=user_id, project_id=project_id
    )

    if not member:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User is not a member of this project",
        )

    # Set the assigner to current user
    member_update.assigned_by = current_user.user_id

    try:
        updated_member = await service.update(
            entity_id=member.id, **member_update.model_dump()
        )
        return ProjectMemberPublic.model_validate(updated_member)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e
