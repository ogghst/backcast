"""Unit tests for Cost Registration Service."""

from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.domain.cost_registration import CostRegistration
from app.models.schemas.cost_registration import (
    CostRegistrationCreate,
    CostRegistrationUpdate,
)
from app.services.cost_registration_service import CostRegistrationService


class TestCostRegistrationServiceCreate:
    """Test CostRegistrationService.create() method."""

    @pytest.mark.asyncio
    async def test_create_cost_registration_success(
        self, db_session: AsyncSession
    ) -> None:
        """Test successfully creating a cost registration.

        Acceptance Criteria:
        - Cost registration is created with provided amount, description
        - cost_registration_id is set (root ID)
        - Transaction time starts now
        - created_by tracks the actor_id

        Expected Failure: ImportError - CostRegistrationService doesn't exist yet
        """
        # Arrange
        service = CostRegistrationService(db_session)
        cost_element_id = uuid4()
        registration_in = CostRegistrationCreate(
            cost_element_id=cost_element_id,
            amount=Decimal("100.00"),
            description="Equipment rental",
        )
        actor_id = uuid4()

        # Act
        created_registration = await service.create(registration_in, actor_id=actor_id)

        # Assert
        assert created_registration is not None
        assert created_registration.cost_element_id == cost_element_id
        assert created_registration.amount == Decimal("100.00")
        assert created_registration.description == "Equipment rental"
        assert created_registration.cost_registration_id is not None
        assert created_registration.created_by == actor_id
        # registration_date should default to now
        assert created_registration.registration_date is not None

    @pytest.mark.asyncio
    async def test_create_cost_registration_with_all_fields(
        self, db_session: AsyncSession
    ) -> None:
        """Test creating a cost registration with all optional fields.

        Acceptance Criteria:
        - All optional fields (quantity, unit_of_measure, registration_date, invoice_number, vendor_reference) are saved correctly

        Expected Failure: ImportError - CostRegistrationService doesn't exist yet
        """
        # Arrange
        service = CostRegistrationService(db_session)
        cost_element_id = uuid4()
        registration_in = CostRegistrationCreate(
            cost_element_id=cost_element_id,
            amount=Decimal("250.00"),
            quantity=Decimal("10.0"),
            unit_of_measure="hours",
            registration_date=datetime(2026, 1, 16, tzinfo=UTC),
            description="Consulting services",
            invoice_number="INV-2026-001",
            vendor_reference="Acme Consulting Inc.",
        )
        actor_id = uuid4()

        # Act
        created_registration = await service.create(registration_in, actor_id=actor_id)

        # Assert
        assert created_registration.amount == Decimal("250.00")
        assert created_registration.quantity == Decimal("10.0")
        assert created_registration.unit_of_measure == "hours"
        assert created_registration.invoice_number == "INV-2026-001"
        assert created_registration.vendor_reference == "Acme Consulting Inc."

    @pytest.mark.asyncio
    async def test_create_without_registration_date_defaults_to_now(
        self, db_session: AsyncSession
    ) -> None:
        """Test that registration_date defaults to current datetime when not provided.

        Acceptance Criteria:
        - When registration_date is None, it defaults to datetime.now()

        Expected Failure: ImportError - CostRegistrationService doesn't exist yet
        """
        # Arrange
        service = CostRegistrationService(db_session)
        cost_element_id = uuid4()
        registration_in = CostRegistrationCreate(
            cost_element_id=cost_element_id,
            amount=Decimal("100.00"),
            # registration_date intentionally omitted
        )
        actor_id = uuid4()

        # Act
        created_registration = await service.create(registration_in, actor_id=actor_id)

        # Assert
        assert created_registration.registration_date is not None
        # Should be close to now (within 1 second tolerance for test execution)
        from datetime import UTC

        now_utc = datetime.now(UTC)
        assert (
            abs((created_registration.registration_date - now_utc).total_seconds()) < 1
        )


