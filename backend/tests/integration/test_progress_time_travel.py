"""Integration tests for Progress Entry time-travel functionality."""

from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import (
    get_current_active_user,
    get_current_user,
)
from app.core.rbac import RBACServiceABC, get_rbac_service
from app.main import app
from app.models.domain.user import User
from app.models.schemas.progress_entry import ProgressEntryCreate, ProgressEntryUpdate
from app.services.progress_entry_service import ProgressEntryService

mock_admin_user = User(
    user_id=uuid4(),
    email="admin@example.com",
    is_active=True,
    role="admin",
    full_name="Admin User",
    hashed_password="hash",
    created_by=uuid4(),
)


def mock_get_current_user() -> User:
    return mock_admin_user


def mock_get_current_active_user() -> User:
    return mock_admin_user


class MockRBACService(RBACServiceABC):
    def has_role(self, user_role: str, required_roles: list[str]) -> bool:
        return True

    def has_permission(self, user_role: str, required_permission: str) -> bool:
        return True

    def get_user_permissions(self, user_role: str) -> list[str]:
        return [
            "progress-entry-read",
            "progress-entry-create",
            "cost-element-read",
            "cost-element-create",
        ]


def mock_get_rbac_service() -> MockRBACService:
    return MockRBACService()


@pytest.fixture(autouse=True)
def override_auth():
    app.dependency_overrides[get_current_user] = mock_get_current_user
    app.dependency_overrides[get_current_active_user] = mock_get_current_active_user
    app.dependency_overrides[get_rbac_service] = mock_get_rbac_service
    yield
    app.dependency_overrides = {}


@pytest_asyncio.fixture
async def setup_cost_element(client: AsyncClient):
    """Setup a cost element for testing."""
    # 1. Department
    dept_res = await client.post(
        "/api/v1/departments",
        json={"code": f"D-{uuid4().hex[:4].upper()}", "name": "Dept"},
    )
    dept_id = dept_res.json()["department_id"]

    # 2. Cost Element Type
    type_res = await client.post(
        "/api/v1/cost-element-types",
        json={
            "code": f"T-{uuid4().hex[:4].upper()}",
            "name": "Type",
            "department_id": dept_id,
        },
    )
    type_id = type_res.json()["cost_element_type_id"]

    # 3. Project
    proj_res = await client.post(
        "/api/v1/projects",
        json={"code": f"P-{uuid4().hex[:4].upper()}", "name": "Proj", "budget": 10000},
    )
    proj_id = proj_res.json()["project_id"]

    # 4. WBE
    wbe_res = await client.post(
        "/api/v1/wbes",
        json={
            "code": f"W-{uuid4().hex[:4].upper()}",
            "name": "WBE",
            "project_id": proj_id,
            "branch": "main",
        },
    )
    wbe_id = wbe_res.json()["wbe_id"]

    # 5. Cost Element
    ce_res = await client.post(
        "/api/v1/cost-elements",
        json={
            "code": f"CE-{uuid4().hex[:4].upper()}",
            "name": "Cost Element",
            "budget_amount": 100000,
            "wbe_id": wbe_id,
            "cost_element_type_id": type_id,
            "branch": "main",
        },
    )
    cost_element_id = ce_res.json()["cost_element_id"]

    return {"cost_element_id": cost_element_id}


