import uuid
from datetime import date, timedelta

from sqlmodel import Session

from app.models import WBE, WBECreate
from tests.utils.project import create_random_project


def create_random_wbe(db: Session, project_id: uuid.UUID | None = None) -> WBE:
    """Create a random WBE with a project."""
    if project_id is None:
        project = create_random_project(db)
        project_id = project.project_id

    wbe_in = WBECreate(
        project_id=project_id,
        machine_type=f"Test Machine {uuid.uuid4().hex[:8]}",
        serial_number=f"SER-{uuid.uuid4().hex[:6]}",
        contracted_delivery_date=date.today() + timedelta(days=180),
        revenue_allocation=50000.00,
        status="designing",
    )

    wbe = WBE.model_validate(wbe_in)
    db.add(wbe)
    db.commit()
    db.refresh(wbe)
    return wbe
