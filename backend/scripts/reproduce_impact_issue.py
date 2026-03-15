import asyncio
import logging
from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

from sqlalchemy import select

from app.db.session import async_session_maker
from app.models.domain.wbe import WBE
from app.models.schemas.change_order import ChangeOrderCreate
from app.services.change_order_service import ChangeOrderService
from app.services.impact_analysis_service import ImpactAnalysisService
from app.services.project import ProjectService
from app.services.wbe import WBEService

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def main():
    logger.info("Starting reproduction script...")
    async with async_session_maker() as session:
        # Initialize Services
        project_service = ProjectService(session)
        wbe_service = WBEService(session)
        co_service = ChangeOrderService(session)
        impact_service = ImpactAnalysisService(session)

        user_id = uuid4()

        # 1. Create Project
        project_id = uuid4()
        await project_service.create_root(
            root_id=project_id,
            actor_id=user_id,
            name=f"Impact Test Project {project_id}",
            code=f"PRJ-{project_id}",
            description="Test for Impact Analysis",
            start_date=datetime.now(UTC),
        )
        logger.info(f"Created Project: {project_id}")

        # 2. Create WBEs on main branch
        wbe_id = uuid4()
        await wbe_service.create_root(
            root_id=wbe_id,
            actor_id=user_id,
            project_id=project_id,
            name="Main WBE",
            code="1.0",
            budget_allocation=Decimal("100000.00"),
            branch="main",
        )
        logger.info(f"Created WBE {wbe_id} on main with budget 100,000.00")

        await session.commit()

        # Verify main branch BAC
        stmt = select(WBE).where(WBE.project_id == project_id, WBE.branch == "main")
        result = await session.execute(stmt)
        wbes = result.scalars().all()
        logger.info(f"Found {len(wbes)} WBEs on main branch")

        # 3. Create Change Order
        co_code = f"CO-{uuid4().hex[:8]}"
        logger.info(f"Creating Change Order {co_code}...")

        co_in = ChangeOrderCreate(
            project_id=project_id,
            code=co_code,
            title="Test Change Order",
            description="Testing impact analysis",
            control_date=datetime.now(UTC),
        )

        co = await co_service.create_change_order(co_in, actor_id=user_id)
        logger.info(
            f"Created Change Order {co.change_order_id} on branch {co.branch_name}"
        )

        # 4. Run Impact Analysis
        logger.info("Running Impact Analysis...")
        try:
            impact = await impact_service.analyze_impact(
                change_order_id=co.change_order_id,
                branch_name=co.branch_name,
                include_evm_metrics=False,
            )

            # 5. Check Results
            scorecard = impact.kpi_scorecard
            logger.info("--- IMPACT ANALYSIS RESULTS ---")
            logger.info(f"Main BAC: {scorecard.bac.main_value}")
            logger.info(f"Change BAC: {scorecard.bac.change_value}")
            logger.info(f"Budget Delta: {scorecard.budget_delta.delta}")
            logger.info(
                f"Budget Delta Percent: {scorecard.budget_delta.delta_percent}%"
            )

            if scorecard.bac.change_value == Decimal("0"):
                logger.error("BUG CONFIRMED: Change BAC is 0!")
            elif scorecard.bac.change_value == scorecard.bac.main_value:
                logger.info("Change BAC matches Main BAC (Expected for no changes)")
            else:
                logger.info(f"Change BAC is diff: {scorecard.bac.change_value}")

        except Exception as e:
            logger.error(f"Analysis Failed: {e}", exc_info=True)


if __name__ == "__main__":
    asyncio.run(main())
