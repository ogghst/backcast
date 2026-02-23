"""Data seeding module for initializing database with default entities.

Provides flexible JSON-based seeding that uses Pydantic schemas for validation.
"""

import asyncio
import json
import logging
from pathlib import Path
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.seed_context import seed_operation
from app.models.schemas.change_order import ChangeOrderUpdate
from app.models.schemas.department import DepartmentCreate
from app.models.schemas.user import UserRegister

logger = logging.getLogger(__name__)


class DataSeeder:
    """Handles database seeding from JSON files."""

    def __init__(self, seed_dir: Path | None = None) -> None:
        """Initialize DataSeeder with seed directory.

        Args:
            seed_dir: Path to directory containing seed JSON files.
                     Defaults to backend/seed relative to project root.
        """
        if seed_dir is None:
            # Default to backend/seed directory
            backend_dir = Path(__file__).parent.parent.parent
            seed_dir = backend_dir / "seed"

        self.seed_dir = seed_dir
        logger.info(f"DataSeeder initialized with seed directory: {self.seed_dir}")

    def load_seed_file(self, filename: str) -> list[dict[str, Any]]:
        """Load and parse a JSON seed file.

        Args:
            filename: Name of the JSON file in seed directory

        Returns:
            List of dictionaries from JSON file

        Raises:
            FileNotFoundError: If seed file doesn't exist
            json.JSONDecodeError: If file contains invalid JSON
        """
        file_path = self.seed_dir / filename
        if not file_path.exists():
            logger.warning(f"Seed file not found: {file_path}")
            return []

        try:
            with open(file_path) as f:
                data = json.load(f)
                if not isinstance(data, list):
                    logger.error(f"Seed file {filename} must contain a JSON array")
                    return []
                return data
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in seed file {filename}: {e}")
            return []

    async def seed_users(self, session: AsyncSession) -> None:
        """Seed users from users.json file.

        Args:
            session: Database session
        """
        from app.services.user import UserService

        logger.info("Starting user seeding...")
        user_data = self.load_seed_file("users.json")

        if not user_data:
            logger.info("No user seed data found or file is empty")
            return

        user_service = UserService(session)
        created_count = 0
        skipped_count = 0

        with seed_operation():  # Allow explicit user_id from seed data
            for idx, user_dict in enumerate(user_data):
                try:
                    # Validate with Pydantic schema
                    user_in = UserRegister(**user_dict)

                    # Check if user already exists
                    existing_user = await user_service.get_by_email(user_in.email)
                    if existing_user:
                        logger.debug(f"User {user_in.email} already exists, skipping")
                        skipped_count += 1
                        continue

                    # Create user (actor_id can be None for seed operation)
                    from uuid import uuid4

                    actor_id = uuid4()  # System actor for seeding
                    await user_service.create_user(user_in, actor_id)
                    created_count += 1
                    logger.info(f"Created user: {user_in.email}")

                except Exception as e:
                    logger.error(f"Failed to seed user at index {idx}: {e}")
                    continue

        logger.info(
            f"User seeding complete: {created_count} created, {skipped_count} skipped"
        )

    async def seed_departments(self, session: AsyncSession) -> None:
        """Seed departments from departments.json file.

        Args:
            session: Database session
        """
        from app.services.department import DepartmentService

        logger.info("Starting department seeding...")
        dept_data = self.load_seed_file("departments.json")

        if not dept_data:
            logger.info("No department seed data found or file is empty")
            return

        dept_service = DepartmentService(session)
        created_count = 0
        skipped_count = 0

        with seed_operation():  # Allow explicit department_id from seed data
            for idx, dept_dict in enumerate(dept_data):
                try:
                    # Validate with Pydantic schema
                    dept_in = DepartmentCreate(**dept_dict)

                    # Check if department already exists
                    existing_dept = await dept_service.get_by_code(dept_in.code)
                    if existing_dept:
                        logger.debug(
                            f"Department {dept_in.code} already exists, skipping"
                        )
                        skipped_count += 1
                        continue

                    # Create department (actor_id can be None for seed operation)
                    from uuid import uuid4

                    actor_id = uuid4()  # System actor for seeding
                    await dept_service.create_department(dept_in, actor_id)
                    created_count += 1
                    logger.info(f"Created department: {dept_in.code}")

                except Exception as e:
                    logger.error(f"Failed to seed department at index {idx}: {e}")
                    continue

        logger.info(
            f"Department seeding complete: {created_count} created, "
            f"{skipped_count} skipped"
        )

    async def seed_cost_element_types(self, session: AsyncSession) -> None:
        """Seed cost element types from cost_element_types.json file.

        Args:
            session: Database session
        """
        from app.models.schemas.cost_element_type import CostElementTypeCreate
        from app.services.cost_element_type_service import CostElementTypeService

        logger.info("Starting cost element type seeding...")
        ce_type_data = self.load_seed_file("cost_element_types.json")

        if not ce_type_data:
            logger.info("No cost element type seed data found or file is empty")
            return

        ce_type_service = CostElementTypeService(session)
        created_count = 0
        skipped_count = 0

        # System actor
        from uuid import uuid4

        actor_id = uuid4()

        with seed_operation():  # Allow explicit cost_element_type_id from seed data
            for idx, item in enumerate(ce_type_data):
                try:
                    # department_id is already in the JSON file now
                    ce_type_in = CostElementTypeCreate(**item)

                    # Create cost element type
                    await ce_type_service.create(ce_type_in, actor_id)
                    created_count += 1
                    logger.info(f"Created CE Type: {ce_type_in.code}")

                except Exception as e:
                    logger.warning(f"Skipping CE Type {item.get('code', idx)}: {e}")
                    skipped_count += 1

        logger.info(
            f"Cost Element Type seeding complete: {created_count} created, {skipped_count} skipped/failed"
        )

    async def seed_projects(self, session: AsyncSession) -> None:
        """Seed projects from projects.json file.

        Args:
            session: Database session
        """
        from app.models.schemas.project import ProjectCreate
        from app.services.project import ProjectService

        logger.info("Starting project seeding...")
        proj_data = self.load_seed_file("projects.json")

        if not proj_data:
            logger.info("No project seed data found or file is empty")
            return

        proj_service = ProjectService(session)
        created_count = 0
        skipped_count = 0

        from uuid import uuid4

        actor_id = uuid4()

        with seed_operation():  # Allow explicit project_id from seed data
            for _, item in enumerate(proj_data):
                try:
                    # Check for existence
                    existing = await proj_service.get_by_code(item["code"])
                    if existing:
                        logger.debug(f"Project {item['code']} exists, skipping")
                        skipped_count += 1
                        continue

                    # Valid times are strings in JSON but Pydantic expects datetime objects or compatible strings
                    # ProjectCreate handles iso strings fine usually, but let's be safe if needed.
                    # ProjectCreate definition: start_date: datetime | None

                    proj_in = ProjectCreate(**item)
                    await proj_service.create_project(proj_in, actor_id)
                    created_count += 1
                    logger.info(f"Created Project: {item['code']}")

                except Exception as e:
                    logger.error(f"Failed to seed project {item.get('code')}: {e}")
                    skipped_count += 1

        logger.info(
            f"Project seeding complete: {created_count} created, {skipped_count} skipped"
        )

    async def seed_wbes(self, session: AsyncSession) -> None:
        """Seed WBEs from wbes.json file.

        Args:
            session: Database session
        """
        from app.models.schemas.wbe import WBECreate
        from app.services.wbe import WBEService

        logger.info("Starting WBE seeding...")
        wbe_data = self.load_seed_file("wbes.json")

        if not wbe_data:
            logger.info("No WBE seed data found or file is empty")
            return

        # Ensure data is sorted by level so parents exist before children
        wbe_data.sort(key=lambda x: x.get("level", 1))

        wbe_service = WBEService(session)
        created_count = 0
        skipped_count = 0

        from uuid import uuid4

        actor_id = uuid4()

        # Cache to track already seeded WBEs for idempotency
        wbe_cache: dict[str, UUID] = {}  # code -> wbe_id

        with seed_operation():  # Allow explicit wbe_id from seed data
            for _, item in enumerate(wbe_data):
                try:
                    # project_id and parent_wbe_id are already in the JSON file now
                    wbe_in = WBECreate(**item)

                    # Check if already seeded (by code and project)
                    # Since we're in seed mode, just try to create - if it exists it will be skipped
                    # by the idempotency logic in the seeder

                    created_wbe = await wbe_service.create_wbe(wbe_in, actor_id)

                    # Store the wbe_id for reference
                    wbe_cache[item["code"]] = created_wbe.wbe_id

                    created_count += 1
                    logger.info(f"Created WBE: {wbe_in.code}")

                except Exception as e:
                    logger.error(f"Failed to seed WBE {item.get('code')}: {e}")
                    skipped_count += 1

        logger.info(
            f"WBE seeding complete: {created_count} created, {skipped_count} skipped/failed"
        )

    async def seed_cost_elements(self, session: AsyncSession) -> None:
        """Seed Cost Elements from cost_elements.json file.

        Args:
            session: Database session
        """
        from app.models.schemas.cost_element import CostElementCreate
        from app.services.cost_element_service import CostElementService

        logger.info("Starting Cost Element seeding...")
        ce_data = self.load_seed_file("cost_elements.json")

        if not ce_data:
            logger.info("No Cost Element seed data found or file is empty")
            return

        ce_service = CostElementService(session)

        from uuid import uuid4

        actor_id = uuid4()

        created_count = 0
        skipped_count = 0

        with seed_operation():  # Allow explicit cost_element_id from seed data
            for _, item in enumerate(ce_data):
                try:
                    # wbe_id and cost_element_type_id are already in the JSON file now
                    # Inject default branch if not present
                    if "branch" not in item:
                        item["branch"] = "main"

                    ce_in = CostElementCreate(**item)
                    await ce_service.create_cost_element(ce_in, actor_id)
                    created_count += 1
                    logger.info(f"Created Cost Element: {ce_in.code}")

                except Exception as e:
                    logger.error(f"Failed to seed CE {item.get('code')}: {e}")
                    skipped_count += 1

        logger.info(
            f"Cost Element seeding complete: {created_count} created, {skipped_count} skipped/failed"
        )

    async def seed_cost_registrations(self, session: AsyncSession) -> None:
        """Seed Cost Registrations from cost_registrations.json file.

        Args:
            session: Database session
        """
        from app.models.schemas.cost_registration import CostRegistrationCreate
        from app.services.cost_registration_service import CostRegistrationService

        logger.info("Starting Cost Registration seeding...")
        cr_data = self.load_seed_file("cost_registrations.json")

        if not cr_data:
            logger.info("No Cost Registration seed data found or file is empty")
            return

        cr_service = CostRegistrationService(session)

        from uuid import uuid4

        actor_id = uuid4()

        created_count = 0
        skipped_count = 0

        with seed_operation():
            for _, item in enumerate(cr_data):
                try:
                    # Inject default branch if not present
                    if "branch" not in item:
                        item["branch"] = "main"

                    cr_in = CostRegistrationCreate(**item)
                    await cr_service.create_cost_registration(cr_in, actor_id)
                    created_count += 1
                    logger.info(f"Created Cost Registration: {cr_in.amount}")

                except Exception as e:
                    logger.error(
                        f"Failed to seed Cost Registration {item.get('description')}: {e}"
                    )
                    skipped_count += 1

        logger.info(
            f"Cost Registration seeding complete: {created_count} created, {skipped_count} skipped/failed"
        )

    async def seed_progress_entries(self, session: AsyncSession) -> None:
        """Seed Progress Entries from progress_entries.json file.

        Args:
            session: Database session
        """
        from app.models.schemas.progress_entry import ProgressEntryCreate
        from app.services.progress_entry_service import ProgressEntryService

        logger.info("Starting Progress Entry seeding...")
        pe_data = self.load_seed_file("progress_entries.json")

        if not pe_data:
            logger.info("No Progress Entry seed data found or file is empty")
            return

        pe_service = ProgressEntryService(session)

        from uuid import uuid4

        actor_id = uuid4()

        created_count = 0
        skipped_count = 0

        with seed_operation():
            for _, item in enumerate(pe_data):
                try:
                    # Inject default branch if not present
                    if "branch" not in item:
                        item["branch"] = "main"

                    pe_in = ProgressEntryCreate(**item)
                    await pe_service.create(actor_id=actor_id, progress_in=pe_in)
                    created_count += 1
                    logger.info(f"Created Progress Entry: {pe_in.progress_percentage}%")

                except Exception as e:
                    logger.error(
                        f"Failed to seed Progress Entry {item.get('notes')}: {e}"
                    )
                    skipped_count += 1

        logger.info(
            f"Progress Entry seeding complete: {created_count} created, {skipped_count} skipped/failed"
        )

    async def seed_change_orders(self, session: AsyncSession) -> None:
        """Seed Change Orders from change_orders.json file.

        Args:
            session: Database session
        """
        from app.models.schemas.change_order import ChangeOrderCreate
        from app.services.change_order_service import ChangeOrderService

        logger.info("Starting Change Order seeding...")
        co_data = self.load_seed_file("change_orders.json")

        if not co_data:
            logger.info("No Change Order seed data found or file is empty")
            return

        co_service = ChangeOrderService(session)

        from app.services.user import UserService

        # Use admin user for actor_id if available to ensure authority for approvals
        user_service = UserService(session)
        admin = await user_service.get_by_email("admin@backcast.org")

        if admin:
            actor_id = admin.user_id
            logger.info(f"Using admin user {actor_id} for Change Order seeding")
        else:
            from uuid import uuid4

            actor_id = uuid4()
            logger.warning(
                "Admin user not found, using random UUID for actor_id (approvals may fail)"
            )

        created_count = 0
        skipped_count = 0

        with seed_operation():
            for _, item in enumerate(co_data):
                try:
                    # Validate with Pydantic schema
                    co_in = ChangeOrderCreate(**item)

                    # Check if change order already exists
                    existing_co = await co_service.get_current_by_code(
                        co_in.code, branch="main"
                    )
                    if existing_co:
                        logger.debug(
                            f"Change Order {co_in.code} already exists, skipping"
                        )
                        skipped_count += 1
                        continue

                    # Store the target status for workflow transition
                    target_status = item.get("status", "Draft")

                    # Store workflow state fields for direct update after creation
                    workflow_fields = {}
                    for field in [
                        "assigned_approver_id",
                        "sla_assigned_at",
                        "sla_due_date",
                        "sla_status",
                    ]:
                        if field in item:
                            workflow_fields[field] = item[field]

                    # Remove status, workflow fields, and non-model fields from create data
                    # so it defaults to "Draft" and only includes valid model fields
                    create_data = item.copy()
                    # Fields to remove from create_data
                    fields_to_remove = [
                        "status",
                        "assigned_approver_id",
                        "sla_assigned_at",
                        "sla_due_date",
                        "sla_status",
                        "priority",
                        "estimated_cost",
                    ]
                    for field in fields_to_remove:
                        create_data.pop(field, None)

                    # Create change order with Draft status
                    # Note: Automatic impact analysis runs on creation but may fail if
                    # project data is incomplete. This is expected during seeding.
                    co_in_draft = ChangeOrderCreate(**create_data)
                    created_co = await co_service.create_change_order(
                        co_in_draft, actor_id=actor_id
                    )
                    created_count += 1
                    logger.info(f"Created Change Order: {co_in.code} - {co_in.title}")

                    # Verify impact analysis completed - retry if needed
                    max_retries = 3
                    impact_analysis_completed = False
                    for retry in range(max_retries):
                        await session.refresh(created_co)
                        if created_co.impact_analysis_status == "completed":
                            logger.info(f"  → Impact analysis completed: {co_in.code}")
                            impact_analysis_completed = True
                            break
                        elif created_co.impact_analysis_status in ("failed", "skipped"):
                            logger.warning(
                                f"  → Impact analysis {created_co.impact_analysis_status}, "
                                f"retrying ({retry + 1}/{max_retries}): {co_in.code}"
                            )
                            # Re-run impact analysis
                            if created_co.branch_name:
                                try:
                                    await co_service._run_impact_analysis(
                                        created_co, created_co.branch_name
                                    )
                                    await session.commit()
                                except Exception as e:
                                    logger.warning(
                                        f"  → Impact analysis retry failed: {e}"
                                    )
                                    await session.rollback()
                                    await asyncio.sleep(2)  # Wait before retry
                            else:
                                logger.warning(
                                    "  → Cannot retry impact analysis: branch_name is None"
                                )
                                break
                        else:
                            # Still in progress, wait
                            logger.info("  → Impact analysis in progress, waiting...")
                            await asyncio.sleep(2)

                    # After retry loop, check final status
                    if not impact_analysis_completed:
                        await session.refresh(created_co)
                        if created_co.impact_analysis_status != "completed":
                            logger.warning(
                                f"  → Impact analysis not completed after {max_retries} retries, "
                                f"skipping workflow transitions for {co_in.code}"
                            )
                            # Skip workflow transitions but keep the CO in Draft status
                            continue

                    # Prevent timestamp overlap for subsequent updates
                    await asyncio.sleep(1)

                    co_id = created_co.change_order_id

                    # If workflow fields are present in seed data, set them directly
                    # This is needed for seeding specific workflow states
                    if workflow_fields:
                        workflow_update = ChangeOrderUpdate(**workflow_fields)
                        await co_service.update_change_order(
                            change_order_id=co_id,
                            change_order_in=workflow_update,
                            actor_id=actor_id,
                            branch="main",
                        )
                        logger.info(f"  → Set workflow fields: {co_in.code}")
                        await asyncio.sleep(1)

                    # If target status is not Draft, attempt to transition through workflow
                    if target_status and target_status != "Draft":
                        try:
                            # For Submitted for Approval status
                            if "Submitted for Approval" in target_status:
                                await co_service.submit_for_approval(
                                    change_order_id=co_id,
                                    actor_id=actor_id,
                                    branch="main",  # ChangeOrder entity lives on main
                                    comment=f"Seeded status: {target_status}",
                                )
                                logger.info(f"  → Submitted for approval: {co_in.code}")

                            # For Under Review status (need to submit first)
                            elif "Under Review" in target_status:
                                # First submit
                                await co_service.submit_for_approval(
                                    change_order_id=co_id,
                                    actor_id=actor_id,
                                    branch="main",  # ChangeOrder entity lives on main
                                    comment="Auto-submit for seeding",
                                )

                                # Then transition to Under Review by updating status
                                # Note: This is a direct status update for seeding purposes
                                under_review_update = ChangeOrderUpdate(
                                    status="Under Review"
                                )
                                await co_service.update_change_order(
                                    change_order_id=co_id,
                                    change_order_in=under_review_update,
                                    actor_id=actor_id,
                                    branch="main",
                                )
                                logger.info(f"  → Under Review: {co_in.code}")

                            # For Approved status (need to submit → under review → approve)
                            elif "Approved" in target_status:
                                # First submit
                                await co_service.submit_for_approval(
                                    change_order_id=co_id,
                                    actor_id=actor_id,
                                    branch="main",  # ChangeOrder entity lives on main
                                    comment="Auto-submit for seeding",
                                )

                                # Then transition to Under Review
                                under_review_update = ChangeOrderUpdate(
                                    status="Under Review"
                                )
                                await co_service.update_change_order(
                                    change_order_id=co_id,
                                    change_order_in=under_review_update,
                                    actor_id=actor_id,
                                    branch="main",
                                )

                                # Then approve
                                await co_service.approve_change_order(
                                    change_order_id=co_id,
                                    approver_id=actor_id,
                                    actor_id=actor_id,
                                    branch="main",  # ChangeOrder entity lives on main
                                    comments="Auto-approved for seeding",
                                )
                                logger.info(f"  → Approved: {co_in.code}")

                            # For Rejected status (need to submit → under review → reject)
                            elif "Rejected" in target_status:
                                # First submit
                                await co_service.submit_for_approval(
                                    change_order_id=co_id,
                                    actor_id=actor_id,
                                    branch="main",  # ChangeOrder entity lives on main
                                    comment="Auto-submit for seeding",
                                )

                                # Then transition to Under Review
                                under_review_update = ChangeOrderUpdate(
                                    status="Under Review"
                                )
                                await co_service.update_change_order(
                                    change_order_id=co_id,
                                    change_order_in=under_review_update,
                                    actor_id=actor_id,
                                    branch="main",
                                )

                                # Then reject
                                await co_service.reject_change_order(
                                    change_order_id=co_id,
                                    rejecter_id=actor_id,
                                    actor_id=actor_id,
                                    branch="main",  # ChangeOrder entity lives on main
                                    comments="Auto-rejected for seeding",
                                )
                                logger.info(f"  → Rejected: {co_in.code}")

                        except Exception as e:
                            logger.warning(
                                f"  Failed to transition {co_in.code} to {target_status}: {e}"
                            )
                            await session.rollback()

                except Exception as e:
                    logger.error(f"Failed to seed Change Order {item.get('code')}: {e}")
                    await session.rollback()
                    skipped_count += 1

        logger.info(
            f"Change Order seeding complete: {created_count} created, {skipped_count} skipped/failed"
        )

    async def seed_change_order_audit_logs(self, session: AsyncSession) -> None:
        """Seed Change Order Audit Logs from change_order_audit_logs.json file.

        Args:
            session: Database session
        """
        from sqlalchemy import insert

        logger.info("Starting Change Order Audit Log seeding...")
        audit_data = self.load_seed_file("change_order_audit_logs.json")

        if not audit_data:
            logger.info("No Change Order Audit Log seed data found or file is empty")
            return

        from app.models.domain.change_order_audit_log import ChangeOrderAuditLog

        created_count = 0
        skipped_count = 0

        with seed_operation():
            for item in audit_data:
                try:
                    # Check if audit log already exists
                    from sqlalchemy import select

                    existing = await session.execute(
                        select(ChangeOrderAuditLog).where(
                            ChangeOrderAuditLog.id == item["id"]
                        )
                    )
                    if existing.scalar_one_or_none():
                        logger.debug(f"Audit log {item['id']} already exists, skipping")
                        skipped_count += 1
                        continue

                    # Insert audit log entry
                    # Parse datetime strings to datetime objects
                    from datetime import datetime

                    item_copy = item.copy()
                    if "changed_at" in item_copy and isinstance(
                        item_copy["changed_at"], str
                    ):
                        item_copy["changed_at"] = datetime.fromisoformat(
                            item_copy["changed_at"]
                        )

                    await session.execute(
                        insert(ChangeOrderAuditLog).values(**item_copy)
                    )
                    created_count += 1
                    logger.debug(f"Created audit log entry: {item['id']}")

                except Exception as e:
                    logger.error(f"Failed to seed audit log {item.get('id')}: {e}")
                    await session.rollback()
                    skipped_count += 1

        logger.info(
            f"Change Order Audit Log seeding complete: {created_count} created, {skipped_count} skipped/failed"
        )

    async def seed_all(self, session: AsyncSession) -> None:
        """Execute all seeding operations in the correct order.

        Args:
            session: Database session
        """
        logger.info("=== Starting database seeding ===")

        try:
            # Seed departments first (referenced by users)
            await self.seed_departments(session)

            # Then seed users
            await self.seed_users(session)

            # Seed Cost Element Types
            await self.seed_cost_element_types(session)

            # Seed Projects
            await self.seed_projects(session)

            # Seed WBEs
            await self.seed_wbes(session)

            # Seed Cost Elements
            await self.seed_cost_elements(session)

            # Seed Cost Registrations
            await self.seed_cost_registrations(session)

            # Seed Progress Entries
            await self.seed_progress_entries(session)

            # Seed Change Orders
            await self.seed_change_orders(session)

            # Seed Change Order Audit Logs
            await self.seed_change_order_audit_logs(session)

            # Commit all changes (services usually commit internally for writes?
            # Or depend on session commit at end. If services use execute() they might depend on session commit.)
            # The pattern here seems to be explicit commit at end of seed_all.
            await session.commit()
            logger.info("=== Database seeding completed successfully ===")

        except Exception as e:
            logger.error(f"Database seeding failed: {e}")
            await session.rollback()
            raise
