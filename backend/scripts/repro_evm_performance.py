import asyncio
import logging
import time
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

from app.core.versioning.enums import BranchMode
from app.db.session import async_session_maker
from app.models.schemas.cost_registration import CostRegistrationCreate
from app.models.schemas.evm import EntityType
from app.models.schemas.progress_entry import ProgressEntryCreate
from app.services.cost_element_service import CostElementService
from app.services.cost_registration_service import CostRegistrationService
from app.services.evm_service import EVMService
from app.services.forecast_service import ForecastService
from app.services.progress_entry_service import ProgressEntryService
from app.services.project import ProjectService
from app.services.schedule_baseline_service import ScheduleBaselineService
from app.services.wbe import WBEService

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

from app.models.domain.cost_element_type import CostElementType  # noqa: E402
from app.models.domain.department import Department  # noqa: E402


async def setup_test_data(session):
    """Sets up a project with rigorous testing data:
    - 1 Project
    - 5 WBEs
    - 10 Cost Elements per WBE (50 total)
    - Full EVM data (Baselines, Actuals, Progress, Forecasts) for each CE
    """
    logger.info("Setting up test data...")
    user_id = uuid4()

    # Initialize Services
    project_service = ProjectService(session)
    wbe_service = WBEService(session)
    ce_service = CostElementService(session)
    sb_service = ScheduleBaselineService(session)
    cr_service = CostRegistrationService(session)
    pe_service = ProgressEntryService(session)
    f_service = ForecastService(session)

    # 0. Create Reference Data (Department & Cost Element Type)
    dept_id = uuid4()
    dept = Department(
        department_id=dept_id,
        name="Test Department",
        code=f"DEPT-{dept_id}",
        description="Test Dept",
        created_by=user_id
    )
    session.add(dept)

    cet_id = uuid4()
    cet = CostElementType(
        cost_element_type_id=cet_id,
        department_id=dept_id,
        name="Test Type",
        code=f"CET-{cet_id}",
        description="Test Type",
        created_by=user_id
    )
    session.add(cet)
    await session.flush()

    logger.info(f"Created Cost Element Type: {cet_id}")

    # 1. Create Project
    project_id = uuid4()
    await project_service.create_root(
        root_id=project_id,
        actor_id=user_id,
        name=f"Performance Test Project {project_id}",
        code=f"PRJ-{project_id}",
        description="Auto-generated for EVM perf test",
        start_date=datetime.now(UTC),
        end_date=datetime.now(UTC) + timedelta(days=365)
    )
    logger.info(f"Created Project: {project_id}")

    cost_elements = []

    # 2. Create WBEs
    for i in range(5):
        wbe_id = uuid4()
        await wbe_service.create_root(
            root_id=wbe_id,
            actor_id=user_id,
            project_id=project_id,
            name=f"WBE {i}",
            code=f"WBE-{i}"
        )

        # 3. Create Cost Elements (10 per WBE)
        for j in range(10):
            ce_id = uuid4()
            await ce_service.create_root(
                root_id=ce_id,
                actor_id=user_id,
                wbe_id=wbe_id,
                name=f"Cost Element {i}-{j}",
                code=f"CE-{i}-{j}",
                budget_amount=Decimal("10000.00"),
                cost_element_type_id=cet_id  # Use ID, not string
            )
            cost_elements.append(ce_id)

    # 4. Create Related Data for ALL Cost Elements
    start_date = datetime.now(UTC) - timedelta(days=30)
    end_date = datetime.now(UTC) + timedelta(days=30)

    for ce_id in cost_elements:
        # Schedule Baseline
        await sb_service.create_root(
            root_id=uuid4(),
            actor_id=user_id,
            cost_element_id=ce_id,
            name="Baseline",
            start_date=start_date,
            end_date=end_date,
            progression_type="LINEAR"
        )

        # Cost Registration (Actual Cost)
        await cr_service.create_cost_registration(
            registration_in=CostRegistrationCreate(
                cost_element_id=ce_id,
                amount=Decimal("5000.00"),
                registration_date=datetime.now(UTC),
                reference="INV-001",
                description="Test Cost"
            ),
            actor_id=user_id
        )

        # Progress Entry
        await pe_service.create_progress_entry(
            progress_in=ProgressEntryCreate(
                progress_entry_id=uuid4(),
                cost_element_id=ce_id,
                progress_percentage=Decimal("50.0"),
                report_date=datetime.now(UTC),
                notes="Halfway done"
            ),
            actor_id=user_id
        )

        # Forecast
        await f_service.create_for_cost_element(
            cost_element_id=ce_id,
            actor_id=user_id,
            eac_amount=Decimal("11000.00"),
            basis_of_estimate="Initial forecast"
        )

    logger.info(f"Created {len(cost_elements)} Cost Elements with full data.")
    return project_id

async def main():
    async with async_session_maker() as session:
        # Create fresh data
        project_id = await setup_test_data(session)
        await session.commit()

        logger.info(f"Testing EVM performance for project: {project_id}")

        # Re-initialize EVM Service with new session
        evm_service = EVMService(session)

        # Measure time
        start_time = time.time()

        logger.info("Starting calculation...")
        try:
            # First run (cold?)
            metrics = await evm_service.calculate_evm_metrics_batch(
                entity_type=EntityType.PROJECT,
                entity_ids=[project_id],
                control_date=datetime.now(UTC),
                branch="main",
                branch_mode=BranchMode.MERGE
            )

            elapsed = time.time() - start_time
            logger.info(f"Calculation took {elapsed:.4f} seconds")
            logger.info(f"Metrics: BAC={metrics.bac}, CPI={metrics.cpi}, SPI={metrics.spi}")

            if elapsed < 1.0:
                logger.info("SUCCESS: Performance goal met (<1.0s)!")
            else:
                logger.warning(f"FAILURE: Performance goal not met ({elapsed:.4f}s > 1.0s)")

        except Exception as e:
            logger.error(f"Error during calculation: {e}", exc_info=True)

if __name__ == "__main__":
    asyncio.run(main())
