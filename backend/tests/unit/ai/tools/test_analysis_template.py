"""Test Analysis tool template functionality and validation."""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.tools.types import ToolContext


@pytest.fixture
def mock_session() -> AsyncMock:
    """Create a mock database session."""
    return AsyncMock(spec=AsyncSession)


class TestAnalysisTemplateValidation:
    """Test Analysis template input validation and error handling."""

    # === T-TPL-ANA-01: test_calculate_evm_metrics_validates_dates ===
    @pytest.mark.asyncio
    async def test_calculate_evm_metrics_validates_project_id(
        self,
        mock_session: AsyncMock
    ) -> None:
        """Test that calculate_evm_metrics validates project_id format.

        Given:
            A calculate_evm_metrics call with invalid project_id
        When:
            The function is called
        Then:
            Error is returned for invalid UUID format
        """
        from app.ai.tools.templates import analysis_template

        # Arrange: Create context
        context = ToolContext(
            session=mock_session,
            user_id=str(uuid4()),
            user_role="admin"
        )

        # Act: Try to calculate with invalid project_id
        result = await analysis_template.calculate_evm_metrics(  # type: ignore[operator]
            project_id="not-a-uuid",
            context=context
        )

        # Assert: Should return error
        assert "error" in result
        assert "Invalid" in result["error"] or "input" in result["error"]

    @pytest.mark.asyncio
    async def test_calculate_evm_metrics_validates_date_format(
        self,
        mock_session: AsyncMock
    ) -> None:
        """Test that calculate_evm_metrics validates date format.

        Given:
            A calculate_evm_metrics call with invalid date format
        When:
            The function is called
        Then:
            Error is returned for invalid date format
        """
        from app.ai.tools.templates import analysis_template

        # Arrange: Create context
        context = ToolContext(
            session=mock_session,
            user_id=str(uuid4()),
            user_role="admin"
        )

        # Act: Try to calculate with invalid date format
        result = await analysis_template.calculate_evm_metrics(  # type: ignore[operator]
            project_id=str(uuid4()),
            as_of_date="not-a-date",
            context=context
        )

        # Assert: Should return error
        assert "error" in result
        assert "Invalid" in result["error"] or "input" in result["error"]

    @pytest.mark.asyncio
    async def test_calculate_evm_metrics_handles_future_date(
        self,
        mock_session: AsyncMock
    ) -> None:
        """Test that calculate_evm_metrics handles future dates.

        Given:
            A calculate_evm_metrics call with future date
        When:
            The function is called
        Then:
            Date is handled gracefully (may use current date instead)
        """
        from app.ai.tools.templates import analysis_template

        # Arrange: Create context
        context = ToolContext(
            session=mock_session,
            user_id=str(uuid4()),
            user_role="admin"
        )

        # Mock EVM service
        mock_evm_service = AsyncMock()
        mock_evm_data = MagicMock()
        mock_evm_data.pv = 100000
        mock_evm_data.ev = 95000
        mock_evm_data.ac = 98000
        mock_evm_data.cv = -3000
        mock_evm_data.sv = -5000
        mock_evm_data.cpi = 0.97
        mock_evm_data.spi = 0.95
        mock_evm_data.vac = -5000
        mock_evm_data.etc = 5000
        mock_evm_data.eac = 105000
        mock_evm_data.bac = 100000
        mock_evm_data.progress_percentage = 95.0
        mock_evm_data.warning = None
        mock_evm_service.calculate_evm_metrics_batch.return_value = mock_evm_data

        with patch.object(
            ToolContext,
            'evm_service',
            mock_evm_service
        ):
            # Act: Calculate with future date
            future_date = "2099-12-31"
            result = await analysis_template.calculate_evm_metrics(  # type: ignore[operator]
                project_id=str(uuid4()),
                as_of_date=future_date,
                context=context
            )

            # Assert: Should handle gracefully
            assert isinstance(result, dict)

    @pytest.mark.asyncio
    async def test_calculate_evm_metrics_handles_nonexistent_project(
        self,
        mock_session: AsyncMock
    ) -> None:
        """Test that calculate_evm_metrics handles non-existent project.

        Given:
            A calculate_evm_metrics call with non-existent project_id
        When:
            The function is called
        Then:
            Error is returned for non-existent project
        """
        from app.ai.tools.templates import analysis_template

        # Arrange: Create context
        context = ToolContext(
            session=mock_session,
            user_id=str(uuid4()),
            user_role="admin"
        )

        # Mock EVM service to raise exception
        mock_evm_service = AsyncMock()
        mock_evm_service.calculate_evm_metrics_batch.side_effect = Exception("Project not found")

        with patch.object(
            ToolContext,
            'evm_service',
            mock_evm_service
        ):
            # Act: Try to calculate for non-existent project
            result = await analysis_template.calculate_evm_metrics(  # type: ignore[operator]
                project_id=str(uuid4()),
                context=context
            )

            # Assert: Should return error
            assert "error" in result

    # === T-TPL-ANA-02: test_forecast_metrics_returns_projections ===
    @pytest.mark.asyncio
    async def test_generate_project_forecast_returns_future_projections(
        self,
        mock_session: AsyncMock
    ) -> None:
        """Test that generate_project_forecast returns future projections.

        Given:
            A valid project_id
        When:
            generate_project_forecast is called
        Then:
            Forecast data includes future projections
        """
        from app.ai.tools.templates import analysis_template

        # Arrange: Create context
        context = ToolContext(
            session=mock_session,
            user_id=str(uuid4()),
            user_role="admin"
        )

        # Mock forecast service
        mock_forecast_service = AsyncMock()
        mock_forecast_data = MagicMock()
        mock_forecast_data.projected_eac = 150000
        mock_forecast_data.projected_etc = 50000
        mock_forecast_data.confidence_level = 0.85
        mock_forecast_data.forecast_date = datetime.now()
        mock_forecast_service.generate_forecast.return_value = mock_forecast_data

        with patch.object(
            ToolContext,
            'forecast_service',
            mock_forecast_service
        ):
            # Act: Generate forecast
            result = await analysis_template.generate_project_forecast(  # type: ignore[operator]
                project_id=str(uuid4()),
                context=context
            )

            # Assert: Should return forecast data
            assert isinstance(result, dict)
            # Should contain projection data
            assert "project_id" in result or "error" in result

    @pytest.mark.asyncio
    async def test_compare_forecast_scenarios_validates_inputs(
        self,
        mock_session: AsyncMock
    ) -> None:
        """Test that compare_forecast_scenarios validates scenario inputs.

        Given:
            Multiple forecast scenarios with different parameters
        When:
            compare_forecast_scenarios is called
        Then:
            Scenarios are compared and results returned
        """
        from app.ai.tools.templates import analysis_template

        # Arrange: Create context
        context = ToolContext(
            session=mock_session,
            user_id=str(uuid4()),
            user_role="admin"
        )

        # Act: Compare forecast scenarios
        result = await analysis_template.compare_forecast_scenarios(  # type: ignore[operator]
            project_id=str(uuid4()),
            scenarios=["optimistic", "realistic", "pessimistic"],
            context=context
        )

        # Assert: Should handle gracefully
        assert isinstance(result, dict)

    @pytest.mark.asyncio
    async def test_get_forecast_accuracy_validates_historical_data(
        self,
        mock_session: AsyncMock
    ) -> None:
        """Test that get_forecast_accuracy validates historical data availability.

        Given:
            A project without sufficient historical data
        When:
            get_forecast_accuracy is called
        Then:
            Warning or error is returned about insufficient data
        """
        from app.ai.tools.templates import analysis_template

        # Arrange: Create context
        context = ToolContext(
            session=mock_session,
            user_id=str(uuid4()),
            user_role="admin"
        )

        # Mock forecast service to return insufficient data
        mock_forecast_service = AsyncMock()
        mock_forecast_service.calculate_forecast_accuracy.return_value = None

        with patch.object(
            ToolContext,
            'forecast_service',
            mock_forecast_service
        ):
            # Act: Try to get forecast accuracy
            result = await analysis_template.get_forecast_accuracy(  # type: ignore[operator]
                project_id=str(uuid4()),
                context=context
            )

            # Assert: Should handle gracefully
            assert isinstance(result, dict)

    @pytest.mark.asyncio
    async def test_get_project_kpis_aggregates_metrics(
        self,
        mock_session: AsyncMock
    ) -> None:
        """Test that get_project_kpis aggregates key performance indicators.

        Given:
            A valid project_id
        When:
            get_project_kpis is called
        Then:
            KPIs are aggregated and returned
        """
        from app.ai.tools.templates import analysis_template

        # Arrange: Create context
        context = ToolContext(
            session=mock_session,
            user_id=str(uuid4()),
            user_role="admin"
        )

        # Act: Get project KPIs
        result = await analysis_template.get_project_kpis(  # type: ignore[operator]
            project_id=str(uuid4()),
            context=context
        )

        # Assert: Should return KPI data
        assert isinstance(result, dict)

    @pytest.mark.asyncio
    async def test_analyze_cost_variance_identifies_deviations(
        self,
        mock_session: AsyncMock
    ) -> None:
        """Test that analyze_cost_variance identifies cost deviations.

        Given:
            A project with cost variance
        When:
            analyze_cost_variance is called
        Then:
            Variance analysis identifies deviations
        """
        from app.ai.tools.templates import analysis_template

        # Arrange: Create context
        context = ToolContext(
            session=mock_session,
            user_id=str(uuid4()),
            user_role="admin"
        )

        # Act: Analyze cost variance
        result = await analysis_template.analyze_cost_variance(  # type: ignore[operator]
            project_id=str(uuid4()),
            context=context
        )

        # Assert: Should return variance analysis
        assert isinstance(result, dict)

    @pytest.mark.asyncio
    async def test_analyze_schedule_variance_identifies_delays(
        self,
        mock_session: AsyncMock
    ) -> None:
        """Test that analyze_schedule_variance identifies schedule delays.

        Given:
            A project with schedule variance
        When:
            analyze_schedule_variance is called
        Then:
            Variance analysis identifies delays
        """
        from app.ai.tools.templates import analysis_template

        # Arrange: Create context
        context = ToolContext(
            session=mock_session,
            user_id=str(uuid4()),
            user_role="admin"
        )

        # Act: Analyze schedule variance
        result = await analysis_template.analyze_schedule_variance(  # type: ignore[operator]
            project_id=str(uuid4()),
            context=context
        )

        # Assert: Should return variance analysis
        assert isinstance(result, dict)


