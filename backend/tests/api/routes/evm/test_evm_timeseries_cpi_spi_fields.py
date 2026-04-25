"""Test EVM Time-Series API returns CPI and SPI fields.

This test verifies that the time-series response schema includes the new
CPI (Cost Performance Index) and SPI (Schedule Performance Index) fields.
"""

from datetime import UTC, datetime
from decimal import Decimal
from typing import Any
from uuid import uuid4

import pytest

from app.api.dependencies.auth import (
    get_current_active_user,
    get_current_user,
)
from app.core.rbac import RBACServiceABC, get_rbac_service
from app.main import app
from app.models.domain.user import User
from app.models.schemas.evm import EVMTimeSeriesPoint

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
            "cost-element-read",
            "evm-read",
            "progress-entry-read",
        ]

    async def has_project_access(
        self,
        user_id,
        user_role: str,
        project_id,
        required_permission: str,
    ) -> bool:
        return True

    async def get_user_projects(self, user_id, user_role: str):
        return []

    async def get_project_role(self, user_id, project_id):
        return "admin"


def mock_get_rbac_service() -> MockRBACService:
    return MockRBACService()


@pytest.fixture(autouse=True)
def override_auth() -> Any:
    app.dependency_overrides[get_current_user] = mock_get_current_user
    app.dependency_overrides[get_current_active_user] = mock_get_current_active_user
    app.dependency_overrides[get_rbac_service] = mock_get_rbac_service
    yield
    app.dependency_overrides = {}


@pytest.mark.asyncio
class TestEVMTimeSeriesCPISPI:
    """Test CPI and SPI fields in EVM time-series response schema."""

    async def test_timeseries_point_schema_has_cpi_spi_fields(self):
        """Test that EVMTimeSeriesPoint schema includes cpi and spi fields."""
        # Create a sample time-series point with CPI and SPI
        point = EVMTimeSeriesPoint(
            date=datetime.now(UTC),
            pv=Decimal("1000.0"),
            ev=Decimal("800.0"),
            ac=Decimal("1200.0"),
            forecast=Decimal("1000.0"),
            actual=Decimal("1200.0"),
            cpi=Decimal("0.6666666667"),  # EV / AC = 800 / 1200
            spi=Decimal("0.8"),  # EV / PV = 800 / 1000
        )

        # Assert: All fields are present
        assert point.cpi == Decimal("0.6666666667")
        assert point.spi == Decimal("0.8")
        assert point.pv == Decimal("1000.0")
        assert point.ev == Decimal("800.0")
        assert point.ac == Decimal("1200.0")

    async def test_timeseries_point_schema_allows_null_cpi_spi(self):
        """Test that CPI and SPI can be None (division by zero case)."""
        # Create a point where CPI and SPI are None (AC=0 or PV=0)
        point = EVMTimeSeriesPoint(
            date=datetime.now(UTC),
            pv=Decimal("0.0"),  # PV = 0, so SPI = None
            ev=Decimal("0.0"),
            ac=Decimal("0.0"),  # AC = 0, so CPI = None
            forecast=Decimal("0.0"),
            actual=Decimal("0.0"),
            cpi=None,  # Division by zero
            spi=None,  # Division by zero
        )

        # Assert: None values are allowed
        assert point.cpi is None
        assert point.spi is None

    async def test_timeseries_point_schema_serialization(self):
        """Test that CPI and SPI serialize correctly to JSON."""
        point = EVMTimeSeriesPoint(
            date=datetime.now(UTC),
            pv=Decimal("1000.0"),
            ev=Decimal("800.0"),
            ac=Decimal("1200.0"),
            forecast=Decimal("1000.0"),
            actual=Decimal("1200.0"),
            cpi=Decimal("0.6666666667"),
            spi=Decimal("0.8"),
        )

        # Serialize to dict (simulating JSON response)
        data = point.model_dump()

        # Assert: Fields are in the serialized output
        assert "cpi" in data
        assert "spi" in data
        assert data["cpi"] == Decimal("0.6666666667")
        assert data["spi"] == Decimal("0.8")

        # Test with None values
        point_null = EVMTimeSeriesPoint(
            date=datetime.now(UTC),
            pv=Decimal("1000.0"),
            ev=Decimal("800.0"),
            ac=Decimal("0.0"),
            forecast=Decimal("1000.0"),
            actual=Decimal("0.0"),
            cpi=None,
            spi=Decimal("0.8"),
        )
        data_null = point_null.model_dump()
        assert data_null["cpi"] is None
        assert data_null["spi"] == Decimal("0.8")
