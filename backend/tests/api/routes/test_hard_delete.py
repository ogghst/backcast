"""Tests for hard delete (permanent delete) endpoints."""


from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app.core.config import settings
from app.models import WBE, CostElement, Project
from app.services.entity_versioning import soft_delete_entity
from tests.utils.cost_element_type import create_random_cost_element_type
from tests.utils.project import create_random_project
from tests.utils.wbe import create_random_wbe


def test_hard_delete_project_requires_admin(
    client: TestClient, normal_user_token_headers: dict[str, str], db: Session
) -> None:
    """Test that hard delete requires admin role."""
    project = create_random_project(db)
    project_id = project.project_id

    # Soft delete first
    soft_delete_entity(
        session=db,
        entity_class=Project,
        entity_id=project_id,
        entity_type="project",
    )
    db.commit()

    # Try to hard delete as normal user (should fail)
    response = client.delete(
        f"{settings.API_V1_STR}/hard-delete/projects/{project_id}",
        headers=normal_user_token_headers,
    )
    assert response.status_code == 403


def test_hard_delete_project(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    """Test hard deleting a soft-deleted project."""
    project = create_random_project(db)
    project_id = project.project_id
    entity_id = project.entity_id

    # Soft delete first
    soft_delete_entity(
        session=db,
        entity_class=Project,
        entity_id=project_id,
        entity_type="project",
    )
    db.commit()

    # Verify it's soft deleted
    statement = (
        select(Project)
        .where(Project.entity_id == entity_id)
        .order_by(Project.version.desc())
    )
    deleted_project = db.exec(statement).first()
    assert deleted_project is not None
    assert deleted_project.status == "deleted"

    # Hard delete
    response = client.delete(
        f"{settings.API_V1_STR}/hard-delete/projects/{project_id}",
        headers=superuser_token_headers,
    )
    assert response.status_code == 200

    # Verify it's permanently deleted
    statement = select(Project).where(Project.entity_id == entity_id)
    all_versions = db.exec(statement).all()
    assert len(all_versions) == 0


def test_hard_delete_validates_entity_is_deleted(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    """Test that hard delete validates entity is soft-deleted first."""
    project = create_random_project(db)
    project_id = project.project_id

    # Try to hard delete an active project (should fail)
    response = client.delete(
        f"{settings.API_V1_STR}/hard-delete/projects/{project_id}",
        headers=superuser_token_headers,
    )
    assert response.status_code == 400
    assert "not deleted" in response.json()["detail"].lower()


def test_hard_delete_wbe(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    """Test hard deleting a soft-deleted WBE."""
    project = create_random_project(db)
    wbe = create_random_wbe(db, project_id=project.project_id)
    wbe_id = wbe.wbe_id
    entity_id = wbe.entity_id

    # Soft delete first
    soft_delete_entity(
        session=db,
        entity_class=WBE,
        entity_id=wbe_id,
        entity_type="wbe",
        branch="main",
    )
    db.commit()

    # Hard delete
    response = client.delete(
        f"{settings.API_V1_STR}/hard-delete/wbes/{wbe_id}?branch=main",
        headers=superuser_token_headers,
    )
    assert response.status_code == 200

    # Verify it's permanently deleted
    statement = (
        select(WBE).where(WBE.entity_id == entity_id).where(WBE.branch == "main")
    )
    all_versions = db.exec(statement).all()
    assert len(all_versions) == 0


def test_hard_delete_cost_element(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    """Test hard deleting a soft-deleted cost element."""
    project = create_random_project(db)
    wbe = create_random_wbe(db, project_id=project.project_id)
    cet = create_random_cost_element_type(db)

    from app.models import CostElementCreate
    from app.services.entity_versioning import create_entity_with_version

    ce_in = CostElementCreate(
        wbe_id=wbe.wbe_id,
        cost_element_type_id=cet.cost_element_type_id,
        department_code="ENG",
        department_name="Engineering",
        budget_bac=10000.00,
        revenue_plan=12000.00,
        business_status="active",
    )
    ce = CostElement.model_validate(ce_in)
    create_entity_with_version(
        session=db,
        entity=ce,
        entity_type="costelement",
        branch="main",
    )
    db.commit()
    db.refresh(ce)
    ce_id = ce.cost_element_id
    entity_id = ce.entity_id

    # Soft delete first
    soft_delete_entity(
        session=db,
        entity_class=CostElement,
        entity_id=ce_id,
        entity_type="costelement",
        branch="main",
    )
    db.commit()

    # Hard delete
    response = client.delete(
        f"{settings.API_V1_STR}/hard-delete/cost-elements/{ce_id}?branch=main",
        headers=superuser_token_headers,
    )
    assert response.status_code == 200

    # Verify it's permanently deleted
    statement = (
        select(CostElement)
        .where(CostElement.entity_id == entity_id)
        .where(CostElement.branch == "main")
    )
    all_versions = db.exec(statement).all()
    assert len(all_versions) == 0


def test_hard_delete_removes_all_versions(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    """Test that hard delete removes all versions of an entity."""
    # Use WBE (branch-enabled) which creates new versions on update
    project = create_random_project(db)
    wbe = create_random_wbe(db, project_id=project.project_id)
    wbe_id = wbe.wbe_id
    entity_id = wbe.entity_id

    # Create multiple versions by updating
    from app.services.entity_versioning import update_entity_with_version

    update_entity_with_version(
        session=db,
        entity_class=WBE,
        entity_id=wbe_id,
        update_data={"machine_type": "Updated Machine"},
        entity_type="wbe",
        branch="main",
    )
    db.commit()

    # Soft delete
    soft_delete_entity(
        session=db,
        entity_class=WBE,
        entity_id=wbe_id,
        entity_type="wbe",
        branch="main",
    )
    db.commit()

    # Verify multiple versions exist
    statement = (
        select(WBE).where(WBE.entity_id == entity_id).where(WBE.branch == "main")
    )
    all_versions_before = db.exec(statement).all()
    assert len(all_versions_before) >= 2

    # Hard delete
    response = client.delete(
        f"{settings.API_V1_STR}/hard-delete/wbes/{wbe_id}?branch=main",
        headers=superuser_token_headers,
    )
    assert response.status_code == 200

    # Verify all versions are deleted
    statement = (
        select(WBE).where(WBE.entity_id == entity_id).where(WBE.branch == "main")
    )
    all_versions_after = db.exec(statement).all()
    assert len(all_versions_after) == 0
