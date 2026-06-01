"""AI Tools Test Data Seeder.

Loads comprehensive test data for AI tools testing from ai_tools_test_data.json.
This seeder creates a complete project hierarchy with organizational units, users,
cost element types, cost event types, cost elements, forecasts, cost registrations,
progress entries, cost events, and change orders for testing all AI tools.
"""

import asyncio
import json
import logging
from pathlib import Path
from typing import Any
from uuid import UUID

from sqlalchemy import select as sa_select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.seed_context import seed_operation
from app.models.domain.organizational_unit import OrganizationalUnit
from app.models.schemas.change_order import ChangeOrderCreate
from app.models.schemas.control_account import ControlAccountCreate
from app.models.schemas.cost_element import CostElementCreate
from app.models.schemas.cost_element_type import CostElementTypeCreate
from app.models.schemas.cost_event import CostEventCreate
from app.models.schemas.cost_event_type import CostEventTypeCreate
from app.models.schemas.cost_registration import CostRegistrationCreate
from app.models.schemas.progress_entry import ProgressEntryCreate
from app.models.schemas.project import ProjectCreate
from app.models.schemas.user import UserRegister
from app.models.schemas.wbs_element import WBSElementCreate
from app.models.schemas.work_package import WorkPackageCreate
from app.services.change_order_service import ChangeOrderService
from app.services.control_account_service import ControlAccountService
from app.services.cost_element_service import CostElementService
from app.services.cost_element_type_service import CostElementTypeService
from app.services.cost_event_service import CostEventService
from app.services.cost_event_type_service import CostEventTypeService
from app.services.cost_registration_service import CostRegistrationService
from app.services.organizational_unit_service import OrganizationalUnitService
from app.services.progress_entry_service import ProgressEntryService
from app.services.project import ProjectService
from app.services.user import UserService
from app.services.wbs_element_service import WBSElementService
from app.services.work_package_service import WorkPackageService

logger = logging.getLogger(__name__)


