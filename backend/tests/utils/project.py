import uuid
from datetime import date, timedelta

from sqlmodel import Session

from app import crud
from app.models import Project, ProjectCreate, UserCreate


def create_random_project(db: Session) -> Project:
    """Create a random project with a random user as project manager."""
    email = f"pm_{uuid.uuid4().hex[:8]}@example.com"
    password = "testpassword123"
    user_in = UserCreate(email=email, password=password)
    pm_user = crud.create_user(session=db, user_create=user_in)

    project_in = ProjectCreate(
        project_name=f"Test Project {uuid.uuid4().hex[:8]}",
        customer_name=f"Test Customer {uuid.uuid4().hex[:6]}",
        contract_value=100000.00,
        start_date=date.today(),
        planned_completion_date=date.today() + timedelta(days=365),
        project_manager_id=pm_user.id,
        status="active",
    )

    project = Project.model_validate(project_in)
    db.add(project)
    db.commit()
    db.refresh(project)
    return project


def create_random_project_with_manager(db: Session, manager_id: uuid.UUID) -> Project:
    """Create a random project with a specific user as project manager."""
    project_in = ProjectCreate(
        project_name=f"Test Project {uuid.uuid4().hex[:8]}",
        customer_name=f"Test Customer {uuid.uuid4().hex[:6]}",
        contract_value=100000.00,
        start_date=date.today(),
        planned_completion_date=date.today() + timedelta(days=365),
        project_manager_id=manager_id,
        status="active",
    )

    project = Project.model_validate(project_in)
    db.add(project)
    db.commit()
    db.refresh(project)
    return project
