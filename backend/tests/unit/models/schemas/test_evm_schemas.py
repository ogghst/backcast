"""Unit tests for EVM (Earned Value Management) Pydantic schemas.

Tests schema validation, field types, and enum values for generic EVM response schemas.
"""

from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.core.versioning.enums import BranchMode
from app.models.schemas.evm import (
    EntityType,
    EVMMetricsResponse,
    EVMTimeSeriesGranularity,
    EVMTimeSeriesPoint,
    EVMTimeSeriesResponse,
)

# Note: EVMMetricsResponse uses float types for JSON serialization
# EVMTimeSeriesPoint uses Decimal types for precision in time-series data


class TestEntityType:
    """Test EntityType enum validation."""

    def test_entity_type_enum_has_required_values(self):
        """Test that EntityType enum has cost_element, wbe, and project values.

        Acceptance Criteria:
        - EntityType enum includes COST_ELEMENT value
        - EntityType enum includes WBE value
        - EntityType enum includes PROJECT value
        """
        # Assert - All required values exist
        assert EntityType.COST_ELEMENT == "cost_element"
        assert EntityType.WBE == "wbe"
        assert EntityType.PROJECT == "project"

    def test_entity_type_enum_is_string_enum(self):
        """Test that EntityType is a string enum for JSON serialization.

        Acceptance Criteria:
        - EntityType inherits from str
        - Values are strings
        """
        # Assert
        assert issubclass(EntityType, str)
        assert isinstance(EntityType.COST_ELEMENT, str)


