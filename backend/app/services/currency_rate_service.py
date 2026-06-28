"""CurrencyRate service - non-versioned FX reference ledger (SimpleEntityBase).

Thin wrapper around :class:`SimpleService` for CRUD + a list/search/filter
method, plus the ``convert_to_base`` helper that resolves the latest effective
rate for a currency as of a given date.
"""

from datetime import datetime
from decimal import Decimal
from typing import Any, cast

from sqlalchemy import and_, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.filtering import FilterParser
from app.core.simple.service import SimpleService
from app.models.domain.currency_rate import CurrencyRate
from app.models.schemas.currency_rate import (
    CurrencyRateCreate,
    CurrencyRateUpdate,
)

#: ISO code of the project base currency. Amounts already in base are returned
#: unchanged (rate == 1.0), and a missing rate for any currency defaults to 1.0
#: so foreign-currency amounts are never silently zeroed.
BASE_CURRENCY = "EUR"


class CurrencyRateService:
    """Service for CurrencyRate management (non-versioned)."""

    def __init__(self, db: AsyncSession) -> None:
        """Initialize service with database session.

        Args:
            db: Async database session.
        """
        self.session = db
        self._simple = SimpleService[CurrencyRate](db, CurrencyRate)

    async def get_by_id(self, rate_id: Any) -> CurrencyRate | None:
        """Get a currency rate by primary key id."""
        return await self._simple.get(rate_id)

    async def create(self, rate_in: CurrencyRateCreate) -> CurrencyRate:
        """Create a new currency rate."""
        data = rate_in.model_dump(exclude_unset=True)
        return await self._simple.create(**data)

    async def update(self, rate_id: Any, rate_in: CurrencyRateUpdate) -> CurrencyRate:
        """Update a currency rate in place (raises ValueError if not found)."""
        updates = rate_in.model_dump(exclude_unset=True)
        return await self._simple.update(rate_id, **updates)

    async def delete(self, rate_id: Any) -> bool:
        """Hard delete a currency rate (returns True if deleted)."""
        return await self._simple.delete(rate_id)

    async def get_currency_rates(
        self,
        skip: int = 0,
        limit: int = 100000,
        search: str | None = None,
        filters: str | None = None,
        sort_field: str | None = None,
        sort_order: str = "asc",
    ) -> tuple[list[CurrencyRate], int]:
        """Get currency rates with server-side search/filter/sort.

        Args:
            skip: Pagination offset.
            limit: Maximum number of rows to return.
            search: Case-insensitive search on currency code.
            filters: URL filter string (supports G4 range operators on real
                columns — e.g. ``effective_date__date_range:...``).
            sort_field: Column to sort by.
            sort_order: "asc" or "desc".

        Returns:
            Tuple of (items, total_count).
        """
        stmt = select(CurrencyRate)

        if search:
            stmt = stmt.where(CurrencyRate.currency.ilike(f"%{search.upper()}%"))

        if filters:
            allowed_fields = ["currency", "effective_date", "rate_to_base"]
            parsed_filters = FilterParser.parse_filters(filters)
            filter_expressions = FilterParser.build_sqlalchemy_filters(
                cast(Any, CurrencyRate),
                parsed_filters,
                allowed_fields=allowed_fields,
            )
            if filter_expressions:
                stmt = stmt.where(and_(*filter_expressions))

        count_stmt = select(func.count()).select_from(stmt.subquery())
        total_result = await self.session.execute(count_stmt)
        total = total_result.scalar_one()

        if sort_field and hasattr(CurrencyRate, sort_field):
            column = getattr(CurrencyRate, sort_field)
            if sort_order.lower() == "desc":
                stmt = stmt.order_by(column.desc())
            else:
                stmt = stmt.order_by(column.asc())
        else:
            # Default: newest effective_date first — most relevant for FX.
            stmt = stmt.order_by(desc(CurrencyRate.effective_date))

        stmt = stmt.offset(skip).limit(limit)

        result = await self.session.execute(stmt)
        items: list[CurrencyRate] = list(result.scalars().all())
        return items, total

    async def convert_to_base(
        self, amount: Decimal, currency: str, as_of: datetime
    ) -> Decimal:
        """Convert ``amount`` in ``currency`` to the base currency as of ``as_of``.

        Resolves the latest stored rate with ``effective_date <= as_of.date()``
        for ``currency``. Returns ``amount`` unchanged when ``currency`` is the
        base currency or when no rate is found (defensive: foreign amounts are
        never silently zeroed by a missing ledger row).

        Args:
            amount: Amount in the source currency.
            currency: ISO-4217 source currency code.
            as_of: Timestamp defining "latest known" (date portion only).

        Returns:
            Amount expressed in the base currency.
        """
        if currency.upper() == BASE_CURRENCY:
            return amount

        as_of_date = as_of.date() if isinstance(as_of, datetime) else as_of
        stmt = (
            select(CurrencyRate.rate_to_base)
            .where(
                CurrencyRate.currency == currency.upper(),
                CurrencyRate.effective_date <= cast(Any, as_of_date),
            )
            .order_by(desc(CurrencyRate.effective_date))
            .limit(1)
        )
        result = await self.session.execute(stmt)
        rate = result.scalar_one_or_none()
        if rate is None:
            return amount
        return Decimal(amount) * Decimal(rate)


async def convert_to_base(
    session: AsyncSession,
    amount: Decimal,
    currency: str,
    as_of: datetime,
) -> Decimal:
    """Module-level convenience wrapper around :meth:`CurrencyRateService.convert_to_base`.

    Args:
        session: Async database session.
        amount: Amount in the source currency.
        currency: ISO-4217 source currency code.
        as_of: Timestamp defining "latest known" (date portion only).

    Returns:
        Amount expressed in the base currency.
    """
    return await CurrencyRateService(session).convert_to_base(amount, currency, as_of)


# Re-exported for callers that import date as a type hint.
__all__ = [
    "BASE_CURRENCY",
    "CurrencyRateService",
    "convert_to_base",
]
