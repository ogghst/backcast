"""AI Tools Test Data Seeder.

Loads comprehensive test data for AI tools testing from ai_tools_test_data.json.
This seeder creates a complete project hierarchy with cost elements, forecasts,
cost registrations, and progress entries for testing all 13 AI tools.
"""

import asyncio
import json
import logging
from pathlib import Path
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.seed_context import seed_operation
from app.models.schemas.cost_element import CostElementCreate
from app.models.schemas.cost_registration import CostRegistrationCreate
from app.models.schemas.progress_entry import ProgressEntryCreate
from app.models.schemas.project import ProjectCreate
from app.models.schemas.wbs_element import WBSElementCreate
from app.services.cost_element_service import CostElementService
from app.services.cost_registration_service import CostRegistrationService
from app.services.progress_entry_service import ProgressEntryService
from app.services.project import ProjectService
from app.services.wbs_element_service import WBSElementService

logger = logging.getLogger(__name__)


class AIToolsTestDataSeeder:
    """Seeds comprehensive test data for AI tools testing."""

    def __init__(self, seed_dir: Path | None = None) -> None:
        """Initialize AI Tools Test Data Seeder.

        Args:
            seed_dir: Path to directory containing seed JSON files.
        """
        if seed_dir is None:
            backend_dir = Path(__file__).parent.parent.parent
            seed_dir = backend_dir / "seed"

        self.seed_dir = seed_dir
        logger.info(f"AI Tools Test Data Seeder initialized with: {self.seed_dir}")

    def load_test_data(self) -> dict[str, Any]:
        """Load the AI tools test data JSON file.

        Returns:
            Dictionary containing test data

        Raises:
            FileNotFoundError: If test data file doesn't exist
            json.JSONDecodeError: If file contains invalid JSON
        """
        file_path = self.seed_dir / "ai_tools_test_data.json"
        if not file_path.exists():
            raise FileNotFoundError(f"AI tools test data file not found: {file_path}")

        with open(file_path) as f:
            return json.load(f)

    async def seed_project(self, session: AsyncSession, data: dict[str, Any]) -> None:
        """Seed the test project.

        Args:
            session: Database session
            data: Test data dictionary
        """
        logger.info("Seeding AI Test Project...")
        project_data = data["project"]

        proj_service = ProjectService(session)

        # Check if project already exists
        existing = await proj_service.get_by_code(project_data["code"])
        if existing:
            logger.info(f"Project {project_data['code']} already exists, skipping")
            return

        from uuid import uuid4

        actor_id = uuid4()

        with seed_operation():
            proj_in = ProjectCreate(**project_data)
            await proj_service.create_project(proj_in, actor_id)
            logger.info(f"Created Project: {proj_in.code}")

    async def seed_wbes(self, session: AsyncSession, data: dict[str, Any]) -> None:
        """Seed the WBS Element hierarchy.

        Args:
            session: Database session
            data: Test data dictionary
        """
        logger.info("Seeding WBS Element hierarchy...")
        wbe_data_list = data["wbes"]

        wbs_element_service = WBSElementService(session)
        proj_service = ProjectService(session)

        from uuid import uuid4

        actor_id = uuid4()

        # Get the actual project ID from the database (by code)
        project = await proj_service.get_by_code(data["project"]["code"])
        if not project:
            raise ValueError(
                f"Project {data['project']['code']} not found. WBS Elements require a parent project."
            )

        actual_project_id = project.project_id

        # Sort by level to ensure parents exist before children
        wbe_data_list.sort(key=lambda x: x["level"])

        # Track generated IDs for parent references
        id_mapping: dict[str, UUID] = {}

        with seed_operation():
            for wbe_data in wbe_data_list:
                try:
                    # Check if WBS Element already exists by code (use actual project ID)
                    existing = await wbs_element_service.get_by_code(
                        wbe_data["code"], project_id=actual_project_id, branch="main"
                    )
                    if existing:
                        logger.debug(f"WBS Element {wbe_data['code']} exists, skipping")
                        # Store the existing ID for parent references
                        # Map old JSON key to new schema field
                        old_id_key = wbe_data.get("wbs_element_id") or wbe_data.get(
                            "wbe_id", ""
                        )
                        id_mapping[str(old_id_key)] = existing.wbs_element_id
                        continue

                    # Generate new UUID and store mapping
                    new_id = uuid4()
                    old_id_key = wbe_data.get("wbs_element_id") or wbe_data.get(
                        "wbe_id", ""
                    )
                    id_mapping[str(old_id_key)] = new_id

                    # Update data with new ID and remap old field names
                    wbe_data["wbs_element_id"] = str(new_id)
                    wbe_data.pop("wbe_id", None)

                    # Update project_id to the actual database ID
                    wbe_data["project_id"] = str(actual_project_id)

                    # Remap parent_wbe_id -> parent_wbs_element_id if it exists
                    if wbe_data.get("parent_wbs_element_id"):
                        wbe_data["parent_wbs_element_id"] = str(
                            id_mapping[wbe_data["parent_wbs_element_id"]]
                        )
                    elif wbe_data.get("parent_wbe_id"):
                        wbe_data["parent_wbs_element_id"] = str(
                            id_mapping[wbe_data["parent_wbe_id"]]
                        )
                        wbe_data.pop("parent_wbe_id", None)

                    wbs_element_in = WBSElementCreate(**wbe_data)
                    await wbs_element_service.create_wbe(wbs_element_in, actor_id)
                    logger.info(f"Created WBS Element: {wbs_element_in.code}")

                except Exception as e:
                    logger.error(
                        f"Failed to seed WBS Element {wbe_data.get('code')}: {e}"
                    )
                    raise

    async def seed_cost_elements_and_forecasts(
        self, session: AsyncSession, data: dict[str, Any]
    ) -> None:
        """Seed cost elements and their associated forecasts.

        Args:
            session: Database session
            data: Test data dictionary
        """
        logger.info("Seeding cost elements and forecasts...")

        from uuid import uuid4

        from sqlalchemy import select

        from app.models.domain.cost_element import CostElement
        from app.services.wbs_element_service import WBSElementService

        actor_id = uuid4()

        # Build a mapping of WBS Element codes to IDs
        wbs_element_service = WBSElementService(session)
        proj_service = ProjectService(session)
        wbs_code_to_id: dict[str, UUID] = {}

        # Get the actual project ID from the database (by code)
        project = await proj_service.get_by_code(data["project"]["code"])
        if not project:
            raise ValueError(
                f"Project {data['project']['code']} not found. Cost elements require a parent project."
            )

        actual_project_id = project.project_id

        # Load all WBS Elements to build code->ID mapping (use actual project ID)
        for wbs_data in data["wbes"]:
            wbs_elem = await wbs_element_service.get_by_code(
                wbs_data["code"], actual_project_id, branch="main"
            )
            if wbs_elem:
                wbs_code_to_id[wbs_data["code"]] = wbs_elem.wbs_element_id
                logger.debug(
                    f"Mapped WBS Element {wbs_data['code']} -> {wbs_elem.wbs_element_id}"
                )
            else:
                logger.warning(f"WBS Element {wbs_data['code']} not found in database")

        # Build a set of existing cost element codes
        # NOTE: CostElement no longer has code/branch columns (refactored to EOC).
        # This seeder needs rework for the new WorkPackage-based model.
        stmt = select(CostElement.code).where(CostElement.branch == "main")  # type: ignore[attr-defined]
        result = await session.execute(stmt)
        existing_codes = set(result.scalars().all())

        # Need to load fresh data for each iteration since we're modifying it
        # Also load fresh WBS Element data since the WBS Element seeder modified it
        original_data = self.load_test_data()
        ce_data_list = original_data["cost_elements"]
        fresh_wbs_data_list = original_data["wbes"]  # Use fresh WBS data for ID mapping

        ce_service = CostElementService(session)

        with seed_operation():
            for ce_data in ce_data_list:
                try:
                    # Check if cost element already exists by code
                    if ce_data["code"] in existing_codes:
                        logger.debug(
                            f"Cost Element {ce_data['code']} already exists, skipping"
                        )
                        continue

                    # Extract forecast data before creating cost element
                    forecast_data = ce_data.pop("forecast", None)

                    # Generate new UUID for cost element
                    new_ce_id = uuid4()
                    ce_data["cost_element_id"]
                    ce_data["cost_element_id"] = str(new_ce_id)

                    # Update WBS Element ID reference using the mapping
                    # Look up the WBS Element by its original ID in the test data
                    original_wbs_id = ce_data.get("wbs_element_id") or ce_data.get(
                        "wbe_id", ""
                    )
                    for wbs_data in fresh_wbs_data_list:
                        wbs_id_key = wbs_data.get("wbs_element_id") or wbs_data.get(
                            "wbe_id", ""
                        )
                        if str(wbs_id_key) == str(original_wbs_id):
                            new_wbs_id = wbs_code_to_id.get(wbs_data["code"])
                            if new_wbs_id:
                                ce_data["work_package_id"] = str(new_wbs_id)
                                ce_data.pop("wbe_id", None)
                                logger.debug(
                                    f"Mapped WBS Element ID for {ce_data['code']}: {original_wbs_id} -> {new_wbs_id}"
                                )
                            else:
                                logger.warning(
                                    f"WBS Element {wbs_data['code']} not found in mapping"
                                )
                            break
                    else:
                        logger.warning(
                            f"Could not find WBS Element with ID {original_wbs_id} in test data"
                        )

                    ce_in = CostElementCreate(**ce_data)
                    created_ce = await ce_service.create_cost_element(ce_in, actor_id)
                    logger.info(f"Created Cost Element: {ce_in.cost_element_id}")

                    # Create forecast if provided
                    if forecast_data:
                        # Generate new UUID for forecast
                        new_forecast_id = uuid4()
                        forecast_data["forecast_id"] = str(new_forecast_id)
                        await self._create_forecast(
                            session, created_ce.cost_element_id, forecast_data, actor_id
                        )

                except Exception as e:
                    # Check if it's an overlap error (version already exists)
                    if "overlap" in str(e).lower() or "overlapping" in str(e).lower():
                        logger.debug(
                            f"Cost Element {ce_data.get('code')} already exists (overlap), skipping"
                        )
                        continue
                    logger.error(
                        f"Failed to seed Cost Element {ce_data.get('code')}: {e}"
                    )
                    raise

    async def _create_forecast(
        self,
        session: AsyncSession,
        cost_element_id: UUID,
        forecast_data: dict[str, Any],
        actor_id: UUID,
    ) -> None:
        """Create a forecast for a cost element and link it.

        Args:
            session: Database session
            cost_element_id: ID of the cost element
            forecast_data: Forecast data dictionary
            actor_id: ID of the user creating the forecast
        """
        from datetime import UTC, datetime

        from sqlalchemy import update

        from app.models.domain.cost_element import CostElement
        from app.models.domain.forecast import Forecast

        with seed_operation():
            # Create forecast
            forecast = Forecast(
                forecast_id=UUID(forecast_data["forecast_id"]),
                eac_amount=forecast_data["eac_amount"],
                basis_of_estimate=forecast_data["basis_of_estimate"],
                created_by=actor_id,
                branch="main",
                valid_time=[datetime.now(UTC), None],
                transaction_time=[datetime.now(UTC), None],
            )
            session.add(forecast)
            await session.flush()

            # Update cost element with forecast_id
            # NOTE: CostElement no longer has branch/forecast_id (refactored to EOC).
            stmt = (
                update(CostElement)
                .where(CostElement.cost_element_id == cost_element_id)
                .where(CostElement.branch == "main")  # type: ignore[attr-defined]
                .values(forecast_id=forecast.forecast_id)
            )
            await session.execute(stmt)
            await session.flush()

            logger.debug(
                f"Created forecast for cost element {cost_element_id}: {forecast_data['eac_amount']}"
            )

    async def seed_cost_registrations(
        self, session: AsyncSession, data: dict[str, Any]
    ) -> None:
        """Seed cost registrations.

        Args:
            session: Database session
            data: Test data dictionary
        """
        logger.info("Seeding cost registrations...")
        cr_data_list = data["cost_registrations"]

        cr_service = CostRegistrationService(session)

        from uuid import uuid4

        from sqlalchemy import select

        from app.models.domain.cost_element import CostElement
        from app.models.domain.cost_registration import CostRegistration

        actor_id = uuid4()

        # Build a mapping of cost element IDs by querying the database
        # NOTE: CostElement no longer has branch/code (refactored to EOC).
        stmt = select(CostElement).where(CostElement.branch == "main")  # type: ignore[attr-defined]
        result = await session.execute(stmt)
        cost_elements = result.scalars().all()

        # Build code -> ID mapping
        ce_code_to_id: dict[str, UUID] = {
            getattr(ce, "code", str(ce.cost_element_id)): ce.cost_element_id
            for ce in cost_elements
        }

        # Build original ID -> code mapping from test data
        ce_id_to_code: dict[str, str] = {
            ce_data["cost_element_id"]: ce_data["code"]
            for ce_data in data["cost_elements"]
        }

        # Get existing cost registrations to avoid duplicates
        # Build mapping of cost_element_id -> code
        ce_id_to_code_map: dict[UUID, str] = {
            ce.cost_element_id: getattr(ce, "code", str(ce.cost_element_id))
            for ce in cost_elements
        }

        # Query all cost registrations
        stmt_cr = select(
            CostRegistration.cost_element_id,
            CostRegistration.registration_date,
            CostRegistration.amount,
            CostRegistration.description,
        )
        result_cr = await session.execute(stmt_cr)
        # Use a simpler key: code + amount + description (ignore exact timestamp due to timezone issues)
        existing_regs = {
            (
                ce_id_to_code_map.get(r.cost_element_id, ""),
                float(r.amount),
                r.description,
            )
            for r in result_cr.all()
        }
        logger.debug(f"Found {len(existing_regs)} existing cost registrations")

        with seed_operation():
            for cr_data in cr_data_list:
                try:
                    # Look up cost element ID by mapping through code
                    original_ce_id = cr_data["cost_element_id"]
                    ce_code = ce_id_to_code.get(str(original_ce_id))
                    cost_element_id = ce_code_to_id.get(ce_code) if ce_code else None

                    if not cost_element_id:
                        logger.warning(
                            f"Could not find cost element for registration: {cr_data.get('description')}"
                        )
                        continue

                    # Check if this registration already exists
                    # Use cost element code + amount + description (ignore exact timestamp due to timezone issues)
                    ce_code = ce_id_to_code.get(str(original_ce_id))
                    reg_key = (ce_code, cr_data["amount"], cr_data["description"])
                    if reg_key in existing_regs:
                        logger.debug(
                            f"Cost Registration already exists: {ce_code} - {cr_data.get('description')[:50]}"
                        )
                        continue

                    # Generate new UUID for the registration
                    cr_data["cost_registration_id"] = str(uuid4())
                    cr_data["cost_element_id"] = str(cost_element_id)

                    cr_in = CostRegistrationCreate(**cr_data)
                    await cr_service.create_cost_registration(
                        cr_in, actor_id, branch="main"
                    )
                    logger.info(
                        f"Created Cost Registration: {cr_in.amount} for {cr_in.cost_element_id}"
                    )

                except Exception as e:
                    logger.error(
                        f"Failed to seed Cost Registration {cr_data.get('description')}: {e}"
                    )
                    raise

    async def seed_progress_entries(
        self, session: AsyncSession, data: dict[str, Any]
    ) -> None:
        """Seed progress entries.

        Args:
            session: Database session
            data: Test data dictionary
        """
        logger.info("Seeding progress entries...")
        pe_data_list = data["progress_entries"]

        pe_service = ProgressEntryService(session)

        from uuid import uuid4

        from sqlalchemy import select

        from app.models.domain.cost_element import CostElement
        from app.models.domain.progress_entry import ProgressEntry

        actor_id = uuid4()

        # Build a mapping of cost element IDs by querying the database
        # NOTE: CostElement no longer has branch/code (refactored to EOC).
        # ProgressEntry now uses work_package_id instead of cost_element_id.
        stmt = select(CostElement).where(CostElement.branch == "main")  # type: ignore[attr-defined]
        result = await session.execute(stmt)
        cost_elements = result.scalars().all()

        # Build code -> ID mapping
        ce_code_to_id: dict[str, UUID] = {
            getattr(ce, "code", str(ce.cost_element_id)): ce.cost_element_id
            for ce in cost_elements
        }

        # Build original ID -> code mapping from test data
        ce_id_to_code: dict[str, str] = {
            ce_data["cost_element_id"]: ce_data["code"]
            for ce_data in data["cost_elements"]
        }

        # Get existing progress entries to avoid duplicates
        # Build mapping of cost_element_id -> code
        ce_id_to_code_map: dict[UUID, str] = {
            ce.cost_element_id: getattr(ce, "code", str(ce.cost_element_id))
            for ce in cost_elements
        }

        # Query all progress entries
        stmt_pe = select(
            ProgressEntry.work_package_id,
            ProgressEntry.progress_percentage,
            ProgressEntry.notes,
        )
        result_pe = await session.execute(stmt_pe)
        existing_entries: set[tuple[str | None, float, str | None]] = {
            (
                ce_id_to_code_map.get(e.work_package_id, ""),
                float(e.progress_percentage),
                e.notes,
            )
            for e in result_pe.all()
        }

        with seed_operation():
            for pe_data in pe_data_list:
                try:
                    # Look up cost element ID by mapping through code
                    original_ce_id = pe_data["cost_element_id"]
                    ce_code = ce_id_to_code.get(str(original_ce_id))
                    cost_element_id = ce_code_to_id.get(ce_code) if ce_code else None

                    if not cost_element_id:
                        logger.warning(
                            f"Could not find cost element for progress entry: {pe_data.get('notes')}"
                        )
                        continue

                    # Check if this progress entry already exists
                    # Use cost element code instead of ID for stability across runs
                    ce_code = ce_id_to_code.get(str(original_ce_id))
                    entry_key = (
                        ce_code,
                        pe_data["progress_percentage"],
                        pe_data["notes"],
                    )
                    if entry_key in existing_entries:
                        logger.debug(
                            f"Progress Entry already exists: {pe_data.get('notes')}"
                        )
                        continue

                    # Generate new UUID for the progress entry
                    pe_data["progress_entry_id"] = str(uuid4())
                    # Map old cost_element_id to work_package_id
                    pe_data["work_package_id"] = pe_data.pop(
                        "cost_element_id", str(cost_element_id)
                    )

                    pe_in = ProgressEntryCreate(**pe_data)
                    await pe_service.create(actor_id=actor_id, progress_in=pe_in)
                    logger.info(
                        f"Created Progress Entry: {pe_in.progress_percentage}% for {pe_in.work_package_id}"
                    )

                except Exception as e:
                    logger.error(
                        f"Failed to seed Progress Entry {pe_data.get('notes')}: {e}"
                    )
                    raise

    async def seed_all(self, session: AsyncSession) -> None:
        """Execute all seeding operations.

        Args:
            session: Database session
        """
        logger.info("=== Starting AI Tools Test Data seeding ===")

        try:
            # Load test data
            data = self.load_test_data()
            logger.info(
                f"Loaded test data for: {data['metadata']['project_name']} ({data['metadata']['project_code']})"
            )

            # Seed in correct order respecting foreign keys
            await self.seed_project(session, data)
            await asyncio.sleep(0.5)  # Small delay to prevent timestamp overlap

            await self.seed_wbes(session, data)
            await asyncio.sleep(0.5)

            await self.seed_cost_elements_and_forecasts(session, data)
            await asyncio.sleep(0.5)

            await self.seed_cost_registrations(session, data)
            await asyncio.sleep(0.5)

            await self.seed_progress_entries(session, data)

            # Commit all changes
            await session.commit()
            logger.info("=== AI Tools Test Data seeding completed successfully ===")

            # Log expected query results for verification
            logger.info("\n=== Expected Query Results ===")
            for query_name, query_data in data["expected_query_results"].items():
                logger.info(f"\n{query_name}:")
                logger.info(f"  Query: {query_data['query']}")
                logger.info(
                    f"  Expected: {json.dumps(query_data['expected_result'], indent=2)}"
                )

        except Exception as e:
            logger.error(f"AI Tools Test Data seeding failed: {e}")
            await session.rollback()
            raise