class AIToolsTestDataSeeder:
    """Seeds comprehensive test data for AI tools testing."""

    def __init__(self, seed_dir: Path | None = None) -> None:
        if seed_dir is None:
            backend_dir = Path(__file__).parent.parent.parent
            seed_dir = backend_dir / "seed"

        self.seed_dir = seed_dir
        self.wbs_id_mapping: dict[str, UUID] = {}  # original JSON id -> new DB id
        self.wbs_id_reverse: dict[UUID, str] = {}  # new DB id -> original JSON id
        self.wp_id_mapping: dict[str, UUID] = {}
        self.ce_id_mapping: dict[str, UUID | None] = {}
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

    # ------------------------------------------------------------------
    # Organizational Units
    # ------------------------------------------------------------------

    async def seed_organizational_units(
        self, session: AsyncSession, data: dict[str, Any]
    ) -> None:
        """Seed organizational units (hierarchical, branchable)."""
        logger.info("Seeding Organizational Units...")
        units_data = data.get("organizational_units", [])
        if not units_data:
            logger.warning("No organizational_units in seed data, skipping")
            return

        from uuid import uuid4

        ou_service = OrganizationalUnitService(session)
        actor_id = uuid4()

        # Sort so parents come before children (by absence/presence of parent_unit_id)
        units_data_sorted = sorted(
            units_data, key=lambda u: u.get("parent_unit_id") is not None
        )

        with seed_operation():
            for unit_data in units_data_sorted:
                code = unit_data["code"]
                existing = await ou_service.get_by_code(code)
                if existing:
                    logger.debug(f"OrganizationalUnit {code} exists, skipping")
                    continue

                root_id = UUID(unit_data["organizational_unit_id"])
                control_date = unit_data.get("control_date")
                parent_unit_id = unit_data.get("parent_unit_id")

                await ou_service.create_root(
                    root_id=root_id,
                    actor_id=actor_id,
                    control_date=control_date,
                    branch="main",
                    code=code,
                    name=unit_data["name"],
                    parent_unit_id=UUID(parent_unit_id) if parent_unit_id else None,
                    is_active=unit_data.get("is_active", True),
                    description=unit_data.get("description"),
                )
                logger.info(f"Created OrganizationalUnit: {code}")

    # ------------------------------------------------------------------
    # Users
    # ------------------------------------------------------------------

    async def seed_users(self, session: AsyncSession, data: dict[str, Any]) -> None:
        """Seed users with role assignments."""
        logger.info("Seeding Users...")
        users_data = data.get("users", [])
        if not users_data:
            logger.warning("No users in seed data, skipping")
            return

        from uuid import uuid4

        user_service = UserService(session)
        actor_id = uuid4()

        with seed_operation():
            for user_data in users_data:
                email = user_data["email"]
                # Check by email (current version)
                existing = await user_service.get_by_email(email)
                if existing:
                    logger.debug(f"User {email} exists, skipping")
                    continue

                user_in = UserRegister(**user_data)
                await user_service.create_user(user_in, actor_id)
                logger.info(
                    f"Created User: {email} ({user_data.get('role', 'viewer')})"
                )

    # ------------------------------------------------------------------
    # Cost Element Types
    # ------------------------------------------------------------------

    async def seed_cost_element_types(
        self, session: AsyncSession, data: dict[str, Any]
    ) -> None:
        """Seed cost element types (versionable, not branchable)."""
        logger.info("Seeding Cost Element Types...")
        types_data = data.get("cost_element_types", [])
        if not types_data:
            logger.warning("No cost_element_types in seed data, skipping")
            return

        from uuid import uuid4

        from sqlalchemy import select

        from app.core.temporal_queries import is_current_version
        from app.models.domain.cost_element_type import CostElementType

        cet_service = CostElementTypeService(session)
        actor_id = uuid4()

        with seed_operation():
            for type_data in types_data:
                code = type_data["code"]
                # Check if already exists by code
                stmt = (
                    select(CostElementType)
                    .where(
                        CostElementType.code == code,
                        is_current_version(
                            CostElementType.valid_time, CostElementType.deleted_at
                        ),
                    )
                    .limit(1)
                )
                result = await session.execute(stmt)
                if result.scalar_one_or_none():
                    logger.debug(f"CostElementType {code} exists, skipping")
                    continue

                type_in = CostElementTypeCreate(**type_data)
                await cet_service.create(type_in, actor_id)
                logger.info(f"Created CostElementType: {code}")

    # ------------------------------------------------------------------
    # Cost Event Types
    # ------------------------------------------------------------------

    async def seed_cost_event_types(
        self, session: AsyncSession, data: dict[str, Any]
    ) -> None:
        """Seed cost event types (versionable, not branchable)."""
        logger.info("Seeding Cost Event Types...")
        types_data = data.get("cost_event_types", [])
        if not types_data:
            logger.warning("No cost_event_types in seed data, skipping")
            return

        from uuid import uuid4

        from sqlalchemy import select

        from app.core.temporal_queries import is_current_version
        from app.models.domain.cost_event_type import CostEventType

        cevt_service = CostEventTypeService(session)
        actor_id = uuid4()

        with seed_operation():
            for type_data in types_data:
                code = type_data["code"]
                # Check if already exists by code
                stmt = (
                    select(CostEventType)
                    .where(
                        CostEventType.code == code,
                        is_current_version(
                            CostEventType.valid_time, CostEventType.deleted_at
                        ),
                    )
                    .limit(1)
                )
                result = await session.execute(stmt)
                if result.scalar_one_or_none():
                    logger.debug(f"CostEventType {code} exists, skipping")
                    continue

                type_in = CostEventTypeCreate(**type_data)
                await cevt_service.create(type_in, actor_id)
                logger.info(f"Created CostEventType: {code}")

    # ------------------------------------------------------------------
    # Project
    # ------------------------------------------------------------------

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

    # ------------------------------------------------------------------
    # WBS Elements
    # ------------------------------------------------------------------

    async def seed_wbs_elements(
        self, session: AsyncSession, data: dict[str, Any]
    ) -> None:
        """Seed the WBS Element hierarchy.

        Args:
            session: Database session
            data: Test data dictionary
        """
        logger.info("Seeding WBS Element hierarchy...")
        wbs_data_list = data["wbs_elements"]

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
        wbs_data_list.sort(key=lambda x: x["level"])

        with seed_operation():
            for wbs_data in wbs_data_list:
                try:
                    existing = await wbs_element_service.get_by_code(
                        wbs_data["code"], project_id=actual_project_id, branch="main"
                    )
                    if existing:
                        logger.debug(f"WBS Element {wbs_data['code']} exists, skipping")
                        old_id_key = wbs_data.get("wbs_element_id", "")
                        self.wbs_id_mapping[str(old_id_key)] = existing.wbs_element_id
                        self.wbs_id_reverse[existing.wbs_element_id] = str(old_id_key)
                        continue

                    new_id = uuid4()
                    old_id_key = wbs_data.get("wbs_element_id", "")
                    self.wbs_id_mapping[str(old_id_key)] = new_id
                    self.wbs_id_reverse[new_id] = str(old_id_key)

                    # Update data with new ID
                    wbs_data["wbs_element_id"] = str(new_id)

                    # Update project_id to the actual database ID
                    wbs_data["project_id"] = str(actual_project_id)

                    # Remap parent_wbs_element_id if it exists
                    if wbs_data.get("parent_wbs_element_id"):
                        wbs_data["parent_wbs_element_id"] = str(
                            self.wbs_id_mapping[wbs_data["parent_wbs_element_id"]]
                        )

                    wbs_element_in = WBSElementCreate(**wbs_data)
                    await wbs_element_service.create_wbe(wbs_element_in, actor_id)
                    logger.info(f"Created WBS Element: {wbs_element_in.code}")

                except Exception as e:
                    logger.error(
                        f"Failed to seed WBS Element {wbs_data.get('code')}: {e}"
                    )
                    raise

    # ------------------------------------------------------------------
    # Work Packages (Control Accounts + Work Packages)
    # ------------------------------------------------------------------

    async def seed_work_packages(
        self, session: AsyncSession, data: dict[str, Any]
    ) -> None:
        """Seed Control Accounts and Work Packages for leaf-level WBS elements.

        For each leaf WBS element (one that is not a parent of another WBS element),
        creates a ControlAccount and a WorkPackage. Stores the mapping from the
        original WBS element ID to the new WorkPackage root ID so downstream
        seeders (cost elements, progress entries, forecasts) can reference real
        WorkPackage IDs.

        Args:
            session: Database session
            data: Test data dictionary
        """
        logger.info("Seeding Control Accounts and Work Packages...")

        from uuid import uuid4

        actor_id = uuid4()

        # Determine leaf WBS elements: those whose wbs_element_id does NOT appear
        # as parent_wbs_element_id in any other WBS element.
        all_parent_ids: set[str] = set()
        for wbs in data["wbs_elements"]:
            pid = wbs.get("parent_wbs_element_id")
            if pid:
                all_parent_ids.add(str(pid))

        ca_service = ControlAccountService(session)
        wp_service = WorkPackageService(session)

        # Fetch an organizational unit to assign to Control Accounts.
        org_unit_stmt = sa_select(OrganizationalUnit.organizational_unit_id).limit(1)
        org_result = await session.execute(org_unit_stmt)
        org_unit_row = org_result.scalar_one_or_none()
        if not org_unit_row:
            raise ValueError(
                "No OrganizationalUnit found. Seed organizational units first."
            )
        org_unit_id = org_unit_row

        with seed_operation():
            for wbs in data["wbs_elements"]:
                mutated_wbs_id = str(wbs.get("wbs_element_id", ""))

                # Skip non-leaf WBS elements
                if mutated_wbs_id in all_parent_ids:
                    continue

                # The wbs_element_id in the list was remapped during WBS seeding.
                # Resolve via reverse mapping to get the original JSON key, then
                # look up the DB id via the forward mapping.
                from uuid import UUID as UUIDType

                original_key: str | None = self.wbs_id_reverse.get(
                    UUIDType(mutated_wbs_id)
                )
                if original_key:
                    db_wbs_id = self.wbs_id_mapping.get(original_key)
                    lookup_key = original_key
                else:
                    # Fallback: the id was never remapped (shouldn't happen)
                    db_wbs_id = self.wbs_id_mapping.get(mutated_wbs_id)
                    lookup_key = mutated_wbs_id

                if not db_wbs_id:
                    raise ValueError(
                        f"Leaf WBS Element {mutated_wbs_id} not found in ID mapping"
                    )

                # Check if we already have a mapping (idempotent re-runs)
                if lookup_key in self.wp_id_mapping:
                    logger.debug(
                        f"WorkPackage for WBS {lookup_key} already mapped, skipping"
                    )
                    continue

                # Create Control Account
                ca_id = uuid4()
                ca_in = ControlAccountCreate(
                    control_account_id=ca_id,
                    name=f"CA - {wbs['name']}",
                    code=f"CA-{wbs['code']}",
                    wbs_element_id=db_wbs_id,
                    organizational_unit_id=org_unit_id,
                    branch="main",
                )
                await ca_service.create_root(
                    root_id=ca_id,
                    actor_id=actor_id,
                    branch="main",
                    name=ca_in.name,
                    code=ca_in.code,
                    wbs_element_id=db_wbs_id,
                    organizational_unit_id=org_unit_id,
                )
                logger.info(f"Created Control Account: {ca_in.name}")

                # Create Work Package under the Control Account
                wp_id = uuid4()
                wp_in = WorkPackageCreate(
                    work_package_id=wp_id,
                    name=f"WP - {wbs['name']}",
                    code=f"WP-{wbs['code']}",
                    control_account_id=ca_id,
                    branch="main",
                )
                await wp_service.create_work_package(wp_in, actor_id)
                logger.info(f"Created Work Package: {wp_in.name}")

                # Store mapping: original WBS element ID -> new WP root ID
                self.wp_id_mapping[lookup_key] = wp_id

    # ------------------------------------------------------------------
    # Cost Elements + Forecasts
    # ------------------------------------------------------------------

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

        from sqlalchemy import func, select

        from app.models.domain.cost_element import CostElement

        actor_id = uuid4()

        # Load fresh data since we modify dicts in-place
        original_data = self.load_test_data()
        ce_data_list = original_data["cost_elements"]

        ce_service = CostElementService(session)

        # Build lookup of existing cost elements by (work_package_id, cost_element_type_id)
        # for idempotent re-runs. Each work_package_id maps to the DB cost_element_id.
        stmt_ce = select(
            CostElement.cost_element_id,
            CostElement.work_package_id,
            CostElement.cost_element_type_id,
        ).where(
            func.upper(CostElement.valid_time).is_(None),
            CostElement.deleted_at.is_(None),
        )
        result_ce = await session.execute(stmt_ce)
        existing_ce_by_wp_type: dict[tuple[str, str], UUID] = {
            (
                str(row.work_package_id),
                str(row.cost_element_type_id),
            ): row.cost_element_id
            for row in result_ce.all()
        }

        with seed_operation():
            for ce_data in ce_data_list:
                try:
                    forecast_data = ce_data.pop("forecast", None)
                    original_ce_id = ce_data.get("cost_element_id", "")

                    # Map wbs_element_id to real WorkPackage ID via wp_id_mapping
                    original_wbs_id = ce_data.get("wbs_element_id", "")
                    db_wp_id = self.wp_id_mapping.get(str(original_wbs_id))
                    if not db_wp_id:
                        raise ValueError(
                            f"WorkPackage for WBS Element {original_wbs_id} not found in mapping"
                        )

                    # Check if this cost element already exists (idempotency)
                    ce_type_id = ce_data.get("cost_element_type_id", "")
                    lookup_key = (str(db_wp_id), str(ce_type_id))
                    existing_ce_id = existing_ce_by_wp_type.get(lookup_key)

                    if existing_ce_id:
                        logger.debug(
                            f"Cost Element for WP {db_wp_id} type {ce_type_id} already exists, skipping"
                        )
                        self.ce_id_mapping[str(original_ce_id)] = existing_ce_id
                        continue

                    new_ce_id = uuid4()
                    ce_data["cost_element_id"] = str(new_ce_id)
                    ce_data["work_package_id"] = str(db_wp_id)
                    ce_data.pop("wbs_element_id", None)
                    ce_data.pop("name", None)

                    ce_in = CostElementCreate(**ce_data)
                    await ce_service.create_cost_element(ce_in, actor_id)
                    logger.info(f"Created Cost Element: {ce_in.cost_element_id}")

                    # Store mapping for cost registrations
                    self.ce_id_mapping[str(original_ce_id)] = ce_in.cost_element_id

                    if forecast_data:
                        new_forecast_id = uuid4()
                        forecast_data["forecast_id"] = str(new_forecast_id)
                        await self._create_forecast(
                            session, forecast_data, actor_id, db_wp_id
                        )

                except Exception as e:
                    # Check if it's an overlap error (version already exists)
                    if "overlap" in str(e).lower() or "overlapping" in str(e).lower():
                        logger.debug(
                            f"Cost Element {ce_data.get('cost_element_id')} already exists (overlap), skipping"
                        )
                        continue
                    logger.error(
                        f"Failed to seed Cost Element {ce_data.get('cost_element_id')}: {e}"
                    )
                    raise

    async def _create_forecast(
        self,
        session: AsyncSession,
        forecast_data: dict[str, Any],
        actor_id: UUID,
        work_package_id: UUID,
    ) -> None:
        """Create a forecast and link it to the WorkPackage.

        Args:
            session: Database session
            forecast_data: Forecast data dictionary
            actor_id: ID of the user creating the forecast
            work_package_id: Root ID of the WorkPackage to link the forecast to
        """
        from datetime import UTC, datetime

        from sqlalchemy import func, update

        from app.models.domain.forecast import Forecast
        from app.models.domain.work_package import WorkPackage

        with seed_operation():
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

            # Link forecast to WorkPackage (current version only)
            stmt = (
                update(WorkPackage)
                .where(
                    WorkPackage.work_package_id == work_package_id,
                    func.upper(WorkPackage.valid_time).is_(None),
                    WorkPackage.deleted_at.is_(None),
                )
                .values(forecast_id=forecast.forecast_id)
            )
            await session.execute(stmt)

            logger.debug(
                f"Created forecast {forecast.forecast_id}: {forecast_data['eac_amount']} "
                f"linked to WP {work_package_id}"
            )

    # ------------------------------------------------------------------
    # Cost Registrations
    # ------------------------------------------------------------------

    async def seed_cost_registrations(
        self, session: AsyncSession, data: dict[str, Any]
    ) -> None:
        """Seed cost registrations."""
        logger.info("Seeding cost registrations...")
        cr_data_list = data["cost_registrations"]

        cr_service = CostRegistrationService(session)

        from uuid import uuid4

        from sqlalchemy import select

        from app.models.domain.cost_registration import CostRegistration

        actor_id = uuid4()

        # Get existing cost registrations to avoid duplicates
        stmt_cr = select(
            CostRegistration.cost_element_id,
            CostRegistration.registration_date,
            CostRegistration.amount,
            CostRegistration.description,
        )
        result_cr = await session.execute(stmt_cr)
        existing_regs = {
            (str(r.cost_element_id), float(r.amount), r.description)
            for r in result_cr.all()
        }
        logger.debug(f"Found {len(existing_regs)} existing cost registrations")

        with seed_operation():
            for cr_data in cr_data_list:
                try:
                    # Resolve cost_element_id via the mapping built during CE seeding
                    original_ce_id = cr_data["cost_element_id"]
                    db_ce_id = self.ce_id_mapping.get(str(original_ce_id))
                    if not db_ce_id:
                        logger.warning(
                            f"Cost element {original_ce_id} not found in mapping, skipping registration"
                        )
                        continue
                    cr_data["cost_element_id"] = str(db_ce_id)

                    reg_key = (
                        cr_data["cost_element_id"],
                        cr_data["amount"],
                        cr_data["description"],
                    )
                    if reg_key in existing_regs:
                        logger.debug(
                            f"Cost Registration already exists: {cr_data.get('description')[:50]}"
                        )
                        continue

                    cr_data["cost_registration_id"] = str(uuid4())

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

    # ------------------------------------------------------------------
    # Progress Entries
    # ------------------------------------------------------------------

    async def seed_progress_entries(
        self, session: AsyncSession, data: dict[str, Any]
    ) -> None:
        """Seed progress entries."""
        logger.info("Seeding progress entries...")
        pe_data_list = data["progress_entries"]

        pe_service = ProgressEntryService(session)

        from uuid import uuid4

        from sqlalchemy import select

        from app.models.domain.progress_entry import ProgressEntry

        actor_id = uuid4()

        # Get existing progress entries to avoid duplicates
        stmt_pe = select(
            ProgressEntry.work_package_id,
            ProgressEntry.progress_percentage,
            ProgressEntry.notes,
        )
        result_pe = await session.execute(stmt_pe)
        existing_entries: set[tuple[str, float, str | None]] = {
            (str(e.work_package_id), float(e.progress_percentage), e.notes)
            for e in result_pe.all()
        }

        with seed_operation():
            for pe_data in pe_data_list:
                try:
                    # Resolve work_package_id via wp_id_mapping (original WBS ID -> real WP ID)
                    original_wp_id = pe_data["work_package_id"]
                    db_wp_id = self.wp_id_mapping.get(str(original_wp_id))
                    if not db_wp_id:
                        logger.warning(
                            f"Work package {original_wp_id} not found in WP mapping, skipping"
                        )
                        continue
                    pe_data["work_package_id"] = str(db_wp_id)

                    entry_key = (
                        pe_data["work_package_id"],
                        pe_data["progress_percentage"],
                        pe_data.get("notes"),
                    )
                    if entry_key in existing_entries:
                        logger.debug(
                            f"Progress Entry already exists: {pe_data.get('notes')}"
                        )
                        continue

                    pe_data["progress_entry_id"] = str(uuid4())

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

    # ------------------------------------------------------------------
    # Cost Events
    # ------------------------------------------------------------------

    async def seed_cost_events(
        self, session: AsyncSession, data: dict[str, Any]
    ) -> None:
        """Seed cost events (quality/cost tracking)."""
        logger.info("Seeding Cost Events...")
        events_data = data.get("cost_events", [])
        if not events_data:
            logger.warning("No cost_events in seed data, skipping")
            return

        from uuid import uuid4

        from sqlalchemy import select

        from app.models.domain.cost_event import CostEvent

        ce_service = CostEventService(session)
        actor_id = uuid4()

        # Get existing cost events by name+project_id for idempotency
        stmt = select(CostEvent.name, CostEvent.project_id)
        result = await session.execute(stmt)
        existing_events = {(r.name, str(r.project_id)) for r in result.all()}

        with seed_operation():
            for event_data in events_data:
                name = event_data["name"]
                project_id = event_data["project_id"]
                event_key = (name, project_id)
                if event_key in existing_events:
                    logger.debug(f"CostEvent '{name}' exists, skipping")
                    continue

                # Remap wbs_element_id if present
                wbs_id = event_data.get("wbs_element_id")
                if wbs_id:
                    db_wbs_id = self.wbs_id_mapping.get(str(wbs_id))
                    if db_wbs_id:
                        event_data["wbs_element_id"] = str(db_wbs_id)
                    else:
                        # WBS not in mapping, set to None
                        event_data["wbs_element_id"] = None

                event_in = CostEventCreate(**event_data)
                await ce_service.create_cost_event(event_in, actor_id)
                logger.info(f"Created CostEvent: {name}")

    # ------------------------------------------------------------------
    # Change Orders
    # ------------------------------------------------------------------

    async def seed_change_orders(
        self, session: AsyncSession, data: dict[str, Any]
    ) -> None:
        """Seed change orders (branchable)."""
        logger.info("Seeding Change Orders...")
        co_data_list = data.get("change_orders", [])
        if not co_data_list:
            logger.warning("No change_orders in seed data, skipping")
            return

        from uuid import uuid4

        from sqlalchemy import select

        from app.models.domain.change_order import ChangeOrder

        co_service = ChangeOrderService(session)
        actor_id = uuid4()

        with seed_operation():
            for co_data in co_data_list:
                code = co_data.get("code", "")

                # Check if CO already exists by code (current, main branch)
                stmt = (
                    select(ChangeOrder)
                    .where(
                        ChangeOrder.code == code,
                        ChangeOrder.branch == "main",
                    )
                    .limit(1)
                )
                result = await session.execute(stmt)
                if result.scalar_one_or_none():
                    logger.debug(f"ChangeOrder {code} exists, skipping")
                    continue

                co_in = ChangeOrderCreate(**co_data)
                await co_service.create_change_order(co_in, actor_id)
                logger.info(
                    f"Created ChangeOrder: {code} ({co_data.get('status', 'draft')})"
                )

    # ------------------------------------------------------------------
    # Orchestrator
    # ------------------------------------------------------------------

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
            # 1. Organizational Units (no deps)
            await self.seed_organizational_units(session, data)
            await asyncio.sleep(0.3)

            # 2. Users (may reference org units via manager_id, but not in our seed)
            await self.seed_users(session, data)
            await asyncio.sleep(0.3)

            # 3. Cost Element Types (reference org units)
            await self.seed_cost_element_types(session, data)
            await asyncio.sleep(0.3)

            # 4. Cost Event Types (no deps)
            await self.seed_cost_event_types(session, data)
            await asyncio.sleep(0.3)

            # 5. Project
            await self.seed_project(session, data)
            await asyncio.sleep(0.5)

            # 6. WBS Elements (reference project)
            await self.seed_wbs_elements(session, data)
            await asyncio.sleep(0.5)

            # 7. Work Packages / Control Accounts (reference WBS + org units)
            await self.seed_work_packages(session, data)
            await asyncio.sleep(0.5)

            # 8. Cost Elements + Forecasts (reference work packages + cost element types)
            await self.seed_cost_elements_and_forecasts(session, data)
            await asyncio.sleep(0.5)

            # 9. Cost Registrations (reference cost elements)
            await self.seed_cost_registrations(session, data)
            await asyncio.sleep(0.5)

            # 10. Progress Entries (reference work packages)
            await self.seed_progress_entries(session, data)
            await asyncio.sleep(0.5)

            # 11. Cost Events (reference project + cost event types)
            await self.seed_cost_events(session, data)
            await asyncio.sleep(0.5)

            # 12. Change Orders (reference project)
            await self.seed_change_orders(session, data)

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
