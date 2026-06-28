"""CurrencyRate API routes (admin-managed FX reference ledger)."""

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import RoleChecker
from app.db.session import get_db
from app.models.schemas.currency_rate import (
    CurrencyRateCreate,
    CurrencyRateRead,
    CurrencyRateUpdate,
)
from app.services.currency_rate_service import CurrencyRateService

router = APIRouter()


def get_currency_rate_service(
    session: AsyncSession = Depends(get_db),
) -> CurrencyRateService:
    """Dependency to get CurrencyRateService instance."""
    return CurrencyRateService(session)


@router.get(
    "",
    response_model=None,  # PaginatedResponse[CurrencyRateRead]
    operation_id="get_currency_rates",
    dependencies=[Depends(RoleChecker(required_permission="currency-rate-read"))],
)
async def read_currency_rates(
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    per_page: int = Query(20, ge=1, description="Items per page"),
    search: str | None = Query(None, description="Search term (currency code)"),
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
    service: CurrencyRateService = Depends(get_currency_rate_service),
) -> dict[str, Any]:
    """Retrieve currency rates with server-side search/filter/sort."""
    from app.models.schemas.common import PaginatedResponse

    skip = (page - 1) * per_page
    items, total = await service.get_currency_rates(
        skip=skip,
        limit=per_page,
        search=search,
        filters=filters,
        sort_field=sort_field,
        sort_order=sort_order,
    )

    items_out = [CurrencyRateRead.model_validate(i) for i in items]
    return PaginatedResponse[CurrencyRateRead](
        items=items_out,
        total=total,
        page=page,
        per_page=per_page,
    ).model_dump()


@router.post(
    "",
    response_model=CurrencyRateRead,
    status_code=status.HTTP_201_CREATED,
    operation_id="create_currency_rate",
    dependencies=[Depends(RoleChecker(required_permission="currency-rate-create"))],
)
async def create_currency_rate(
    rate_in: CurrencyRateCreate,
    service: CurrencyRateService = Depends(get_currency_rate_service),
) -> Any:
    """Create a new currency rate."""
    return await service.create(rate_in)


@router.get(
    "/{rate_id}",
    response_model=CurrencyRateRead,
    operation_id="get_currency_rate",
    dependencies=[Depends(RoleChecker(required_permission="currency-rate-read"))],
)
async def read_currency_rate(
    rate_id: UUID,
    service: CurrencyRateService = Depends(get_currency_rate_service),
) -> Any:
    """Get a specific currency rate by id."""
    item = await service.get_by_id(rate_id)
    if item is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Currency Rate not found",
        )
    return item


@router.put(
    "/{rate_id}",
    response_model=CurrencyRateRead,
    operation_id="update_currency_rate",
    dependencies=[Depends(RoleChecker(required_permission="currency-rate-update"))],
)
async def update_currency_rate(
    rate_id: UUID,
    rate_in: CurrencyRateUpdate,
    service: CurrencyRateService = Depends(get_currency_rate_service),
) -> Any:
    """Update a currency rate."""
    item = await service.get_by_id(rate_id)
    if item is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Currency Rate not found",
        )
    try:
        return await service.update(rate_id, rate_in)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.delete(
    "/{rate_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    operation_id="delete_currency_rate",
    dependencies=[Depends(RoleChecker(required_permission="currency-rate-update"))],
)
async def delete_currency_rate(
    rate_id: UUID,
    service: CurrencyRateService = Depends(get_currency_rate_service),
) -> None:
    """Hard delete a currency rate (idempotent: 204 even if absent).

    Uses ``currency-rate-update`` (same admin-only guard as create) since FX
    reference data is admin-managed.
    """
    await service.delete(rate_id)
