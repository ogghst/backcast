"""Data seeding module for initializing database with default entities.

Provides flexible JSON-based seeding that uses Pydantic schemas for validation.
"""

import json
import logging
from pathlib import Path
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.seed_context import seed_operation
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
                    await ce_service.create(ce_in, actor_id)
                    created_count += 1
                    logger.info(f"Created Cost Element: {ce_in.code}")

                except Exception as e:
                    logger.error(f"Failed to seed CE {item.get('code')}: {e}")
                    skipped_count += 1

        logger.info(
            f"Cost Element seeding complete: {created_count} created, {skipped_count} skipped/failed"
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

            # Commit all changes (services usually commit internally for writes?
            # Or depend on session commit at end. If services use execute() they might depend on session commit.)
            # The pattern here seems to be explicit commit at end of seed_all.
            await session.commit()
            logger.info("=== Database seeding completed successfully ===")

        except Exception as e:
            logger.error(f"Database seeding failed: {e}")
            await session.rollback()
            raise
