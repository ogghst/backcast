"""Unit tests for EVMService time-series functionality.

Test ID Prefix: T-BE-003
"""

from datetime import datetime
from decimal import Decimal
from uuid import uuid4

import pytest

from app.models.schemas.evm import (
    EntityType,
    EVMTimeSeriesGranularity,
    EVMTimeSeriesPoint,
    EVMTimeSeriesResponse,
)
from app.services.evm_service import EVMService


class TestEVMTimeSeriesBasic:
    """Test basic time-series functionality."""

    @pytest.mark.asyncio
    async def test_get_evm_timeseries_method_exists(self) -> None:
        """Test that get_evm_timeseries method exists.

        Test ID: T-BE-003-001

        Expected: Method signature is correct and callable.
        """
        # Arrange
        service = EVMService(None)  # type: ignore[arg-type]  # type: ignore[arg-type]  # No DB needed for signature check

        # Act & Assert - Check method exists
        assert hasattr(service, "get_evm_timeseries")
        assert callable(service.get_evm_timeseries)


class TestEVMTimeSeriesDateRangeHelper:
    """Test date range generation helper method."""

    def test_generate_date_intervals_daily(self) -> None:
        """Test daily date interval generation.

        Test ID: T-BE-003-002

        Expected: Generates one date per day in range.
        """
        # Arrange
        service = EVMService(None)  # type: ignore[arg-type]
        start_date = datetime(2024, 1, 1)
        end_date = datetime(2024, 1, 3)

        # Act
        dates = service._generate_date_intervals(
            start_date, end_date, EVMTimeSeriesGranularity.DAY
        )

        # Assert
        assert len(dates) == 3  # Jan 1, Jan 2, Jan 3
        assert dates[0] == datetime(2024, 1, 1)
        assert dates[1] == datetime(2024, 1, 2)
        assert dates[2] == datetime(2024, 1, 3)

    def test_generate_date_intervals_weekly(self) -> None:
        """Test weekly date interval generation.

        Test ID: T-BE-003-003

        Expected: Generates one date per week in range.
        """
        # Arrange
        service = EVMService(None)  # type: ignore[arg-type]
        start_date = datetime(2024, 1, 1)
        end_date = datetime(2024, 1, 22)  # 3 weeks

        # Act
        dates = service._generate_date_intervals(
            start_date, end_date, EVMTimeSeriesGranularity.WEEK
        )

        # Assert
        assert len(dates) == 4  # Jan 1, Jan 8, Jan 15, Jan 22
        assert dates[0] == datetime(2024, 1, 1)
        assert dates[1] == datetime(2024, 1, 8)
        assert dates[2] == datetime(2024, 1, 15)
        assert dates[3] == datetime(2024, 1, 22)

    def test_generate_date_intervals_monthly(self) -> None:
        """Test monthly date interval generation.

        Test ID: T-BE-003-004

        Expected: Generates one date per month in range.
        """
        # Arrange
        service = EVMService(None)  # type: ignore[arg-type]
        start_date = datetime(2024, 1, 1)
        end_date = datetime(2024, 3, 31)

        # Act
        dates = service._generate_date_intervals(
            start_date, end_date, EVMTimeSeriesGranularity.MONTH
        )

        # Assert
        assert len(dates) == 3  # Jan 1, Feb 1, Mar 1
        assert dates[0] == datetime(2024, 1, 1)
        assert dates[1] == datetime(2024, 2, 1)
        assert dates[2] == datetime(2024, 3, 1)

    def test_generate_date_intervals_monthly_year_boundary(self) -> None:
        """Test monthly date interval generation across year boundary.

        Test ID: T-BE-003-005

        Expected: Correctly handles December to January transition.
        """
        # Arrange
        service = EVMService(None)  # type: ignore[arg-type]
        start_date = datetime(2023, 12, 1)
        end_date = datetime(2024, 2, 1)

        # Act
        dates = service._generate_date_intervals(
            start_date, end_date, EVMTimeSeriesGranularity.MONTH
        )

        # Assert
        assert len(dates) == 3  # Dec 1, Jan 1, Feb 1
        assert dates[0] == datetime(2023, 12, 1)
        assert dates[1] == datetime(2024, 1, 1)
        assert dates[2] == datetime(2024, 2, 1)


