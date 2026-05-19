"""Data seeding module for initializing database with default entities.

Provides flexible JSON-based seeding that uses Pydantic schemas for validation.
"""

import asyncio
import json
import logging
from datetime import UTC, datetime
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
                    await ce_service.create_cost_element(
                        ce_in, actor_id, branch=item["branch"]
                    )
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
                    await cr_service.create_cost_registration(
                        cr_in, actor_id, branch=item["branch"]
                    )
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
                    await pe_service.create(
                        actor_id=actor_id, progress_in=pe_in, branch=item["branch"]
                    )
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
                    target_status = item.get("status", "draft")

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

                    # Run impact analysis explicitly (not triggered by creation)
                    if created_co.branch_name:
                        try:
                            await co_service._run_impact_analysis(
                                created_co, created_co.branch_name
                            )
                            await session.commit()
                        except Exception as e:
                            logger.warning(
                                f"  → Impact analysis failed for {co_in.code}: {e}"
                            )
                            await session.rollback()

                    # Verify impact analysis completed
                    await asyncio.sleep(1)
                    await session.refresh(created_co)

                    if created_co.impact_analysis_status == "completed":
                        logger.info(f"  → Impact analysis completed: {co_in.code}")
                    else:
                        logger.warning(
                            f"  → Impact analysis status: {created_co.impact_analysis_status}, "
                            f"skipping workflow transitions for {co_in.code}"
                        )
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
                    if target_status and target_status != "draft":
                        try:
                            # For Submitted for Approval status
                            if (
                                "submitted_for_approval" in target_status
                                or "Submitted for Approval" in target_status
                            ):
                                await co_service.submit_for_approval(
                                    change_order_id=co_id,
                                    actor_id=actor_id,
                                    branch="main",  # ChangeOrder entity lives on main
                                    comment=f"Seeded status: {target_status}",
                                )
                                logger.info(f"  → Submitted for approval: {co_in.code}")

                            # For Under Review status (need to submit first)
                            elif (
                                "under_review" in target_status
                                or "Under Review" in target_status
                            ):
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
                                    status="under_review"
                                )
                                await co_service.update_change_order(
                                    change_order_id=co_id,
                                    change_order_in=under_review_update,
                                    actor_id=actor_id,
                                    branch="main",
                                )
                                logger.info(f"  → Under Review: {co_in.code}")

                            # For Approved status (need to submit → under review → approve)
                            elif (
                                "approved" in target_status
                                or "Approved" in target_status
                            ):
                                # First submit
                                await co_service.submit_for_approval(
                                    change_order_id=co_id,
                                    actor_id=actor_id,
                                    branch="main",  # ChangeOrder entity lives on main
                                    comment="Auto-submit for seeding",
                                )

                                # Then transition to Under Review
                                under_review_update = ChangeOrderUpdate(
                                    status="under_review"
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
                            elif (
                                "rejected" in target_status
                                or "Rejected" in target_status
                            ):
                                # First submit
                                await co_service.submit_for_approval(
                                    change_order_id=co_id,
                                    actor_id=actor_id,
                                    branch="main",  # ChangeOrder entity lives on main
                                    comment="Auto-submit for seeding",
                                )

                                # Then transition to Under Review
                                under_review_update = ChangeOrderUpdate(
                                    status="under_review"
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

    async def seed_ai_providers(self, session: AsyncSession) -> None:
        """Seed AI providers from ai_providers.json file.

        Args:
            session: Database session
        """
        from sqlalchemy import select as sql_select

        from app.models.domain.ai import AIModel, AIProvider, AIProviderConfig

        logger.info("Starting AI provider seeding...")
        provider_data = self.load_seed_file("ai_providers.json")

        if not provider_data:
            logger.info("No AI provider seed data found or file is empty")
            return

        created_count = 0
        skipped_count = 0

        with seed_operation():  # Allow explicit IDs from seed data
            for idx, provider_dict in enumerate(provider_data):
                try:
                    provider_id = provider_dict.get("id")
                    provider_configs = provider_dict.pop("configs", [])
                    provider_models = provider_dict.pop("models", [])

                    # Check if provider already exists
                    stmt = sql_select(AIProvider).where(
                        AIProvider.id == UUID(provider_id)
                    )
                    result = await session.execute(stmt)
                    existing = result.scalar_one_or_none()

                    if existing:
                        logger.debug(
                            f"AI Provider {provider_dict.get('name')} already exists, skipping"
                        )
                        skipped_count += 1
                        continue

                    # Create provider with explicit ID
                    provider = AIProvider(
                        id=UUID(provider_id) if provider_id else None,
                        provider_type=provider_dict["provider_type"],
                        name=provider_dict["name"],
                        base_url=provider_dict.get("base_url"),
                        is_active=provider_dict.get("is_active", True),
                    )
                    session.add(provider)
                    await session.flush()

                    # Add configs
                    for config_dict in provider_configs:
                        config_id = config_dict.pop("id", None)
                        config = AIProviderConfig(
                            id=UUID(config_id) if config_id else None,
                            provider_id=str(provider.id),
                            key=config_dict["key"],
                            value=config_dict.get("value"),
                            is_encrypted=config_dict.get("is_encrypted", False),
                        )
                        session.add(config)
                        await session.flush()

                    # Add models
                    for model_dict in provider_models:
                        model_id = model_dict.pop("id", None)
                        model = AIModel(
                            id=UUID(model_id) if model_id else None,
                            provider_id=str(provider.id),
                            model_id=model_dict["model_id"],
                            display_name=model_dict["display_name"],
                            is_active=model_dict.get("is_active", True),
                        )
                        session.add(model)
                        await session.flush()

                    created_count += 1
                    logger.info(f"Created AI Provider: {provider.name}")

                except Exception as e:
                    logger.error(f"Failed to seed AI provider at index {idx}: {e}")
                    skipped_count += 1
                    continue

        logger.info(
            f"AI Provider seeding complete: {created_count} created, {skipped_count} skipped/failed"
        )

    async def seed_ai_assistants(self, session: AsyncSession) -> None:
        """Seed AI assistant configs from ai_assistant_configs.json file.

        Args:
            session: Database session
        """
        from sqlalchemy import select as sql_select

        from app.models.domain.ai import AIAssistantConfig

        logger.info("Starting AI assistant seeding...")
        assistant_data = self.load_seed_file("ai_assistant_configs.json")

        if not assistant_data:
            logger.info("No AI assistant seed data found or file is empty")
            return

        created_count = 0
        skipped_count = 0

        with seed_operation():  # Allow explicit IDs from seed data
            for idx, assistant_dict in enumerate(assistant_data):
                try:
                    assistant_id = assistant_dict.get("id")

                    # Check if assistant already exists
                    stmt = sql_select(AIAssistantConfig).where(
                        AIAssistantConfig.id == UUID(assistant_id)
                    )
                    result = await session.execute(stmt)
                    existing = result.scalar_one_or_none()

                    if existing:
                        logger.debug(
                            f"AI Assistant {assistant_dict.get('name')} already exists, skipping"
                        )
                        skipped_count += 1
                        continue

                    # Create assistant with explicit ID
                    assistant = AIAssistantConfig(
                        id=UUID(assistant_id) if assistant_id else None,
                        name=assistant_dict["name"],
                        description=assistant_dict.get("description"),
                        model_id=str(assistant_dict["model_id"]),
                        system_prompt=assistant_dict.get("system_prompt"),
                        temperature=assistant_dict.get("temperature"),
                        max_tokens=assistant_dict.get("max_tokens"),
                        is_active=assistant_dict.get("is_active", True),
                        default_role=assistant_dict.get("default_role"),
                        agent_type=assistant_dict.get("agent_type", "main"),
                        allowed_tools=assistant_dict.get("allowed_tools"),
                        delegation_config=assistant_dict.get("delegation_config"),
                        structured_output_schema=assistant_dict.get(
                            "structured_output_schema"
                        ),
                        is_system=assistant_dict.get("is_system", False),
                    )
                    session.add(assistant)
                    await session.flush()

                    created_count += 1
                    logger.info(f"Created AI Assistant: {assistant.name}")

                except Exception as e:
                    logger.error(f"Failed to seed AI assistant at index {idx}: {e}")
                    skipped_count += 1
                    continue

        logger.info(
            f"AI Assistant seeding complete: {created_count} created, {skipped_count} skipped/failed"
        )

    async def seed_ai_tools_test_data(self, session: AsyncSession) -> None:
        """Seed AI Tools test data from ai_tools_test_data.json file.

        Args:
            session: Database session
        """
        from app.db.ai_tools_seeder import AIToolsTestDataSeeder

        logger.info("Starting AI Tools test data seeding...")

        # Check if test data file exists
        test_data_file = self.seed_dir / "ai_tools_test_data.json"
        if not test_data_file.exists():
            logger.info("No AI Tools test data file found, skipping")
            return

        try:
            ai_tools_seeder = AIToolsTestDataSeeder(seed_dir=self.seed_dir)
            await ai_tools_seeder.seed_all(session)
        except Exception as e:
            logger.warning(f"AI Tools test data seeding failed (non-critical): {e}")

    async def seed_ai_specialists(self, session: AsyncSession) -> None:
        """Seed AI specialist configs from ai_specialist_configs.json file.

        Specialists are DB-configurable agents with agent_type='specialist'.
        Idempotent — checks by name + agent_type before inserting.

        Args:
            session: Database session
        """
        from sqlalchemy import select as sql_select

        from app.models.domain.ai import AIAssistantConfig

        logger.info("Starting AI specialist seeding...")
        specialist_data = self.load_seed_file("ai_specialist_configs.json")

        if not specialist_data:
            logger.info("No AI specialist seed data found or file is empty")
            return

        created_count = 0
        skipped_count = 0

        with seed_operation():
            for idx, spec_dict in enumerate(specialist_data):
                try:
                    # Check if specialist already exists by name + agent_type
                    stmt = sql_select(AIAssistantConfig).where(
                        AIAssistantConfig.name == spec_dict["name"],
                        AIAssistantConfig.agent_type == "specialist",
                    )
                    result = await session.execute(stmt)
                    existing = result.scalar_one_or_none()

                    if existing:
                        logger.debug(
                            f"AI Specialist {spec_dict['name']} already exists, skipping"
                        )
                        skipped_count += 1
                        continue

                    # Look up model_id — use the first active model if not specified
                    model_id = spec_dict.get("model_id")
                    if not model_id:
                        from app.models.domain.ai import AIModel

                        model_stmt = (
                            sql_select(AIModel)
                            .where(AIModel.is_active.is_(True))
                            .limit(1)
                        )
                        model_result = await session.execute(model_stmt)
                        model = model_result.scalar_one_or_none()
                        if not model:
                            logger.error(
                                "No active AI model found, skipping specialist seeding"
                            )
                            return
                        model_id = str(model.id)

                    specialist = AIAssistantConfig(
                        name=spec_dict["name"],
                        description=spec_dict.get("description"),
                        model_id=str(model_id),
                        system_prompt=spec_dict.get("system_prompt"),
                        temperature=spec_dict.get("temperature"),
                        max_tokens=spec_dict.get("max_tokens"),
                        is_active=spec_dict.get("is_active", True),
                        default_role=spec_dict.get("default_role"),
                        agent_type="specialist",
                        allowed_tools=spec_dict.get("allowed_tools"),
                        delegation_config=spec_dict.get("delegation_config"),
                        structured_output_schema=spec_dict.get(
                            "structured_output_schema"
                        ),
                        is_system=spec_dict.get("is_system", True),
                    )
                    session.add(specialist)
                    await session.flush()

                    created_count += 1
                    logger.info(f"Created AI Specialist: {specialist.name}")

                except Exception as e:
                    logger.error(f"Failed to seed AI specialist at index {idx}: {e}")
                    skipped_count += 1
                    continue

        logger.info(
            f"AI Specialist seeding complete: {created_count} created, "
            f"{skipped_count} skipped/failed"
        )

    async def seed_rbac_roles(self, session: AsyncSession) -> None:
        """Seed RBAC roles and permissions from seed/rbac_roles.json.

        Idempotent - safe to run multiple times. Skips existing roles.
        Creates system roles (is_system=True) that cannot be deleted via API.

        Args:
            session: Database session
        """
        from sqlalchemy import select

        from app.models.domain.rbac import RBACRole, RBACRolePermission

        logger.info("Starting RBAC role seeding...")

        rbac_file = self.seed_dir / "rbac_roles.json"

        if not rbac_file.exists():
            logger.warning(f"RBAC seed file not found: {rbac_file}")
            return

        try:
            with rbac_file.open() as f:
                rbac_config = json.load(f)
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in RBAC seed file {rbac_file}: {e}")
            return

        roles_data = rbac_config.get("roles", {})
        if not roles_data:
            logger.info("No roles found in RBAC config")
            return

        # Track existing roles for idempotency
        stmt = select(RBACRole.name)
        result = await session.execute(stmt)
        existing_roles = set(result.scalars().all())

        if existing_roles:
            logger.debug(f"Found {len(existing_roles)} existing RBAC roles")

        # Track existing permissions for idempotency
        # role_id is stored as UUID in database but mapped as string in the model
        # Query using ORM to ensure proper type conversion
        stmt_perms = select(RBACRolePermission.role_id, RBACRolePermission.permission)
        result_perms = await session.execute(stmt_perms)

        existing_perms: set[tuple[str, str]] = set()
        for row in result_perms.all():
            # row is a tuple of (role_id, permission)
            # role_id might be returned as UUID, convert to string for comparison
            role_id_val = row[0]
            permission_val = row[1]
            # Convert role_id to string if it's a UUID
            if hasattr(role_id_val, "__str__"):
                role_id_str = str(role_id_val)
            else:
                role_id_str = role_id_val
            existing_perms.add((role_id_str, permission_val))

        logger.info(
            f"Found {len(existing_perms)} existing RBAC role permissions in database"
        )

        created_count = 0
        skipped_count = 0
        permission_created_count = 0
        permission_skipped_count = 0
        permission_removed_count = 0

        desired_perms: set[tuple[str, str]] = set()
        role_id_map: dict[str, str] = {}  # role_name -> role_id_str

        now = datetime.now(UTC)

        with seed_operation():  # Allow explicit role_id from seed data
            for role_name, role_def in roles_data.items():
                try:
                    # Check if role already exists
                    if role_name in existing_roles:
                        logger.debug(
                            f"Role {role_name} already exists, skipping creation"
                        )
                        skipped_count += 1
                        stmt_role = select(RBACRole).where(RBACRole.name == role_name)
                        result_role = await session.execute(stmt_role)
                        role = result_role.scalar_one_or_none()
                        if role:
                            role_id = role.id
                        else:
                            logger.error(
                                f"Role {role_name} in existing_roles but not found in DB"
                            )
                            continue
                    else:
                        from uuid import uuid4

                        role_id = uuid4()
                        role = RBACRole(
                            id=role_id,
                            name=role_name,
                            description=role_def.get("description"),
                            is_system=True,
                            created_at=now,
                            updated_at=now,
                        )
                        session.add(role)
                        await session.flush()
                        created_count += 1
                        logger.info(f"Created RBAC role: {role_name}")

                    permissions = role_def.get("permissions", [])
                    role_id_str = str(role_id)
                    role_id_map[role_name] = role_id_str
                    logger.debug(
                        f"Processing {len(permissions)} permissions for role"
                        f" {role_name} (role_id={role_id_str})"
                    )

                    for perm in permissions:
                        desired_perms.add((role_id_str, perm))
                        if (role_id_str, perm) in existing_perms:
                            logger.debug(
                                f"Skipping existing permission: {role_name}.{perm}"
                            )
                            permission_skipped_count += 1
                            continue

                        from uuid import uuid4

                        role_perm = RBACRolePermission(
                            id=uuid4(),
                            role_id=role_id_str,
                            permission=perm,
                        )
                        session.add(role_perm)
                        permission_created_count += 1
                        logger.debug(f"Adding permission: {role_name}.{perm}")

                except Exception as e:
                    logger.error(f"Failed to seed role {role_name}: {e}")
                    continue

            # Remove permissions present in DB but not in the config file
            stale_perms = existing_perms - desired_perms
            for role_id_str, perm in stale_perms:
                # Only clean up permissions for roles that are still defined in config
                if role_id_str not in role_id_map.values():
                    continue
                try:
                    from sqlalchemy import delete

                    await session.execute(
                        delete(RBACRolePermission).where(
                            RBACRolePermission.role_id == role_id_str,
                            RBACRolePermission.permission == perm,
                        )
                    )
                    permission_removed_count += 1
                    logger.info(f"Removed stale permission: {role_id_str}.{perm}")
                except Exception as e:
                    logger.error(
                        f"Failed to remove stale permission {role_id_str}.{perm}: {e}"
                    )

        logger.info(
            f"RBAC role seeding complete: {created_count} created,"
            f" {skipped_count} skipped | "
            f"Permissions: {permission_created_count} created,"
            f" {permission_skipped_count} skipped,"
            f" {permission_removed_count} removed"
        )

    async def seed_user_role_assignments(self, session: AsyncSession) -> None:
        """Seed global UserRoleAssignment records for each user.

        Creates one GLOBAL-scoped UserRoleAssignment for each user by reading
        the role from the seed data (users.json) and mapping it to the
        corresponding RBACRole. Uses direct SQLAlchemy queries consistent
        with seed_rbac_roles() pattern.

        Idempotent - skips users that already have a global assignment.

        Args:
            session: Database session
        """
        from sqlalchemy import select

        from app.models.domain.rbac import RBACRole
        from app.models.domain.user import User
        from app.models.domain.user_role_assignment import (
            ScopeType,
            UserRoleAssignment,
        )

        logger.info("Starting user role assignment seeding...")

        # Load seed data to get role mappings by user_id
        user_seed_data = self.load_seed_file("users.json")
        seed_role_map: dict[str, str] = {}  # user_id string -> role name
        for item in user_seed_data:
            uid = item.get("user_id")
            role_name = item.get("role")
            if uid and role_name:
                seed_role_map[uid] = role_name

        # Load all users
        stmt_users = select(User)
        result_users = await session.execute(stmt_users)
        users = result_users.scalars().all()

        if not users:
            logger.info("No users found, skipping role assignment seeding")
            return

        # Load all RBAC roles
        stmt_roles = select(RBACRole)
        result_roles = await session.execute(stmt_roles)
        roles = result_roles.scalars().all()

        # Build role name -> role_id lookup
        role_map: dict[str, UUID] = {role.name: role.id for role in roles}

        created_count = 0
        skipped_count = 0

        with seed_operation():
            for user in users:
                user_id_str = str(user.user_id)
                user_role_name = seed_role_map.get(user_id_str)

                if not user_role_name:
                    logger.warning(
                        f"User {user.email} has no role in seed data, "
                        f"skipping assignment"
                    )
                    skipped_count += 1
                    continue

                # Look up the RBACRole for the user's role name
                if user_role_name not in role_map:
                    logger.warning(
                        f"User {user.email} has unrecognized role "
                        f"'{user_role_name}', skipping assignment"
                    )
                    skipped_count += 1
                    continue

                role_id = role_map[user_role_name]

                # Check if global assignment already exists
                stmt_existing = select(UserRoleAssignment).where(
                    UserRoleAssignment.user_id == user.user_id,
                    UserRoleAssignment.scope_type == ScopeType.GLOBAL,
                    UserRoleAssignment.scope_id.is_(None),
                )
                result_existing = await session.execute(stmt_existing)
                existing = result_existing.scalar_one_or_none()

                if existing:
                    logger.debug(
                        f"User {user.email} already has global role assignment, "
                        f"skipping"
                    )
                    skipped_count += 1
                    continue

                # Create the global assignment
                from uuid import uuid4

                assignment = UserRoleAssignment(
                    id=uuid4(),
                    user_id=user.user_id,
                    role_id=role_id,
                    scope_type=ScopeType.GLOBAL,
                    scope_id=None,
                    granted_at=datetime.now(UTC),
                )
                session.add(assignment)
                created_count += 1
                logger.info(
                    f"Created global role assignment: {user.email} -> {user_role_name}"
                )

            if created_count > 0:
                await session.flush()

        logger.info(
            f"User role assignment seeding complete: {created_count} created, "
            f"{skipped_count} skipped"
        )

    async def seed_co_workflow_config(self, session: AsyncSession) -> None:
        """Seed change order workflow configuration.

        Creates global workflow config with impact levels, approval rules, and SLA rules.
        Required for change order impact analysis.

        Args:
            session: Database session
        """
        from sqlalchemy import select as sql_select

        from app.models.domain.change_order_config import (
            ChangeOrderApprovalRuleConfig,
            ChangeOrderImpactLevelConfig,
            ChangeOrderSLARuleConfig,
            ChangeOrderWorkflowConfig,
        )

        logger.info("Starting CO Workflow Config seeding...")

        # Load all config files
        workflow_data = self.load_seed_file("co_workflow_config.json")
        impact_levels_data = self.load_seed_file("co_impact_level_config.json")
        approval_rules_data = self.load_seed_file("co_approval_rule_config.json")
        sla_rules_data = self.load_seed_file("co_sla_rule_config.json")

        if not workflow_data:
            logger.info("No CO workflow config seed data found")
            return

        created_count = 0
        skipped_count = 0

        with seed_operation():
            for config_dict in workflow_data:
                try:
                    config_id = UUID(config_dict["config_id"])

                    # Check if config already exists
                    stmt = sql_select(ChangeOrderWorkflowConfig).where(
                        ChangeOrderWorkflowConfig.config_id == config_id
                    )
                    result = await session.execute(stmt)
                    existing = result.scalar_one_or_none()

                    if existing:
                        logger.debug(
                            f"CO Workflow Config {config_id} already exists, skipping"
                        )
                        skipped_count += 1
                        continue

                    # Create workflow config
                    config = ChangeOrderWorkflowConfig(
                        id=UUID(config_dict["id"]),
                        config_id=config_id,
                        project_id=UUID(config_dict["project_id"])
                        if config_dict.get("project_id")
                        else None,
                        is_active=config_dict["is_active"],
                        version=config_dict["version"],
                        created_by=UUID(config_dict["created_by"]),
                        updated_by=UUID(config_dict["updated_by"])
                        if config_dict.get("updated_by")
                        else None,
                        impact_weights=config_dict["impact_weights"],
                        score_boundaries=config_dict["score_boundaries"],
                    )
                    session.add(config)
                    await session.flush()

                    # Seed impact levels
                    if impact_levels_data:
                        for level_dict in impact_levels_data:
                            if UUID(level_dict["config_id"]) == config_id:
                                level = ChangeOrderImpactLevelConfig(
                                    id=UUID(level_dict["id"]),
                                    config_id=config_id,
                                    level_name=level_dict["level_name"],
                                    level_order=level_dict["level_order"],
                                    threshold_amount=level_dict["threshold_amount"],
                                    score_threshold_min=level_dict[
                                        "score_threshold_min"
                                    ],
                                    score_threshold_max=level_dict[
                                        "score_threshold_max"
                                    ],
                                    is_active=level_dict["is_active"],
                                )
                                session.add(level)

                    # Seed approval rules
                    if approval_rules_data:
                        for rule_dict in approval_rules_data:
                            if UUID(rule_dict["config_id"]) == config_id:
                                approval_rule = ChangeOrderApprovalRuleConfig(
                                    id=UUID(rule_dict["id"]),
                                    config_id=config_id,
                                    impact_level_name=rule_dict["impact_level_name"],
                                    required_authority_level=rule_dict[
                                        "required_authority_level"
                                    ],
                                    approver_role=rule_dict["approver_role"],
                                )
                                session.add(approval_rule)

                    # Seed SLA rules
                    if sla_rules_data:
                        for rule_dict in sla_rules_data:
                            if UUID(rule_dict["config_id"]) == config_id:
                                sla_rule = ChangeOrderSLARuleConfig(
                                    id=UUID(rule_dict["id"]),
                                    config_id=config_id,
                                    impact_level_name=rule_dict["impact_level_name"],
                                    business_days=rule_dict["business_days"],
                                )
                                session.add(sla_rule)

                    created_count += 1
                    logger.info(f"Created CO Workflow Config: {config_id}")

                except Exception as e:
                    logger.error(f"Failed to seed CO workflow config: {e}")
                    skipped_count += 1

        logger.info(
            f"CO Workflow Config seeding complete: {created_count} created, {skipped_count} skipped"
        )

    async def seed_all(self, session: AsyncSession) -> None:
        """Execute all seeding operations in the correct order.

        Args:
            session: Database session
        """
        logger.info("=== Starting database seeding ===")

        try:
            # Seed RBAC roles first (required by users)
            await self.seed_rbac_roles(session)

            # Seed departments (referenced by users)
            await self.seed_departments(session)

            # Then seed users (depend on roles and departments)
            await self.seed_users(session)

            # Seed user role assignments (depends on users and rbac_roles)
            await self.seed_user_role_assignments(session)

            # Seed CO Workflow Config (required by change orders)
            await self.seed_co_workflow_config(session)

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

            # Seed AI Providers
            await self.seed_ai_providers(session)

            # Seed AI Assistants
            await self.seed_ai_assistants(session)

            # Seed AI Specialists
            await self.seed_ai_specialists(session)

            # Seed AI Tools Test Data
            await self.seed_ai_tools_test_data(session)

            # Commit all changes (services usually commit internally for writes?
            # Or depend on session commit at end. If services use execute() they might depend on session commit.)
            # The pattern here seems to be explicit commit at end of seed_all.
            await session.commit()
            logger.info("=== Database seeding completed successfully ===")

        except Exception as e:
            logger.error(f"Database seeding failed: {e}")
            await session.rollback()
            raise
