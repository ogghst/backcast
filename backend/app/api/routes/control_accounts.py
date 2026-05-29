"""Control Account API routes with RBAC and EVCS support."""

from collections.abc import Sequence
from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import RoleChecker, UserIdentity, get_current_user
from app.core.versioning.enums import BranchMode
from app.db.session import get_db
from app.models.domain.control_account import ControlAccount
from app.models.schemas.control_account import (
    ControlAccountCreate,
    ControlAccountPublic,
    ControlAccountUpdate,
)
from app.services.control_account_service import ControlAccountService

router = APIRouter()


def get_control_account_service(
    session: AsyncSession = Depends(get_db),
) -> ControlAccountService:
    return ControlAccountService(session)


@router.get(
    "",
    response_model=None,
    operation_id="get_control_accounts",
    dependencies=[Depends(RoleChecker(required_permission="control-account-read"))],
)
async def read_control_accounts(
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    per_page: int = Query(20, ge=1, description="Items per page"),
    wbs_element_id: UUID | None = Query(
        None, description="Filter by WBS Element root ID"
    ),
    organizational_unit_id: UUID | None = Query(
        None, description="Filter by Organizational Unit root ID"
    ),
    branch: str = Query("main", description="Branch name"),
    branch_mode: BranchMode = Query(
        BranchMode.MERGED,
        description="Branch mode: merged or isolated",
    ),
    search: str | None = Query(None, description="Search term (code, name)"),
    filters: str | None = Query(
        None,
        description="Filters in format 'column:value;column:value1,value2'",
    ),
    sort_field: str | None = Query(None, description="Field to sort by"),
    sort_order: str = Query(
        "asc",
        pattern="^(asc|desc)$",
        description="Sort order (asc or desc)",
    ),
    as_of: datetime | None = Query(
        None,
        description="Time travel: get Control Accounts as of this timestamp (ISO 8601)",
    ),
    service: ControlAccountService = Depends(get_control_account_service),
) -> dict[str, Any]:
    """Retrieve control accounts with server-side search, filtering, and sorting.

    Supports filtering by WBS Element or Organizational Unit for matrix navigation.
    Requires read permission.
    """
    from app.models.schemas.common import PaginatedResponse
    from app.models.schemas.control_account import ControlAccountPublic

    if as_of is None:
        from datetime import UTC

        as_of = datetime.now(tz=UTC)

    legacy_filters: dict[str, Any] = {}
    if wbs_element_id:
        legacy_filters["wbs_element_id"] = wbs_element_id
    if organizational_unit_id:
        legacy_filters["organizational_unit_id"] = organizational_unit_id

    skip = (page - 1) * per_page

    try:
        items, total = await service.get_control_accounts(
            wbs_element_id=wbs_element_id,
            organizational_unit_id=organizational_unit_id,
            branch=branch,
            branch_mode=branch_mode,
            skip=skip,
            limit=per_page,
            as_of=as_of,
        )

        items_out = [ControlAccountPublic.model_validate(i) for i in items]

        response = PaginatedResponse[ControlAccountPublic](
            items=items_out,
            total=total,
            page=page,
            per_page=per_page,
        )

        return response.model_dump()

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e


@router.post(
    "",
    response_model=ControlAccountPublic,
    status_code=status.HTTP_201_CREATED,
    operation_id="create_control_account",
    dependencies=[Depends(RoleChecker(required_permission="control-account-create"))],
)
async def create_control_account(
    ca_in: ControlAccountCreate,
    current_user: UserIdentity = Depends(get_current_user),
    service: ControlAccountService = Depends(get_control_account_service),
) -> ControlAccount:
    """Create a new control account. Requires create permission."""
    try:
        ca_data = ca_in.model_dump(exclude_unset=True)
        root_id = ca_data.pop("control_account_id", None) or uuid4()
        return await service.create_root(
            root_id=root_id,
            actor_id=current_user.user_id,
            **ca_data,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e


@router.get(
    "/{control_account_id}",
    response_model=ControlAccountPublic,
    operation_id="get_control_account",
    dependencies=[Depends(RoleChecker(required_permission="control-account-read"))],
)
async def read_control_account(
    control_account_id: UUID,
    branch: str = Query("main", description="Branch name"),
    branch_mode: BranchMode = Query(
        BranchMode.MERGED,
        description="Branch mode: merged or isolated",
    ),
    as_of: datetime | None = Query(
        None,
        description="Time travel: get control account state as of this timestamp (ISO 8601)",
    ),
    service: ControlAccountService = Depends(get_control_account_service),
) -> ControlAccount:
    """Get a specific control account by root ID. Requires read permission.

    Supports time-travel queries via the as_of parameter.
    """
    if as_of is None:
        from datetime import UTC

        as_of = datetime.now(tz=UTC)

    item = await service.get_as_of(
        entity_id=control_account_id,
        as_of=as_of,
        branch=branch,
        branch_mode=branch_mode,
    )

    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Control Account not found in branch '{branch}'"
            + (f" as of {as_of}" if as_of else ""),
        )
    return item


@router.put(
    "/{control_account_id}",
    response_model=ControlAccountPublic,
    operation_id="update_control_account",
    dependencies=[Depends(RoleChecker(required_permission="control-account-update"))],
)
async def update_control_account(
    control_account_id: UUID,
    ca_in: ControlAccountUpdate,
    current_user: UserIdentity = Depends(get_current_user),
    service: ControlAccountService = Depends(get_control_account_service),
) -> ControlAccount:
    """Update a control account. Requires update permission."""
    try:
        from app.core.branching.commands import UpdateCommand

        update_data = ca_in.model_dump(exclude_unset=True)
        branch = update_data.pop("branch", None) or "main"
        control_date = update_data.pop("control_date", None)
        cmd = UpdateCommand(  # type: ignore[type-var]
            entity_class=ControlAccount,
            root_id=control_account_id,
            actor_id=current_user.user_id,
            branch=branch,
            control_date=control_date,
            updates=update_data,
        )
        return await cmd.execute(service.session)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


@router.delete(
    "/{control_account_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    operation_id="delete_control_account",
    dependencies=[Depends(RoleChecker(required_permission="control-account-delete"))],
)
async def delete_control_account(
    control_account_id: UUID,
    control_date: datetime | None = Query(
        None, description="Optional control date for deletion"
    ),
    current_user: UserIdentity = Depends(get_current_user),
    service: ControlAccountService = Depends(get_control_account_service),
) -> None:
    """Soft delete a control account. Requires delete permission."""
    try:
        await service.soft_delete(
            root_id=control_account_id,
            actor_id=current_user.user_id,
            control_date=control_date,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


@router.get(
    "/{control_account_id}/history",
    response_model=list[ControlAccountPublic],
    operation_id="get_control_account_history",
    dependencies=[Depends(RoleChecker(required_permission="control-account-read"))],
)
async def read_control_account_history(
    control_account_id: UUID,
    service: ControlAccountService = Depends(get_control_account_service),
) -> Sequence[ControlAccount]:
    """Get version history for a control account. Requires read permission."""
    history = await service.get_history(control_account_id)
    if not history:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No history found for this Control Account",
        )
    return history