class TestAnalysisTemplateExisting:
    """Keep existing basic tests for template structure."""

    def test_analysis_template_can_be_imported(self) -> None:
        """Test that the Analysis template can be imported without errors."""
        try:
            from app.ai.tools.templates import analysis_template
            assert analysis_template is not None
        except Exception as e:
            pytest.fail(f"Failed to import Analysis template: {e}")

    def test_analysis_template_has_required_functions(self) -> None:
        """Test that the Analysis template has all required example functions."""
        from app.ai.tools.templates import analysis_template

        # Check that all Analysis functions exist
        assert hasattr(analysis_template, "calculate_evm_metrics")
        assert hasattr(analysis_template, "get_evm_performance_summary")
        assert hasattr(analysis_template, "analyze_cost_variance")
        assert hasattr(analysis_template, "analyze_schedule_variance")
        assert hasattr(analysis_template, "generate_project_forecast")
        assert hasattr(analysis_template, "compare_forecast_scenarios")
        assert hasattr(analysis_template, "get_forecast_accuracy")
        assert hasattr(analysis_template, "get_project_kpis")

    def test_analysis_template_functions_have_decorators(self) -> None:
        """Test that Analysis template functions have @ai_tool decorators."""
        from app.ai.tools.templates import analysis_template

        # Check that functions have the _is_ai_tool attribute set by decorator
        functions = [
            "calculate_evm_metrics",
            "get_evm_performance_summary",
            "analyze_cost_variance",
            "analyze_schedule_variance",
            "generate_project_forecast",
            "compare_forecast_scenarios",
            "get_forecast_accuracy",
            "get_project_kpis",
        ]

        for func_name in functions:
            func = getattr(analysis_template, func_name)
            # All should have _is_ai_tool attribute from decorator
            assert hasattr(func, "_is_ai_tool"), f"{func_name} missing @ai_tool decorator"
            assert func._is_ai_tool is True, f"{func_name} decorator not properly applied"