class TestCostRegistrationServiceUpdate:
    """Test CostRegistrationService.update() method."""

    @pytest.mark.asyncio
    async def test_update_creates_new_version(self, db_session: AsyncSession) -> None:
        """Test updating a cost registration creates a new version.

        Acceptance Criteria:
        - Update creates new version with different row ID
        - New version preserves cost_registration_id (root ID)
        - Old version is closed in valid_time
        - New version tracks new actor_id

        Expected Failure: ImportError - CostRegistrationService doesn't exist yet
        """
        # Arrange
        service = CostRegistrationService(db_session)
        cost_element_id = uuid4()

        # Create initial version
        registration_in = CostRegistrationCreate(
            cost_element_id=cost_element_id,
            amount=Decimal("100.00"),
            quantity=Decimal("10.0"),
            description="Original description",
        )
        v1 = await service.create(registration_in, actor_id=uuid4())
        registration_id = v1.cost_registration_id
        v1_id = v1.id  # Capture ID before update

        # Act - Update the amount and description
        update_in = CostRegistrationUpdate(
            amount=Decimal("150.00"),
            quantity=Decimal("15.0"),
            description="Updated description",
        )
        actor_id_2 = uuid4()
        v2 = await service.update(registration_id, update_in, actor_id=actor_id_2)

        # Assert
        await db_session.refresh(v2)  # Ensure v2 is loaded
        assert v2.id != v1_id  # New version has different row ID
        assert v2.cost_registration_id == registration_id  # Same root ID
        assert v2.amount == Decimal("150.00")
        assert v2.quantity == Decimal("15.0")
        assert v2.description == "Updated description"
        assert v2.created_by == actor_id_2  # New version tracks new actor

        # Verify old version still exists in DB
        stmt = select(CostRegistration).where(CostRegistration.id == v1_id)
        old_version = (await db_session.execute(stmt)).scalar_one()
        assert old_version.amount == Decimal("100.00")
        assert old_version.quantity == Decimal("10.0")


class TestCostRegistrationServiceDelete:
    """Test CostRegistrationService.soft_delete() method."""

    @pytest.mark.asyncio
    async def test_soft_delete_cost_registration(
        self, db_session: AsyncSession
    ) -> None:
        """Test soft deleting a cost registration.

        Acceptance Criteria:
        - Soft delete marks deleted_at timestamp
        - Soft delete marks deleted_by with actor_id
        - Soft deleted registration is reversible

        Expected Failure: ImportError - CostRegistrationService doesn't exist yet
        """
        # Arrange
        service = CostRegistrationService(db_session)
        cost_element_id = uuid4()

        registration_in = CostRegistrationCreate(
            cost_element_id=cost_element_id,
            amount=Decimal("100.00"),
            description="To be deleted",
        )
        created_registration = await service.create(registration_in, actor_id=uuid4())
        registration_id = created_registration.cost_registration_id

        # Act
        actor_id_delete = uuid4()
        await service.soft_delete(registration_id, actor_id=actor_id_delete)

        # Assert - Query directly to get the soft-deleted version
        # (get_by_id filters out deleted items)
        stmt = (
            select(CostRegistration)
            .where(CostRegistration.cost_registration_id == registration_id)
            .order_by(CostRegistration.valid_time.desc())
            .limit(1)
        )
        deleted = (await db_session.execute(stmt)).scalar_one()
        assert deleted is not None
        assert deleted.is_deleted is True
        assert deleted.deleted_by == actor_id_delete


class TestCostRegistrationServiceGetById:
    """Test CostRegistrationService.get_by_id() method."""

    @pytest.mark.asyncio
    async def test_get_by_id_returns_current_version(
        self, db_session: AsyncSession
    ) -> None:
        """Test getting a cost registration by root ID returns current version.

        Acceptance Criteria:
        - get_by_id returns the current (latest) version
        - Filters out soft-deleted versions
        - Filters out closed valid_time versions

        Expected Failure: ImportError - CostRegistrationService doesn't exist yet
        """
        # Arrange
        service = CostRegistrationService(db_session)
        cost_element_id = uuid4()

        registration_in = CostRegistrationCreate(
            cost_element_id=cost_element_id,
            amount=Decimal("100.00"),
            description="Test registration",
        )
        created = await service.create(registration_in, actor_id=uuid4())
        registration_id = created.cost_registration_id

        # Act
        retrieved = await service.get_by_id(registration_id)

        # Assert
        assert retrieved is not None
        assert retrieved.cost_registration_id == registration_id
        assert retrieved.amount == Decimal("100.00")
        assert retrieved.is_deleted is False

    @pytest.mark.asyncio
    async def test_get_by_id_returns_none_for_deleted(
        self, db_session: AsyncSession
    ) -> None:
        """Test getting a soft-deleted registration returns None.

        Acceptance Criteria:
        - get_by_id returns None for soft-deleted registrations

        Expected Failure: ImportError - CostRegistrationService doesn't exist yet
        """
        # Arrange
        service = CostRegistrationService(db_session)
        cost_element_id = uuid4()

        registration_in = CostRegistrationCreate(
            cost_element_id=cost_element_id,
            amount=Decimal("100.00"),
        )
        created = await service.create(registration_in, actor_id=uuid4())
        registration_id = created.cost_registration_id

        # Soft delete it
        await service.soft_delete(registration_id, actor_id=uuid4())

        # Act
        retrieved = await service.get_by_id(registration_id)

        # Assert
        assert retrieved is None