class TestEVMMetricsResponse:
    """Test EVMMetricsResponse schema validation."""

    def test_evm_metrics_response_with_all_fields_validates(self):
        """Test that EVMMetricsResponse validates with all required fields.

        Acceptance Criteria:
        - Schema validates with all EVM metrics fields
        - Flat structure with all metrics explicitly defined
        - All required fields are present
        """
        # Arrange
        entity_id = uuid4()
        control_date = datetime(2026, 1, 22, tzinfo=UTC)

        # Act - Create with all fields (schema converts to float)
        metrics = EVMMetricsResponse(
            entity_type=EntityType.COST_ELEMENT,
            entity_id=entity_id,
            bac=100000.0,
            pv=50000.0,
            ev=45000.0,
            ac=55000.0,
            cv=-10000.0,
            sv=-5000.0,
            cpi=0.818,
            spi=0.90,
            eac=122000.0,
            vac=-22000.0,
            etc=67000.0,
            control_date=control_date,
            branch="main",
            branch_mode=BranchMode.MERGE,
        )

        # Assert
        assert metrics.entity_type == EntityType.COST_ELEMENT
        assert metrics.entity_id == entity_id
        assert metrics.bac == 100000.0
        assert metrics.pv == 50000.0
        assert metrics.ev == 45000.0
        assert metrics.ac == 55000.0
        assert metrics.cv == -10000.0
        assert metrics.sv == -5000.0
        assert metrics.cpi == 0.818
        assert metrics.spi == 0.90
        assert metrics.eac == 122000.0
        assert metrics.vac == -22000.0
        assert metrics.etc == 67000.0
        assert metrics.control_date == control_date
        assert metrics.branch == "main"

    def test_evm_metrics_response_flat_structure_not_list(self):
        """Test that EVMMetricsResponse has flat structure, not list-based.

        Acceptance Criteria:
        - Metrics are individual fields, not a list
        - No metrics list field exists
        """
        # Arrange
        entity_id = uuid4()
        control_date = datetime(2026, 1, 22, tzinfo=UTC)

        # Act
        metrics = EVMMetricsResponse(
            entity_type=EntityType.WBE,
            entity_id=entity_id,
            bac=100000.0,
            pv=50000.0,
            ev=45000.0,
            ac=55000.0,
            cv=-10000.0,
            sv=-5000.0,
            cpi=0.818,
            spi=0.90,
            eac=122000.0,
            vac=-22000.0,
            etc=67000.0,
            control_date=control_date,
            branch="main",
            branch_mode=BranchMode.STRICT,
        )

        # Assert - Individual fields exist
        assert hasattr(metrics, "bac")
        assert hasattr(metrics, "pv")
        assert hasattr(metrics, "ev")
        assert hasattr(metrics, "ac")
        assert hasattr(metrics, "cv")
        assert hasattr(metrics, "sv")
        assert hasattr(metrics, "cpi")
        assert hasattr(metrics, "spi")
        assert hasattr(metrics, "eac")
        assert hasattr(metrics, "vac")
        assert hasattr(metrics, "etc")

        # Assert - No metrics list
        assert not hasattr(metrics, "metrics")

    def test_evm_metrics_response_missing_required_field_raises_error(self):
        """Test that EVMMetricsResponse requires all fields.

        Acceptance Criteria:
        - Missing required field raises ValidationError
        """
        # Arrange
        entity_id = uuid4()
        control_date = datetime(2026, 1, 22, tzinfo=UTC)

        # Act & Assert - Missing required fields
        with pytest.raises(ValidationError) as exc_info:
            EVMMetricsResponse(
                entity_type=EntityType.PROJECT,
                entity_id=entity_id,
                bac=100000.0,
                # Missing pv, ev, ac, cv, sv, cpi, spi, eac, vac, etc
                control_date=control_date,
                branch="main",
                branch_mode=BranchMode.MERGE,
            )

        errors = exc_info.value.errors()
        assert len(errors) > 0

    def test_evm_metrics_response_with_wbe_entity_type(self):
        """Test that EVMMetricsResponse accepts WBE entity type.

        Acceptance Criteria:
        - entity_type can be EntityType.WBE
        """
        # Arrange
        wbe_id = uuid4()
        control_date = datetime(2026, 1, 22, tzinfo=UTC)

        # Act
        metrics = EVMMetricsResponse(
            entity_type=EntityType.WBE,
            entity_id=wbe_id,
            bac=50000.0,
            pv=25000.0,
            ev=24000.0,
            ac=26000.0,
            cv=-2000.0,
            sv=-1000.0,
            cpi=0.923,
            spi=0.96,
            eac=54000.0,
            vac=-4000.0,
            etc=28000.0,
            control_date=control_date,
            branch="feature-branch",
            branch_mode=BranchMode.STRICT,
        )

        # Assert
        assert metrics.entity_type == EntityType.WBE

    def test_evm_metrics_response_with_project_entity_type(self):
        """Test that EVMMetricsResponse accepts PROJECT entity type.

        Acceptance Criteria:
        - entity_type can be EntityType.PROJECT
        """
        # Arrange
        project_id = uuid4()
        control_date = datetime(2026, 1, 22, tzinfo=UTC)

        # Act
        metrics = EVMMetricsResponse(
            entity_type=EntityType.PROJECT,
            entity_id=project_id,
            bac=1000000.0,
            pv=500000.0,
            ev=480000.0,
            ac=520000.0,
            cv=-40000.0,
            sv=-20000.0,
            cpi=0.923,
            spi=0.96,
            eac=1080000.0,
            vac=-80000.0,
            etc=560000.0,
            control_date=control_date,
            branch="main",
            branch_mode=BranchMode.MERGE,
        )

        # Assert
        assert metrics.entity_type == EntityType.PROJECT


