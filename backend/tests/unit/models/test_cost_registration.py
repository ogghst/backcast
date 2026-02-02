"""Unit tests for CostRegistration domain model.

Tests model behavior, mixin composition, and versioning support.
"""

from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

from app.models.domain.cost_registration import CostRegistration


class TestCostRegistrationModel:
    """Test CostRegistration model behavior and Mixin composition."""

    def test_cost_registration_initialization(self):
        """Test basic initialization and mixin defaults.

        Acceptance Criteria:
        - CostRegistration model can be instantiated with required fields
        - cost_registration_id is set (root ID)
        - VersionableMixin provides temporal fields (valid_time, transaction_time, deleted_at)
        - Model is NOT branchable (no branch, parent_id, merge_from_branch)
        - Optional fields (quantity, unit_of_measure, registration_date) can be set

        Expected Failure: ImportError - CostRegistration model doesn't exist yet
        """
        # Arrange
        cost_registration_id = uuid4()
        cost_element_id = uuid4()
        actor_id = uuid4()

        # Act
        registration = CostRegistration(
            cost_registration_id=cost_registration_id,
            cost_element_id=cost_element_id,
            amount=Decimal("100.00"),
            quantity=Decimal("10.0"),
            unit_of_measure="hours",
            registration_date=datetime(2026, 1, 15, tzinfo=UTC),
            description="Equipment rental",
            invoice_number="INV-001",
            created_by=actor_id,
        )

        # Assert
        assert registration.cost_registration_id == cost_registration_id
        assert registration.cost_element_id == cost_element_id
        assert registration.amount == Decimal("100.00")
        assert registration.quantity == Decimal("10.0")
        assert registration.unit_of_measure == "hours"
        assert registration.registration_date == datetime(2026, 1, 15, tzinfo=UTC)
        assert registration.description == "Equipment rental"
        assert registration.invoice_number == "INV-001"
        assert registration.vendor_reference is None

        # VersionableMixin fields exist (valid_time set by DB/SQLAlchemy on persist)
        assert hasattr(registration, "valid_time")
        assert hasattr(registration, "transaction_time")
        assert registration.deleted_at is None
        assert registration.created_by == actor_id
        assert registration.deleted_by is None

        # Not branchable (no BranchableMixin)
        assert not hasattr(registration, "branch")
        assert not hasattr(registration, "parent_id")
        assert not hasattr(registration, "merge_from_branch")

    def test_cost_registration_without_optional_fields(self):
        """Test initialization without quantity, unit_of_measure, or registration_date.

        Acceptance Criteria:
        - Model can be created with just required fields
        - Optional fields default to None
        """
        # Arrange
        cost_registration_id = uuid4()
        cost_element_id = uuid4()
        actor_id = uuid4()

        # Act
        registration = CostRegistration(
            cost_registration_id=cost_registration_id,
            cost_element_id=cost_element_id,
            amount=Decimal("100.00"),
            created_by=actor_id,
        )

        # Assert
        assert registration.quantity is None
        assert registration.unit_of_measure is None
        assert registration.registration_date is None
        assert registration.description is None

    def test_cost_registration_is_deleted_property(self):
        """Test is_deleted property from VersionableMixin.

        Acceptance Criteria:
        - is_deleted returns False when deleted_at is None
        - is_deleted returns True when deleted_at is set

        Expected Failure: ImportError - CostRegistration model doesn't exist yet
        """
        # Arrange
        cost_registration_id = uuid4()
        cost_element_id = uuid4()
        actor_id = uuid4()

        registration = CostRegistration(
            cost_registration_id=cost_registration_id,
            cost_element_id=cost_element_id,
            amount=Decimal("100.00"),
            created_by=actor_id,
        )

        # Assert - not deleted initially
        assert registration.is_deleted is False
        assert registration.deleted_at is None

        # Act - soft delete
        registration.soft_delete()

        # Assert - now deleted
        assert registration.is_deleted is True
        assert registration.deleted_at is not None

    def test_cost_registration_undelete(self):
        """Test undelete method from VersionableMixin.

        Acceptance Criteria:
        - undelete() sets deleted_at back to None
        - is_deleted returns False after undelete

        Expected Failure: ImportError - CostRegistration model doesn't exist yet
        """
        # Arrange
        cost_registration_id = uuid4()
        cost_element_id = uuid4()
        actor_id = uuid4()

        registration = CostRegistration(
            cost_registration_id=cost_registration_id,
            cost_element_id=cost_element_id,
            amount=Decimal("100.00"),
            created_by=actor_id,
        )

        # Soft delete first
        registration.soft_delete()
        assert registration.is_deleted is True

        # Act - undelete
        registration.undelete()

        # Assert
        assert registration.is_deleted is False
        assert registration.deleted_at is None

    def test_cost_registration_clone(self):
        """Test clone method from VersionableMixin.

        Acceptance Criteria:
        - clone() creates new instance with same cost_registration_id
        - clone() allows overriding fields
        - clone() clears id, valid_time, transaction_time for new version

        Expected Failure: ImportError - CostRegistration model doesn't exist yet
        """
        # Arrange
        cost_registration_id = uuid4()
        cost_element_id = uuid4()
        actor_id = uuid4()

        original = CostRegistration(
            cost_registration_id=cost_registration_id,
            cost_element_id=cost_element_id,
            amount=Decimal("100.00"),
            quantity=Decimal("10.0"),
            unit_of_measure="hours",
            created_by=actor_id,
        )

        # Simulate saved state
        original.id = uuid4()

        # Act - clone with override
        cloned = original.clone(
            amount=Decimal("150.00"), quantity=Decimal("15.0"), description="Updated"
        )

        # Assert
        assert cloned.cost_registration_id == cost_registration_id  # Same root ID
        assert cloned.cost_element_id == cost_element_id
        assert cloned.amount == Decimal("150.00")  # Overridden
        assert cloned.quantity == Decimal("15.0")  # Overridden
        assert cloned.description == "Updated"  # Overridden
        assert cloned.unit_of_measure == "hours"  # Preserved
        assert cloned.id is None  # Cleared for new version
        # valid_time and transaction_time will be None for DB to generate

    def test_cost_registration_repr(self):
        """Test __repr__ method for debugging.

        Acceptance Criteria:
        - __repr__ includes key fields for identification

        Expected Failure: ImportError - CostRegistration model doesn't exist yet
        """
        # Arrange
        cost_registration_id = uuid4()
        cost_element_id = uuid4()
        actor_id = uuid4()

        registration = CostRegistration(
            cost_registration_id=cost_registration_id,
            cost_element_id=cost_element_id,
            amount=Decimal("100.00"),
            created_by=actor_id,
        )

        # Act
        repr_str = repr(registration)

        # Assert
        assert "CostRegistration" in repr_str
        assert (
            str(cost_registration_id) in repr_str or "cost_registration_id" in repr_str
        )
