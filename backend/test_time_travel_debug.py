"""Debug script to verify time travel behavior."""

import asyncio
from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.models.schemas.cost_registration import CostRegistrationCreate
from app.services.cost_registration_service import CostRegistrationService

# Setup
DATABASE_URL = "postgresql+asyncpg://postgres:postgres@localhost:5432/backcast_evs"


async def main():
    """Test time travel query with soft delete."""
    engine = create_async_engine(DATABASE_URL, echo=True)
    async_session_maker = async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with async_session_maker() as session:
        service = CostRegistrationService(session)

        # Use a fixed cost element ID (you may need to adjust this)
        cost_element_id = uuid4()

        # Create cost on Jan 1
        registration = await service.create(
            CostRegistrationCreate(
                cost_element_id=cost_element_id,
                amount=Decimal("100.00"),
                registration_date=datetime(2026, 1, 1, tzinfo=UTC),
            ),
            actor_id=uuid4(),
        )
        print(f"Created registration: {registration.cost_registration_id}")
        print(f"  valid_time: {registration.valid_time}")
        print(f"  deleted_at: {registration.deleted_at}")

        # Query total as of Jan 10 (before deletion)
        total_before_delete = await service.get_total_for_cost_element(
            cost_element_id=cost_element_id,
            as_of=datetime(2026, 1, 10, 12, 0, 0, tzinfo=UTC),
        )
        print(f"\nTotal as of Jan 10 (before soft delete): {total_before_delete}")

        # Soft delete on Jan 20
        await service.soft_delete(
            registration.cost_registration_id,
            actor_id=uuid4(),
            control_date=datetime(2026, 1, 20, tzinfo=UTC),
        )

        # Refresh to see the updated deleted_at
        await session.refresh(registration)
        print("\nAfter soft delete:")
        print(f"  deleted_at: {registration.deleted_at}")

        # Query total as of Jan 10 (before deletion)
        total = await service.get_total_for_cost_element(
            cost_element_id=cost_element_id,
            as_of=datetime(2026, 1, 10, 12, 0, 0, tzinfo=UTC),
        )
        print(f"\nTotal as of Jan 10 (after soft delete): {total}")
        print("Expected: 100.00 (deleted_at is Jan 20, which is AFTER Jan 10)")

        # Query total as of Jan 25 (after deletion)
        total_after = await service.get_total_for_cost_element(
            cost_element_id=cost_element_id,
            as_of=datetime(2026, 1, 25, 12, 0, 0, tzinfo=UTC),
        )
        print(f"\nTotal as of Jan 25 (after soft delete): {total_after}")
        print("Expected: 0 (deleted_at is Jan 20, which is BEFORE Jan 25)")

        await session.rollback()

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
