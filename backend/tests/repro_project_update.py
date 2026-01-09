import asyncio
from uuid import uuid4

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.config import settings
from app.models.schemas.project import ProjectCreate, ProjectUpdate
from app.services.project import ProjectService


async def reproduce() -> None:
    # Setup DB connection
    # Setup DB connection
    engine = create_async_engine(str(settings.ASYNC_DATABASE_URI))
    AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)

    async with AsyncSessionLocal() as session:
        service = ProjectService(session)
        actor_id = uuid4()

        print("\n--- Starting Reproduction Script ---")

        # 1. Create Project
        project_code = f"REPRO-{uuid4()}"
        print(f"Creating project with code: {project_code}")

        project_in = ProjectCreate(
            name="Repro Project",
            code=project_code,
            budget=10000,
            description="Test Description",
        )

        try:
            created = await service.create_project(project_in, actor_id)
            print(f"Created Project ID (root): {created.project_id}")
            print(f"Created Version ID: {created.id}")
            print(f"Created Valid Time: {created.valid_time}")
        except Exception as e:
            print(f"FAILED to create project: {e}")
            return

        # 2. Update Project (Immediately)
        print("\nAttempting immediate update...")
        update_in = ProjectUpdate(name="Updated Repro Project", budget=20000)

        try:
            updated = await service.update_project(
                created.project_id, update_in, actor_id
            )
            print(f"Updated Version ID: {updated.id}")
            print(f"Updated Name: {updated.name}")
            print("SUCCESS: Update completed.")
        except ValueError as e:
            print(f"CAUGHT EXPECTED ERROR (ValueError): {e}")
            print("REPRODUCTION SUCCESSFUL: The bug is present.")
        except Exception as e:
            print(f"CAUGHT UNEXPECTED ERROR: {type(e).__name__}: {e}")


if __name__ == "__main__":
    asyncio.run(reproduce())