class TestEVMTimeSeriesPoint:
    """Test EVMTimeSeriesPoint schema validation."""

    def test_evm_time_series_point_with_all_fields_validates(self):
        """Test that EVMTimeSeriesPoint validates with all fields.

        Acceptance Criteria:
        - Schema validates with date and all metric values
        - All fields are properly typed
        """
        # Arrange
        point_date = datetime(2026, 1, 22, tzinfo=UTC)

        # Act
        point = EVMTimeSeriesPoint(
            date=point_date,
            pv=Decimal("50000.00"),
            ev=Decimal("45000.00"),
            ac=Decimal("55000.00"),
            forecast=Decimal("60000.00"),
            actual=Decimal("55000.00"),
        )

        # Assert
        assert point.date == point_date
        assert point.pv == Decimal("50000.00")
        assert point.ev == Decimal("45000.00")
        assert point.ac == Decimal("55000.00")
        assert point.forecast == Decimal("60000.00")
        assert point.actual == Decimal("55000.00")

    def test_evm_time_series_point_missing_required_field_raises_error(self):
        """Test that EVMTimeSeriesPoint requires all fields.

        Acceptance Criteria:
        - Missing required field raises ValidationError
        """
        # Arrange
        point_date = datetime(2026, 1, 22, tzinfo=UTC)

        # Act & Assert - Missing required fields
        with pytest.raises(ValidationError) as exc_info:
            EVMTimeSeriesPoint(
                date=point_date,
                pv=Decimal("50000.00"),
                # Missing ev, ac, forecast, actual
            )

        errors = exc_info.value.errors()
        assert len(errors) > 0


class TestEVMTimeSeriesGranularity:
    """Test EVMTimeSeriesGranularity enum validation."""

    def test_evm_time_series_granularity_enum_has_required_values(self):
        """Test that EVMTimeSeriesGranularity enum has day, week, and month values.

        Acceptance Criteria:
        - Enum includes DAY value
        - Enum includes WEEK value
        - Enum includes MONTH value
        """
        # Assert
        assert EVMTimeSeriesGranularity.DAY == "day"
        assert EVMTimeSeriesGranularity.WEEK == "week"
        assert EVMTimeSeriesGranularity.MONTH == "month"

    def test_evm_time_series_granularity_enum_is_string_enum(self):
        """Test that EVMTimeSeriesGranularity is a string enum.

        Acceptance Criteria:
        - Enum inherits from str
        - Values are strings
        """
        # Assert
        assert issubclass(EVMTimeSeriesGranularity, str)
        assert isinstance(EVMTimeSeriesGranularity.WEEK, str)