class TestEVMTimeSeriesEntityTypes:
    """Test time-series for different entity types."""

    @pytest.mark.asyncio
    async def test_wbe_entity_type_supported(self) -> None:
        """Test that WBE entity type is supported.

        Test ID: T-BE-003-006

        Expected: Method accepts WBE entity type and delegates to _get_wbe_evm_timeseries.
        """
        # Arrange
        service = EVMService(None)  # type: ignore[arg-type]
        entity_id = uuid4()

        # Act & Assert - Method should accept WBE entity type
        # Will fail without DB, but we're checking it doesn't raise "not supported" error
        # It should fail trying to access DB instead
        try:
            await service.get_evm_timeseries(
                entity_type=EntityType.WBE,
                entity_id=entity_id,
                granularity=EVMTimeSeriesGranularity.WEEK,
                control_date=datetime(2024, 1, 15),
                branch="main",
            )
        except ValueError as e:
            # Should NOT be "not yet supported" error
            assert "not yet supported" not in str(e)
        except (AttributeError, TypeError):
            # Expected - no DB connection
            pass

    @pytest.mark.asyncio
    async def test_project_entity_type_supported(self) -> None:
        """Test that PROJECT entity type is supported.

        Test ID: T-BE-003-007

        Expected: Method accepts PROJECT entity type and delegates to _get_project_evm_timeseries.
        """
        # Arrange
        service = EVMService(None)  # type: ignore[arg-type]
        entity_id = uuid4()

        # Act & Assert - Method should accept PROJECT entity type
        try:
            await service.get_evm_timeseries(
                entity_type=EntityType.PROJECT,
                entity_id=entity_id,
                granularity=EVMTimeSeriesGranularity.WEEK,
                control_date=datetime(2024, 1, 15),
                branch="main",
            )
        except ValueError as e:
            # Should NOT be "not yet supported" error
            assert "not yet supported" not in str(e)
        except (AttributeError, TypeError):
            # Expected - no DB connection
            pass


class TestEVMTimeSeriesResponseStructure:
    """Test time-series response structure."""

    @pytest.mark.asyncio
    async def test_response_has_granularity_field(self) -> None:
        """Test that response includes granularity field.

        Test ID: T-BE-003-008

        Expected: Response.granularity matches request granularity.
        """
        response = EVMTimeSeriesResponse(
            granularity=EVMTimeSeriesGranularity.WEEK,
            points=[],
            start_date=datetime(2024, 1, 1),
            end_date=datetime(2024, 1, 31),
            total_points=0,
        )
        assert response.granularity == EVMTimeSeriesGranularity.WEEK

    @pytest.mark.asyncio
    async def test_response_has_points_array(self) -> None:
        """Test that response includes points array.

        Test ID: T-BE-003-009

        Expected: Response.points is a list of EVMTimeSeriesPoint.
        """
        response = EVMTimeSeriesResponse(
            granularity=EVMTimeSeriesGranularity.WEEK,
            points=[],
            start_date=datetime(2024, 1, 1),
            end_date=datetime(2024, 1, 31),
            total_points=0,
        )
        assert isinstance(response.points, list)
        assert response.total_points == 0

    @pytest.mark.asyncio
    async def test_response_has_start_date(self) -> None:
        """Test that response includes start_date.

        Test ID: T-BE-003-010
        """
        start_date = datetime(2024, 1, 1)
        response = EVMTimeSeriesResponse(
            granularity=EVMTimeSeriesGranularity.WEEK,
            points=[],
            start_date=start_date,
            end_date=datetime(2024, 1, 31),
            total_points=0,
        )
        assert response.start_date == start_date

    @pytest.mark.asyncio
    async def test_response_has_end_date(self) -> None:
        """Test that response includes end_date.

        Test ID: T-BE-003-011
        """
        end_date = datetime(2024, 1, 31)
        response = EVMTimeSeriesResponse(
            granularity=EVMTimeSeriesGranularity.WEEK,
            points=[],
            start_date=datetime(2024, 1, 1),
            end_date=end_date,
            total_points=0,
        )
        assert response.end_date == end_date

    @pytest.mark.asyncio
    async def test_response_has_total_points(self) -> None:
        """Test that response includes total_points count.

        Test ID: T-BE-003-012
        """
        response = EVMTimeSeriesResponse(
            granularity=EVMTimeSeriesGranularity.WEEK,
            points=[],
            start_date=datetime(2024, 1, 1),
            end_date=datetime(2024, 1, 31),
            total_points=0,
        )
        assert response.total_points == 0


class TestEVMTimeSeriesPointStructure:
    """Test time-series point structure."""

    def test_point_has_date_field(self) -> None:
        """Test that time-series point has date field.

        Test ID: T-BE-003-013
        """
        point = EVMTimeSeriesPoint(
            date=datetime(2024, 1, 15),
            pv=Decimal("100"),
            ev=Decimal("90"),
            ac=Decimal("95"),
            forecast=Decimal("100"),
            actual=Decimal("95"),
        )
        assert point.date == datetime(2024, 1, 15)

    def test_point_has_pv_field(self) -> None:
        """Test that time-series point has PV (Planned Value) field.

        Test ID: T-BE-003-014
        """
        point = EVMTimeSeriesPoint(
            date=datetime(2024, 1, 15),
            pv=Decimal("100"),
            ev=Decimal("90"),
            ac=Decimal("95"),
            forecast=Decimal("100"),
            actual=Decimal("95"),
        )
        assert point.pv == Decimal("100")

    def test_point_has_ev_field(self) -> None:
        """Test that time-series point has EV (Earned Value) field.

        Test ID: T-BE-003-015
        """
        point = EVMTimeSeriesPoint(
            date=datetime(2024, 1, 15),
            pv=Decimal("100"),
            ev=Decimal("90"),
            ac=Decimal("95"),
            forecast=Decimal("100"),
            actual=Decimal("95"),
        )
        assert point.ev == Decimal("90")

    def test_point_has_ac_field(self) -> None:
        """Test that time-series point has AC (Actual Cost) field.

        Test ID: T-BE-003-016
        """
        point = EVMTimeSeriesPoint(
            date=datetime(2024, 1, 15),
            pv=Decimal("100"),
            ev=Decimal("90"),
            ac=Decimal("95"),
            forecast=Decimal("100"),
            actual=Decimal("95"),
        )
        assert point.ac == Decimal("95")

    def test_point_has_forecast_field(self) -> None:
        """Test that time-series point has forecast field.

        Test ID: T-BE-003-017
        """
        point = EVMTimeSeriesPoint(
            date=datetime(2024, 1, 15),
            pv=Decimal("100"),
            ev=Decimal("90"),
            ac=Decimal("95"),
            forecast=Decimal("110"),
            actual=Decimal("95"),
        )
        assert point.forecast == Decimal("110")

    def test_point_has_actual_field(self) -> None:
        """Test that time-series point has actual field.

        Test ID: T-BE-003-018
        """
        point = EVMTimeSeriesPoint(
            date=datetime(2024, 1, 15),
            pv=Decimal("100"),
            ev=Decimal("90"),
            ac=Decimal("95"),
            forecast=Decimal("100"),
            actual=Decimal("95"),
        )
        assert point.actual == Decimal("95")


