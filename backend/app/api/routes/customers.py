"""Customer API routes (non-versioned reference data)."""

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import RoleChecker
from app.db.session import get_db
from app.models.schemas.customer import (
    CustomerCreate,
    CustomerRead,
    CustomerUpdate,
)
from app.services.customer_service import CustomerService

router = APIRouter()


def get_customer_service(session: AsyncSession = Depends(get_db)) -> CustomerService:
    """Dependency to get CustomerService instance."""
    return CustomerService(session)


@router.get(
    "",
    response_model=None,  # PaginatedResponse[CustomerRead]
    operation_id="get_customers",
    dependencies=[Depends(RoleChecker(required_permission="customer-read"))],
)
async def read_customers(
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    per_page: int = Query(20, ge=1, description="Items per page"),
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
    service: CustomerService = Depends(get_customer_service),
) -> dict[str, Any]:
    """Retrieve customers with server-side search, filtering, and sorting."""
    from app.models.schemas.common import PaginatedResponse

    skip = (page - 1) * per_page
    items, total = await service.get_customers(
        skip=skip,
        limit=per_page,
        search=search,
        filters=filters,
        sort_field=sort_field,
        sort_order=sort_order,
    )

    items_out = [CustomerRead.model_validate(i) for i in items]
    return PaginatedResponse[CustomerRead](
        items=items_out,
        total=total,
        page=page,
        per_page=per_page,
    ).model_dump()


@router.post(
    "",
    response_model=CustomerRead,
    status_code=status.HTTP_201_CREATED,
    operation_id="create_customer",
    dependencies=[Depends(RoleChecker(required_permission="customer-create"))],
)
async def create_customer(
    customer_in: CustomerCreate,
    service: CustomerService = Depends(get_customer_service),
) -> Any:
    """Create a new customer."""
    return await service.create(customer_in)


@router.get(
    "/{customer_id}",
    response_model=CustomerRead,
    operation_id="get_customer",
    dependencies=[Depends(RoleChecker(required_permission="customer-read"))],
)
async def read_customer(
    customer_id: UUID,
    service: CustomerService = Depends(get_customer_service),
) -> Any:
    """Get a specific customer by id."""
    item = await service.get_by_id(customer_id)
    if item is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Customer not found",
        )
    return item


@router.put(
    "/{customer_id}",
    response_model=CustomerRead,
    operation_id="update_customer",
    dependencies=[Depends(RoleChecker(required_permission="customer-update"))],
)
async def update_customer(
    customer_id: UUID,
    customer_in: CustomerUpdate,
    service: CustomerService = Depends(get_customer_service),
) -> Any:
    """Update a customer."""
    item = await service.get_by_id(customer_id)
    if item is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Customer not found",
        )
    try:
        return await service.update(customer_id, customer_in)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.delete(
    "/{customer_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    operation_id="delete_customer",
    dependencies=[Depends(RoleChecker(required_permission="customer-delete"))],
)
async def delete_customer(
    customer_id: UUID,
    service: CustomerService = Depends(get_customer_service),
) -> None:
    """Hard delete a customer (idempotent: 204 even if absent)."""
    await service.delete(customer_id)
