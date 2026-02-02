"""Unit tests for EVM Pydantic schemas."""

from datetime import datetime
from decimal import Decimal
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.core.versioning.enums import BranchMode
from app.models.schemas.evm import EntityType, EVMMetricsResponse


class TestEntityType:
    """Test EntityType enum validation."""

    def test_entity_type_cost_element_valid(self) -> None:
        """Test EntityType.COST_ELEMENT is valid."""
        # Arrange & Act
        entity_type = EntityType.COST_ELEMENT

        # Assert
        assert entity_type == "cost_element"

    def test_entity_type_wbe_valid(self) -> None:
        """Test EntityType.WBE is valid."""
        # Arrange & Act
        entity_type = EntityType.WBE

        # Assert
        assert entity_type == "wbe"

    def test_entity_type_project_valid(self) -> None:
        """Test EntityType.PROJECT is valid."""
        # Arrange & Act
        entity_type = EntityType.PROJECT

        # Assert
        assert entity_type == "project"


class TestEVMMetricsResponse:
    """Test EVMMetricsResponse schema validation."""

    def test_evm_metrics_response_with_all_fields(self) -> None:
        """Test EVMMetricsResponse validates with all required fields."""
        # Arrange
        entity_id = uuid4()
        control_date = datetime(2024, 1, 15, 12, 0, 0)

        # Act
        metrics = EVMMetricsResponse(
            bac=Decimal("100000"),
            pv=Decimal("50000"),
            ac=Decimal("60000"),
            ev=Decimal("45000"),
            cv=Decimal("-15000"),
            sv=Decimal("-5000"),
            cpi=Decimal("0.75"),
            spi=Decimal("0.9"),
            eac=Decimal("120000"),
            vac=Decimal("-20000"),
            etc=Decimal("60000"),
            entity_type=EntityType.COST_ELEMENT,
            entity_id=entity_id,
            control_date=control_date,
            branch="main",
            branch_mode=BranchMode.MERGE,
            progress_percentage=Decimal("45"),
            warning=None,
        )

        # Assert
        assert metrics.bac == Decimal("100000")
        assert metrics.entity_type == EntityType.COST_ELEMENT
        assert metrics.entity_id == entity_id
        assert metrics.control_date == control_date
        assert metrics.branch == "main"
        assert metrics.branch_mode == BranchMode.MERGE

    def test_evm_metrics_response_with_wbe_entity_type(self) -> None:
        """Test EVMMetricsResponse works with WBE entity type."""
        # Arrange
        entity_id = uuid4()
        control_date = datetime(2024, 1, 15, 12, 0, 0)

        # Act
        metrics = EVMMetricsResponse(
            bac=Decimal("200000"),
            pv=Decimal("100000"),
            ac=Decimal("110000"),
            ev=Decimal("95000"),
            cv=Decimal("-15000"),
            sv=Decimal("-5000"),
            cpi=Decimal("0.864"),
            spi=Decimal("0.95"),
            eac=Decimal("230000"),
            vac=Decimal("-30000"),
            etc=Decimal("120000"),
            entity_type=EntityType.WBE,
            entity_id=entity_id,
            control_date=control_date,
            branch="main",
            branch_mode=BranchMode.MERGE,
            progress_percentage=Decimal("47.5"),
            warning=None,
        )

        # Assert
        assert metrics.entity_type == EntityType.WBE

    def test_evm_metrics_response_with_project_entity_type(self) -> None:
        """Test EVMMetricsResponse works with Project entity type."""
        # Arrange
        entity_id = uuid4()
        control_date = datetime(2024, 1, 15, 12, 0, 0)

        # Act
        metrics = EVMMetricsResponse(
            bac=Decimal("500000"),
            pv=Decimal("250000"),
            ac=Decimal("280000"),
            ev=Decimal("240000"),
            cv=Decimal("-40000"),
            sv=Decimal("-10000"),
            cpi=Decimal("0.857"),
            spi=Decimal("0.96"),
            eac=Decimal("580000"),
            vac=Decimal("-80000"),
            etc=Decimal("300000"),
            entity_type=EntityType.PROJECT,
            entity_id=entity_id,
            control_date=control_date,
            branch="main",
            branch_mode=BranchMode.MERGE,
            progress_percentage=Decimal("48"),
            warning=None,
        )

        # Assert
        assert metrics.entity_type == EntityType.PROJECT

    def test_evm_metrics_response_with_none_indices(self) -> None:
        """Test EVMMetricsResponse allows None for CPI and SPI (division by zero)."""
        # Arrange
        entity_id = uuid4()
        control_date = datetime(2024, 1, 15, 12, 0, 0)

        # Act
        metrics = EVMMetricsResponse(
            bac=Decimal("100000"),
            pv=Decimal("0"),  # No planned value yet
            ac=Decimal("0"),  # No actual costs yet
            ev=Decimal("0"),  # No progress
            cv=Decimal("0"),
            sv=Decimal("0"),
            cpi=None,  # Division by zero
            spi=None,  # Division by zero
            eac=None,
            vac=None,
            etc=None,
            entity_type=EntityType.COST_ELEMENT,
            entity_id=entity_id,
            control_date=control_date,
            branch="main",
            branch_mode=BranchMode.MERGE,
            progress_percentage=None,
            warning="No progress reported",
        )

        # Assert
        assert metrics.cpi is None
        assert metrics.spi is None
        assert metrics.eac is None
        assert metrics.warning == "No progress reported"

    def test_evm_metrics_response_missing_entity_type_fails(self) -> None:
        """Test EVMMetricsResponse validation fails without entity_type."""
        # Arrange
        entity_id = uuid4()
        control_date = datetime(2024, 1, 15, 12, 0, 0)

        # Act & Assert
        with pytest.raises(ValidationError) as exc_info:
            EVMMetricsResponse(
                bac=Decimal("100000"),
                pv=Decimal("50000"),
                ac=Decimal("60000"),
                ev=Decimal("45000"),
                cv=Decimal("-15000"),
                sv=Decimal("-5000"),
                cpi=Decimal("0.75"),
                spi=Decimal("0.9"),
                eac=Decimal("120000"),
                vac=Decimal("-20000"),
                etc=Decimal("60000"),
                # entity_type missing - should fail
                entity_id=entity_id,
                control_date=control_date,
                branch="main",
                branch_mode=BranchMode.MERGE,
                progress_percentage=Decimal("45"),
                warning=None,
            )

        # Assert error contains field name
        assert "entity_type" in str(exc_info.value)

    def test_evm_metrics_response_missing_entity_id_fails(self) -> None:
        """Test EVMMetricsResponse validation fails without entity_id."""
        # Arrange
        control_date = datetime(2024, 1, 15, 12, 0, 0)

        # Act & Assert
        with pytest.raises(ValidationError) as exc_info:
            EVMMetricsResponse(
                bac=Decimal("100000"),
                pv=Decimal("50000"),
                ac=Decimal("60000"),
                ev=Decimal("45000"),
                cv=Decimal("-15000"),
                sv=Decimal("-5000"),
                cpi=Decimal("0.75"),
                spi=Decimal("0.9"),
                eac=Decimal("120000"),
                vac=Decimal("-20000"),
                etc=Decimal("60000"),
                entity_type=EntityType.COST_ELEMENT,
                # entity_id missing - should fail
                control_date=control_date,
                branch="main",
                branch_mode=BranchMode.MERGE,
                progress_percentage=Decimal("45"),
                warning=None,
            )

        # Assert error contains field name
        assert "entity_id" in str(exc_info.value)

    def test_evm_metrics_response_serialization(self) -> None:
        """Test EVMMetricsResponse serializes to dict correctly."""
        # Arrange
        entity_id = uuid4()
        control_date = datetime(2024, 1, 15, 12, 0, 0)

        metrics = EVMMetricsResponse(
            bac=Decimal("100000"),
            pv=Decimal("50000"),
            ac=Decimal("60000"),
            ev=Decimal("45000"),
            cv=Decimal("-15000"),
            sv=Decimal("-5000"),
            cpi=Decimal("0.75"),
            spi=Decimal("0.9"),
            eac=Decimal("120000"),
            vac=Decimal("-20000"),
            etc=Decimal("60000"),
            entity_type=EntityType.COST_ELEMENT,
            entity_id=entity_id,
            control_date=control_date,
            branch="main",
            branch_mode=BranchMode.MERGE,
            progress_percentage=Decimal("45"),
            warning=None,
        )

        # Act
        data = metrics.model_dump()

        # Assert
        assert data["bac"] == Decimal("100000")
        assert data["entity_type"] == "cost_element"
        assert data["entity_id"] == entity_id
        assert data["control_date"] == control_date
        assert data["branch"] == "main"
        assert data["branch_mode"] == BranchMode.MERGE
