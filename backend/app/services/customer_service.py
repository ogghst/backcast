"""Customer service - non-versioned reference data (SimpleEntityBase).

Thin wrapper around :class:`SimpleService` for CRUD, plus a list/search/filter
method that mirrors the CostElementTypeService read pattern but without EVCS
time-travel (Customer is non-versioned).
"""

from typing import Any, cast

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.filtering import FilterParser
from app.core.simple.service import SimpleService
from app.models.domain.customer import Customer
from app.models.schemas.customer import CustomerCreate, CustomerUpdate


class CustomerService:
    """Service for Customer management (non-versioned)."""

    def __init__(self, db: AsyncSession) -> None:
        """Initialize service with database session.

        Args:
            db: Async database session.
        """
        self.session = db
        self._simple = SimpleService[Customer](db, Customer)

    async def get_by_id(self, customer_id: Any) -> Customer | None:
        """Get a customer by primary key id."""
        return await self._simple.get(customer_id)

    async def create(self, customer_in: CustomerCreate) -> Customer:
        """Create a new customer."""
        data = customer_in.model_dump(exclude_unset=True)
        return await self._simple.create(**data)

    async def update(self, customer_id: Any, customer_in: CustomerUpdate) -> Customer:
        """Update a customer in place (raises ValueError if not found)."""
        updates = customer_in.model_dump(exclude_unset=True)
        return await self._simple.update(customer_id, **updates)

    async def delete(self, customer_id: Any) -> bool:
        """Hard delete a customer (returns True if deleted, False if absent)."""
        return await self._simple.delete(customer_id)

    async def get_customers(
        self,
        skip: int = 0,
        limit: int = 100000,
        search: str | None = None,
        filters: str | None = None,
        sort_field: str | None = None,
        sort_order: str = "asc",
    ) -> tuple[list[Customer], int]:
        """Get customers with server-side search, filtering, and sorting.

        Args:
            skip: Pagination offset.
            limit: Maximum number of rows to return.
            search: Case-insensitive search across code and name.
            filters: URL filter string (column:value;column:value1,value2,
                supports G4 range operators on real columns).
            sort_field: Column to sort by.
            sort_order: "asc" or "desc".

        Returns:
            Tuple of (items, total_count).
        """
        stmt = select(Customer)

        if search:
            search_term = f"%{search}%"
            stmt = stmt.where(
                or_(
                    Customer.code.ilike(search_term),
                    Customer.name.ilike(search_term),
                )
            )

        if filters:
            allowed_fields = ["code", "name", "is_active"]
            parsed_filters = FilterParser.parse_filters(filters)
            filter_expressions = FilterParser.build_sqlalchemy_filters(
                cast(Any, Customer),
                parsed_filters,
                allowed_fields=allowed_fields,
            )
            if filter_expressions:
                stmt = stmt.where(and_(*filter_expressions))

        count_stmt = select(func.count()).select_from(stmt.subquery())
        total_result = await self.session.execute(count_stmt)
        total = total_result.scalar_one()

        if sort_field and hasattr(Customer, sort_field):
            column = getattr(Customer, sort_field)
            if sort_order.lower() == "desc":
                stmt = stmt.order_by(column.desc())
            else:
                stmt = stmt.order_by(column.asc())
        else:
            stmt = stmt.order_by(Customer.name.asc())

        stmt = stmt.offset(skip).limit(limit)

        result = await self.session.execute(stmt)
        items: list[Customer] = list(result.scalars().all())
        return items, total