class TestProgressTimeTravel:
    """Test progress entry time-travel queries."""

    @pytest.mark.asyncio
    async def test_get_latest_progress_with_as_of(
        self,
        db_session: AsyncSession,
        setup_cost_element,
    ):
        """Test get_latest_progress() with historical as_of parameter.

        Test ID: T-009

        Scenario:
        - Day 1: Create progress entry with 25%
        - Day 5: Create progress entry with 50%
        - Day 10: Query with as_of=Day 3
        - Expected: Should return 25% (latest as of Day 3)
        """
        # Arrange
        service = ProgressEntryService(db_session)
        cost_element_id = setup_cost_element["cost_element_id"]
        user_id = mock_admin_user.user_id

        day_1 = datetime(2026, 1, 10, tzinfo=UTC)
        day_5 = datetime(2026, 1, 14, tzinfo=UTC)
        day_3 = datetime(2026, 1, 12, tzinfo=UTC)

        # Create progress entry on Day 1
        await service.create(
            progress_in=ProgressEntryCreate(
                cost_element_id=cost_element_id,
                progress_percentage=Decimal("25.00"),
                notes="Day 1 progress",
                control_date=day_1,
            ),
            actor_id=user_id,
        )

        # Create progress entry on Day 5
        await service.create(
            progress_in=ProgressEntryCreate(
                cost_element_id=cost_element_id,
                progress_percentage=Decimal("50.00"),
                notes="Day 5 progress",
                control_date=day_5,
            ),
            actor_id=user_id,
        )

        # Act - query as of Day 3 (should get Day 1's entry)
        latest = await service.get_latest_progress(
            cost_element_id=cost_element_id,
            as_of=day_3,
        )

        # Assert
        assert latest is not None
        assert latest.progress_percentage == Decimal("25.00")
        assert latest.notes == "Day 1 progress"

    @pytest.mark.asyncio
    async def test_time_travel_with_deleted_entry(
        self,
        db_session: AsyncSession,
        setup_cost_element,
    ):
        """Test that deleted entries are excluded from time-travel queries.

        Test ID: T-019

        Scenario:
        - Day 1: Create progress with 25%
        - Day 3: Soft delete the entry
        - Day 5: Query with as_of=Day 2 (before deletion)
        - Expected: Should return entry
        - Day 7: Query with as_of=Day 4 (after deletion)
        - Expected: Should not return entry
        """
        # Arrange
        service = ProgressEntryService(db_session)
        cost_element_id = setup_cost_element["cost_element_id"]
        user_id = mock_admin_user.user_id

        day_1 = datetime(2026, 1, 10, tzinfo=UTC)
        day_3 = datetime(2026, 1, 12, tzinfo=UTC)
        day_2 = datetime(2026, 1, 11, tzinfo=UTC)
        day_4 = datetime(2026, 1, 13, tzinfo=UTC)

        # Create progress entry
        progress = await service.create(
            progress_in=ProgressEntryCreate(
                cost_element_id=cost_element_id,
                progress_percentage=Decimal("25.00"),
                control_date=day_1,
            ),
            actor_id=user_id,
        )
        progress_entry_id = progress.progress_entry_id

        # Soft delete on Day 3
        await service.soft_delete(
            progress_entry_id=progress_entry_id,
            actor_id=user_id,
            control_date=day_3,
        )

        # Act 1 - query as of Day 2 (before deletion)
        latest_before_delete = await service.get_latest_progress(
            cost_element_id=cost_element_id,
            as_of=day_2,
        )

        # Act 2 - query as of Day 4 (after deletion)
        latest_after_delete = await service.get_latest_progress(
            cost_element_id=cost_element_id,
            as_of=day_4,
        )

        # Assert
        assert latest_before_delete is not None
        assert latest_before_delete.progress_percentage == Decimal("25.00")
        assert latest_after_delete is None

    @pytest.mark.asyncio
    async def test_version_history_query(
        self,
        db_session: AsyncSession,
        setup_cost_element,
    ):
        """Test querying full version history of a progress entry.

        Test ID: T-019

        Scenario:
        - Create progress entry with 25%
        - Update to 50% (creates new version)
        - Update to 75% (creates another version)
        - Query history
        - Expected: 3 versions in history
        """
        # Arrange
        service = ProgressEntryService(db_session)
        cost_element_id = setup_cost_element["cost_element_id"]
        user_id = mock_admin_user.user_id

        # Create initial version
        progress = await service.create(
            progress_in=ProgressEntryCreate(
                cost_element_id=cost_element_id,
                progress_percentage=Decimal("25.00"),
            ),
            actor_id=user_id,
        )
        progress_entry_id = progress.progress_entry_id

        # Update to 50%
        await service.update(
            progress_entry_id=progress_entry_id,
            progress_in=ProgressEntryUpdate(progress_percentage=Decimal("50.00")),
            actor_id=user_id,
        )

        # Update to 75%
        await service.update(
            progress_entry_id=progress_entry_id,
            progress_in=ProgressEntryUpdate(progress_percentage=Decimal("75.00")),
            actor_id=user_id,
        )

        # Act - get history
        history = await service.get_history(root_id=progress_entry_id)

        # Assert
        assert len(history) == 3
        assert history[0].progress_percentage == Decimal("75.00")  # Most recent first
        assert history[1].progress_percentage == Decimal("50.00")
        assert history[2].progress_percentage == Decimal("25.00")

    @pytest.mark.asyncio
    async def test_bitemporal_filtering(
        self,
        db_session: AsyncSession,
        setup_cost_element,
    ):
        """Test bitemporal filtering with valid_time and transaction_time.

        Test ID: T-019

        Scenario:
        - Day 1: Create progress with 25%
        - Day 5: Update to 50% (new version)
        - Day 10: Query with as_of=Day 3
        - Expected: Should return 25% (version valid on Day 3)
        """
        # Arrange
        service = ProgressEntryService(db_session)
        cost_element_id = setup_cost_element["cost_element_id"]
        user_id = mock_admin_user.user_id

        day_1 = datetime(2026, 1, 10, tzinfo=UTC)
        day_5 = datetime(2026, 1, 14, tzinfo=UTC)
        day_3 = datetime(2026, 1, 12, tzinfo=UTC)

        # Create progress on Day 1
        progress = await service.create(
            progress_in=ProgressEntryCreate(
                cost_element_id=cost_element_id,
                progress_percentage=Decimal("25.00"),
                control_date=day_1,
            ),
            actor_id=user_id,
        )

        # Update on Day 5
        await service.update(
            progress_entry_id=progress.progress_entry_id,
            progress_in=ProgressEntryUpdate(progress_percentage=Decimal("50.00")),
            actor_id=user_id,
            control_date=day_5,
        )

        # Act - query as of Day 3 using get_progress_entry_as_of
        historical = await service.get_progress_entry_as_of(
            progress_entry_id=progress.progress_entry_id,
            as_of=day_3,
        )

        # Assert
        assert historical is not None
        assert historical.progress_percentage == Decimal("25.00")

    @pytest.mark.asyncio
    async def test_progress_decrease_with_justification(
        self,
        db_session: AsyncSession,
        setup_cost_element,
    ):
        """Test that progress decrease requires justification.

        Test ID: T-023

        Scenario:
        - Create progress with 75%
        - Update to 50% with justification
        - Query history
        - Expected: Both versions exist, notes contain justification
        """
        # Arrange
        service = ProgressEntryService(db_session)
        cost_element_id = setup_cost_element["cost_element_id"]
        user_id = mock_admin_user.user_id

        # Create initial progress
        progress = await service.create(
            progress_in=ProgressEntryCreate(
                cost_element_id=cost_element_id,
                progress_percentage=Decimal("75.00"),
                notes="Excellent progress",
            ),
            actor_id=user_id,
        )

        # Decrease with justification
        updated = await service.update(
            progress_entry_id=progress.progress_entry_id,
            progress_in=ProgressEntryUpdate(
                progress_percentage=Decimal("50.00"),
                notes="Work undone - inspection failed, rework required",
            ),
            actor_id=user_id,
        )

        # Assert
        assert updated.progress_percentage == Decimal("50.00")
        assert "rework required" in updated.notes

        # Verify history
        history = await service.get_history(root_id=progress.progress_entry_id)
        assert len(history) == 2
        assert history[0].progress_percentage == Decimal("50.00")
        assert history[1].progress_percentage == Decimal("75.00")