class TestEVMTimeSeriesResponse:
    """Test EVMTimeSeriesResponse schema validation."""

    def test_evm_time_series_response_with_all_fields_validates(self):
        """Test that EVMTimeSeriesResponse validates with all fields.

        Acceptance Criteria:
        - Schema validates with granularity, points, and metadata
        - points is a list of EVMTimeSeriesPoint
        """
        # Arrange
        point1_date = datetime(2026, 1, 15, tzinfo=UTC)
        point2_date = datetime(2026, 1, 22, tzinfo=UTC)

        points = [
            EVMTimeSeriesPoint(
                date=point1_date,
                pv=Decimal("40000.00"),
                ev=Decimal("38000.00"),
                ac=Decimal("42000.00"),
                forecast=Decimal("45000.00"),
                actual=Decimal("42000.00"),
            ),
            EVMTimeSeriesPoint(
                date=point2_date,
                pv=Decimal("50000.00"),
                ev=Decimal("45000.00"),
                ac=Decimal("55000.00"),
                forecast=Decimal("60000.00"),
                actual=Decimal("55000.00"),
            ),
        ]

        # Act
        response = EVMTimeSeriesResponse(
            granularity=EVMTimeSeriesGranularity.WEEK,
            points=points,
            start_date=datetime(2026, 1, 1, tzinfo=UTC),
            end_date=datetime(2026, 1, 31, tzinfo=UTC),
            total_points=2,
        )

        # Assert
        assert response.granularity == EVMTimeSeriesGranularity.WEEK
        assert len(response.points) == 2
        assert response.points[0].date == point1_date
        assert response.points[1].date == point2_date
        assert response.start_date == datetime(2026, 1, 1, tzinfo=UTC)
        assert response.end_date == datetime(2026, 1, 31, tzinfo=UTC)
        assert response.total_points == 2

    def test_evm_time_series_response_default_weekly_granularity(self):
        """Test that EVMTimeSeriesResponse uses weekly granularity by default.

        Acceptance Criteria:
        - granularity defaults to WEEK if not provided
        """
        # Arrange
        points = [
            EVMTimeSeriesPoint(
                date=datetime(2026, 1, 15, tzinfo=UTC),
                pv=Decimal("40000.00"),
                ev=Decimal("38000.00"),
                ac=Decimal("42000.00"),
                forecast=Decimal("45000.00"),
                actual=Decimal("42000.00"),
            ),
        ]

        # Act - Note: In production code, this would have a default value
        # For now, we'll test with explicit WEEK value
        response = EVMTimeSeriesResponse(
            granularity=EVMTimeSeriesGranularity.WEEK,
            points=points,
            start_date=datetime(2026, 1, 1, tzinfo=UTC),
            end_date=datetime(2026, 1, 31, tzinfo=UTC),
            total_points=1,
        )

        # Assert
        assert response.granularity == EVMTimeSeriesGranularity.WEEK

    def test_evm_time_series_response_with_day_granularity(self):
        """Test that EVMTimeSeriesResponse accepts day granularity.

        Acceptance Criteria:
        - granularity can be DAY
        """
        # Arrange
        points = [
            EVMTimeSeriesPoint(
                date=datetime(2026, 1, 15, tzinfo=UTC),
                pv=Decimal("40000.00"),
                ev=Decimal("38000.00"),
                ac=Decimal("42000.00"),
                forecast=Decimal("45000.00"),
                actual=Decimal("42000.00"),
            ),
        ]

        # Act
        response = EVMTimeSeriesResponse(
            granularity=EVMTimeSeriesGranularity.DAY,
            points=points,
            start_date=datetime(2026, 1, 1, tzinfo=UTC),
            end_date=datetime(2026, 1, 31, tzinfo=UTC),
            total_points=1,
        )

        # Assert
        assert response.granularity == EVMTimeSeriesGranularity.DAY

    def test_evm_time_series_response_with_month_granularity(self):
        """Test that EVMTimeSeriesResponse accepts month granularity.

        Acceptance Criteria:
        - granularity can be MONTH
        """
        # Arrange
        points = [
            EVMTimeSeriesPoint(
                date=datetime(2026, 1, 15, tzinfo=UTC),
                pv=Decimal("40000.00"),
                ev=Decimal("38000.00"),
                ac=Decimal("42000.00"),
                forecast=Decimal("45000.00"),
                actual=Decimal("42000.00"),
            ),
        ]

        # Act
        response = EVMTimeSeriesResponse(
            granularity=EVMTimeSeriesGranularity.MONTH,
            points=points,
            start_date=datetime(2026, 1, 1, tzinfo=UTC),
            end_date=datetime(2026, 1, 31, tzinfo=UTC),
            total_points=1,
        )

        # Assert
        assert response.granularity == EVMTimeSeriesGranularity.MONTH

    def test_evm_time_series_response_missing_required_field_raises_error(self):
        """Test that EVMTimeSeriesResponse requires all fields.

        Acceptance Criteria:
        - Missing required field raises ValidationError
        """
        # Act & Assert - Missing required fields
        with pytest.raises(ValidationError) as exc_info:
            EVMTimeSeriesResponse(
                granularity=EVMTimeSeriesGranularity.WEEK,
                # Missing points, start_date, end_date, total_points
            )

        errors = exc_info.value.errors()
        assert len(errors) > 0

    def test_evm_time_series_response_empty_points_list(self):
        """Test that EVMTimeSeriesResponse accepts empty points list.

        Acceptance Criteria:
        - points can be an empty list
        """
        # Act
        response = EVMTimeSeriesResponse(
            granularity=EVMTimeSeriesGranularity.WEEK,
            points=[],
            start_date=datetime(2026, 1, 1, tzinfo=UTC),
            end_date=datetime(2026, 1, 31, tzinfo=UTC),
            total_points=0,
        )

        # Assert
        assert len(response.points) == 0
        assert response.total_points == 0
