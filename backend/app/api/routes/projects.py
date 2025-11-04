import uuid
from typing import Any

from fastapi import APIRouter, HTTPException
from sqlmodel import SQLModel, func, select

from app.api.deps import CurrentUser, SessionDep
from app.models import (
    WBE,
    CostElement,
    CostElementCreate,
    Message,
    Project,
    ProjectCreate,
    ProjectPublic,
    ProjectsPublic,
    ProjectUpdate,
    WBECreate,
)

router = APIRouter(prefix="/projects", tags=["projects"])


# Template schemas for bulk import
class WBETemplateItem(SQLModel):
    """WBE with nested cost elements."""

    wbe: dict
    cost_elements: list[dict] = []


class ProjectTemplate(SQLModel):
    """Template for creating a complete project hierarchy."""

    project: dict
    wbes: list[WBETemplateItem] = []


@router.get("/", response_model=ProjectsPublic)
def read_projects(
    session: SessionDep, _current_user: CurrentUser, skip: int = 0, limit: int = 100
) -> Any:
    """
    Retrieve projects.
    """
    count_statement = select(func.count()).select_from(Project)
    count = session.exec(count_statement).one()
    statement = select(Project).offset(skip).limit(limit)
    projects = session.exec(statement).all()

    return ProjectsPublic(data=projects, count=count)


@router.get("/{id}", response_model=ProjectPublic)
def read_project(session: SessionDep, _current_user: CurrentUser, id: uuid.UUID) -> Any:
    """
    Get project by ID.
    """
    project = session.get(Project, id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


@router.post("/", response_model=ProjectPublic)
def create_project(
    *, session: SessionDep, _current_user: CurrentUser, project_in: ProjectCreate
) -> Any:
    """
    Create new project.
    """
    project = Project.model_validate(project_in)
    session.add(project)
    session.commit()
    session.refresh(project)
    return project


@router.put("/{id}", response_model=ProjectPublic)
def update_project(
    *,
    session: SessionDep,
    _current_user: CurrentUser,
    id: uuid.UUID,
    project_in: ProjectUpdate,
) -> Any:
    """
    Update a project.
    """
    project = session.get(Project, id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    update_dict = project_in.model_dump(exclude_unset=True)
    project.sqlmodel_update(update_dict)
    session.add(project)
    session.commit()
    session.refresh(project)
    return project


@router.delete("/{id}")
def delete_project(
    session: SessionDep, _current_user: CurrentUser, id: uuid.UUID
) -> Message:
    """
    Delete a project.
    """
    project = session.get(Project, id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Check if project has WBEs
    wbes_count = session.exec(
        select(func.count()).select_from(WBE).where(WBE.project_id == id)
    ).one()
    if wbes_count > 0:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot delete project with {wbes_count} existing WBE(s). Delete WBEs first.",
        )

    session.delete(project)
    session.commit()
    return Message(message="Project deleted successfully")


@router.post("/from-template", response_model=ProjectPublic)
def create_project_from_template(
    *, session: SessionDep, _current_user: CurrentUser, template: ProjectTemplate
) -> Any:
    """
    Create a complete project structure from a template.

    This endpoint creates a project with all associated WBEs and cost elements
    in a single transaction. If any part fails, the entire operation is rolled back.
    """
    # Start a transaction explicitly
    try:
        # Create the project from template
        project_data = template.project
        project_create = ProjectCreate(**project_data)
        project = Project.model_validate(project_create)
        session.add(project)
        session.flush()  # Get project_id without committing

        created_wbes = []
        for wbe_item in template.wbes:
            # Create WBE
            wbe_data = wbe_item.wbe.copy()
            wbe_data["project_id"] = project.project_id
            wbe_create = WBECreate(**wbe_data)
            wbe = WBE.model_validate(wbe_create)
            session.add(wbe)
            session.flush()
            created_wbes.append(wbe)

            # Create cost elements for this WBE
            for ce_data in wbe_item.cost_elements:
                ce_data_with_wbe = ce_data.copy()
                ce_data_with_wbe["wbe_id"] = wbe.wbe_id
                ce_create = CostElementCreate(**ce_data_with_wbe)
                ce = CostElement.model_validate(ce_create)
                session.add(ce)

        # Commit all at once
        session.commit()
        session.refresh(project)

        return project
    except Exception as e:
        session.rollback()
        raise HTTPException(
            status_code=400, detail=f"Failed to create project from template: {str(e)}"
        )
