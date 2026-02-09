"""Test to verify UUID serialization fix for impact analysis results.

This test verifies that the fix for the UUID serialization bug works correctly.
The issue was that impact_analysis.model_dump() was returning UUID objects
which cannot be serialized to JSON for storage in JSONB columns.

The fix uses model_dump(mode='json') to convert UUIDs to strings.
"""

import json
from decimal import Decimal
from uuid import UUID, uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.schemas.impact_analysis import (
    EntityChange,
    EntityChanges,
    ImpactAnalysisResponse,
    KPIMetric,
    KPIScorecard,
)


class TestUUIDSerializationFix:
    """Test that UUID objects are properly serialized for JSONB storage."""

    @pytest.mark.asyncio
    async def test_impact_analysis_response_model_dump_json_mode(
        self, db_session: AsyncSession
    ) -> None:
        """Test that ImpactAnalysisResponse can be serialized with mode='json'.

        Acceptance Criteria:
        - model_dump(mode='json') converts UUID to string
        - Result can be serialized to JSON
        - Result can be deserialized back from JSON
        """
        # Arrange - Create an ImpactAnalysisResponse with UUID
        change_order_id = uuid4()
        impact_response = ImpactAnalysisResponse(
            change_order_id=change_order_id,
            branch_name="BR-test-001",
            main_branch_name="main",
            kpi_scorecard=KPIScorecard(
                bac=KPIMetric(
                    main_value=Decimal("100000.00"),
                    change_value=Decimal("120000.00"),
                    delta=Decimal("20000.00"),
                    delta_percent=20.0,
                ),
                budget_delta=KPIMetric(
                    main_value=Decimal("100000.00"),
                    change_value=Decimal("120000.00"),
                    delta=Decimal("20000.00"),
                    delta_percent=20.0,
                ),
                gross_margin=KPIMetric(
                    main_value=Decimal("20000.00"),
                    change_value=Decimal("25000.00"),
                    delta=Decimal("5000.00"),
                    delta_percent=25.0,
                ),
                actual_costs=KPIMetric(
                    main_value=Decimal("80000.00"),
                    change_value=Decimal("95000.00"),
                    delta=Decimal("15000.00"),
                    delta_percent=18.75,
                ),
                revenue_delta=KPIMetric(
                    main_value=Decimal("150000.00"),
                    change_value=Decimal("175000.00"),
                    delta=Decimal("25000.00"),
                    delta_percent=16.67,
                ),
            ),
            entity_changes=EntityChanges(
                wbes=[
                    EntityChange(
                        id=123,
                        name="1.1 - Assembly Station",
                        change_type="modified",
                        budget_delta=Decimal("5000.00"),
                        revenue_delta=Decimal("10000.00"),
                        cost_delta=None,
                    )
                ]
            ),
            waterfall=[],
            time_series=[],
        )

        # Act - Dump with mode='json' to convert UUIDs to strings
        impact_dict = impact_response.model_dump(mode='json')

        # Assert - UUID should be converted to string
        assert isinstance(impact_dict["change_order_id"], str)
        assert impact_dict["change_order_id"] == str(change_order_id)

        # Assert - Can be serialized to JSON (simulating PostgreSQL JSONB storage)
        json_str = json.dumps(impact_dict)
        assert json_str is not None

        # Assert - Can be deserialized from JSON
        deserialized = json.loads(json_str)
        assert deserialized["change_order_id"] == str(change_order_id)

        # Assert - Can convert string back to UUID
        restored_uuid = UUID(deserialized["change_order_id"])
        assert restored_uuid == change_order_id

    @pytest.mark.asyncio
    async def test_impact_analysis_response_model_dump_default_mode_fails(
        self, db_session: AsyncSession
    ) -> None:
        """Test that ImpactAnalysisResponse with default mode cannot be JSON serialized.

        Acceptance Criteria:
        - model_dump() (default mode) returns UUID object
        - UUID object cannot be serialized to JSON
        - This demonstrates why the bug existed
        """
        # Arrange
        change_order_id = uuid4()
        impact_response = ImpactAnalysisResponse(
            change_order_id=change_order_id,
            branch_name="BR-test-001",
            main_branch_name="main",
            kpi_scorecard=KPIScorecard(
                bac=KPIMetric(
                    main_value=Decimal("100000.00"),
                    change_value=Decimal("120000.00"),
                    delta=Decimal("20000.00"),
                    delta_percent=20.0,
                ),
                budget_delta=KPIMetric(
                    main_value=Decimal("100000.00"),
                    change_value=Decimal("120000.00"),
                    delta=Decimal("20000.00"),
                    delta_percent=20.0,
                ),
                gross_margin=KPIMetric(
                    main_value=Decimal("20000.00"),
                    change_value=Decimal("25000.00"),
                    delta=Decimal("5000.00"),
                    delta_percent=25.0,
                ),
                actual_costs=KPIMetric(
                    main_value=Decimal("80000.00"),
                    change_value=Decimal("95000.00"),
                    delta=Decimal("15000.00"),
                    delta_percent=18.75,
                ),
                revenue_delta=KPIMetric(
                    main_value=Decimal("150000.00"),
                    change_value=Decimal("175000.00"),
                    delta=Decimal("25000.00"),
                    delta_percent=16.67,
                ),
            ),
            entity_changes=EntityChanges(),
            waterfall=[],
            time_series=[],
        )

        # Act - Dump with default mode (python mode)
        impact_dict = impact_response.model_dump()

        # Assert - UUID is still a UUID object, not a string
        assert isinstance(impact_dict["change_order_id"], UUID)
        assert not isinstance(impact_dict["change_order_id"], str)

        # Assert - Cannot be serialized to JSON (this would fail in PostgreSQL)
        with pytest.raises(TypeError):
            json.dumps(impact_dict)

    @pytest.mark.asyncio
    async def test_uuid_serialization_roundtrip(self, db_session: AsyncSession) -> None:
        """Test complete roundtrip: UUID -> JSON -> UUID.

        Acceptance Criteria:
        - UUID converts to string in JSON
        - String in JSON converts back to UUID
        - Original UUID is preserved
        """
        # Arrange
        original_uuid = uuid4()

        # Act - Convert to string (simulating model_dump(mode='json'))
        uuid_str = str(original_uuid)

        # Serialize to JSON (simulating PostgreSQL JSONB storage)
        json_data = json.dumps({"change_order_id": uuid_str})

        # Deserialize from JSON
        deserialized = json.loads(json_data)

        # Convert back to UUID
        restored_uuid = UUID(deserialized["change_order_id"])

        # Assert - Original UUID is preserved
        assert restored_uuid == original_uuid