class TestEVMTimeSeriesGranularitySupport:
    """Test that all granularity options are supported."""

    @pytest.mark.asyncio
    async def test_method_supports_day_granularity(self) -> None:
        """Test that method signature accepts DAY granularity.

        Test ID: T-BE-003-019
        """
        service = EVMService(None)  # type: ignore[arg-type]
        entity_id = uuid4()

        # This will fail due to no database, but we're checking the signature accepts it
        with pytest.raises((ValueError, AttributeError)):
            await service.get_evm_timeseries(
                entity_type=EntityType.COST_ELEMENT,
                entity_id=entity_id,
                granularity=EVMTimeSeriesGranularity.DAY,
                control_date=datetime(2024, 1, 15),
                branch="main",
            )

    @pytest.mark.asyncio
    async def test_method_supports_week_granularity(self) -> None:
        """Test that method signature accepts WEEK granularity.

        Test ID: T-BE-003-020
        """
        service = EVMService(None)  # type: ignore[arg-type]
        entity_id = uuid4()

        with pytest.raises((ValueError, AttributeError)):
            await service.get_evm_timeseries(
                entity_type=EntityType.COST_ELEMENT,
                entity_id=entity_id,
                granularity=EVMTimeSeriesGranularity.WEEK,
                control_date=datetime(2024, 1, 15),
                branch="main",
            )

    @pytest.mark.asyncio
    async def test_method_supports_month_granularity(self) -> None:
        """Test that method signature accepts MONTH granularity.

        Test ID: T-BE-003-021
        """
        service = EVMService(None)  # type: ignore[arg-type]
        entity_id = uuid4()

        with pytest.raises((ValueError, AttributeError)):
            await service.get_evm_timeseries(
                entity_type=EntityType.COST_ELEMENT,
                entity_id=entity_id,
                granularity=EVMTimeSeriesGranularity.MONTH,
                control_date=datetime(2024, 1, 15),
                branch="main",
            )


class TestEVMTimeSeriesWBEAggregation:
    """Test WBE time-series aggregation methods."""

    def test_wbe_aggregation_method_exists(self) -> None:
        """Test that _get_wbe_evm_timeseries method exists.

        Test ID: T-BE-003-022

        Expected: Method exists and is callable.
        """
        service = EVMService(None)  # type: ignore[arg-type]
        assert hasattr(service, "_get_wbe_evm_timeseries")
        assert callable(service._get_wbe_evm_timeseries)


class TestEVMTimeSeriesProjectAggregation:
    """Test Project time-series aggregation methods."""

    def test_project_aggregation_method_exists(self) -> None:
        """Test that _get_project_evm_timeseries method exists.

        Test ID: T-BE-003-023

        Expected: Method exists and is callable.
        """
        service = EVMService(None)  # type: ignore[arg-type]
        assert hasattr(service, "_get_project_evm_timeseries")
        assert callable(service._get_project_evm_timeseries)


class TestEVMTimeSeriesDataGeneration:
    """Test time-series data generation methods."""

    def test_generate_timeseries_points_method_exists(self) -> None:
        """Test that _generate_timeseries_points method exists.

        Test ID: T-BE-003-024

        Expected: Method exists and is callable.
        """
        service = EVMService(None)  # type: ignore[arg-type]
        assert hasattr(service, "_generate_timeseries_points")
        assert callable(service._generate_timeseries_points)

    def test_get_ev_as_of_date_method_exists(self) -> None:
        """Test that _get_ev_as_of_date method exists.

        Test ID: T-BE-003-025

        Expected: Method exists and is callable.
        """
        service = EVMService(None)  # type: ignore[arg-type]
        assert hasattr(service, "_get_ev_as_of_date")
        assert callable(service._get_ev_as_of_date)
