"""Test impact analysis API response."""
import asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import async_session_maker
from app.models.domain.change_order import ChangeOrder
from app.services.impact_analysis_service import ImpactAnalysisService
from app.core.versioning.enums import BranchMode


async def test_impact_analysis():
    """Test impact analysis."""
    async with async_session_maker() as session:
        # Get CO-2026-001
        co_stmt = select(ChangeOrder).where(ChangeOrder.code == "CO-2026-001")
        co_result = await session.execute(co_stmt)
        co = co_result.scalar_one_or_none()

        if not co:
            print("Change Order CO-2026-001 not found")
            return

        print(f"Testing CO: {co.code}")
        print(f"Project ID: {co.project_id}")
        print()

        # Test with MERGE mode
        print("=" * 60)
        print("TESTING MERGE MODE")
        print("=" * 60)
        service = ImpactAnalysisService(session)
        analysis = await service.analyze_impact(
            change_order_id=co.change_order_id,
            branch_name="BR-CO-2026-001",
            branch_mode=BranchMode.MERGE,
        )

        print(f"\nBAC (Budget at Completion):")
        print(f"  Main: {analysis.kpi_scorecard.bac.main_value}")
        print(f"  Change: {analysis.kpi_scorecard.bac.change_value}")
        print(f"  Merged: {analysis.kpi_scorecard.bac.merged_value}")
        print(f"  Delta: {analysis.kpi_scorecard.bac.delta}")
        print()

        print(f"Budget Delta:")
        print(f"  Main: {analysis.kpi_scorecard.budget_delta.main_value}")
        print(f"  Change: {analysis.kpi_scorecard.budget_delta.change_value}")
        print(f"  Merged: {analysis.kpi_scorecard.budget_delta.merged_value}")
        print(f"  Delta: {analysis.kpi_scorecard.budget_delta.delta}")
        print()

        # Test with STRICT mode
        print("=" * 60)
        print("TESTING STRICT MODE")
        print("=" * 60)
        analysis_strict = await service.analyze_impact(
            change_order_id=co.change_order_id,
            branch_name="BR-CO-2026-001",
            branch_mode=BranchMode.STRICT,
        )

        print(f"\nBAC (Budget at Completion):")
        print(f"  Main: {analysis_strict.kpi_scorecard.bac.main_value}")
        print(f"  Change: {analysis_strict.kpi_scorecard.bac.change_value}")
        print(f"  Merged: {analysis_strict.kpi_scorecard.bac.merged_value}")
        print(f"  Delta: {analysis_strict.kpi_scorecard.bac.delta}")
        print()


if __name__ == "__main__":
    asyncio.run(test_impact_analysis())
