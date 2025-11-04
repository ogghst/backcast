"""Tests for AuditLog model."""
import uuid

from sqlmodel import Session

from app import crud
from app.models import (
    AuditLog,
    AuditLogCreate,
    AuditLogPublic,
    UserCreate,
)


def test_create_audit_log(db: Session) -> None:
    """Test creating an audit log entry."""
    email = f"user_{uuid.uuid4().hex[:8]}@example.com"
    password = "testpassword123"
    user_in = UserCreate(email=email, password=password)
    user = crud.create_user(session=db, user_create=user_in)

    # Create audit log entry
    audit_in = AuditLogCreate(
        entity_type="project",
        entity_id=uuid.uuid4(),
        action="create",
        field_name=None,
        old_value=None,
        new_value="New project created",
        reason="Project kickoff",
        user_id=user.id,
        ip_address="192.168.1.1",
        user_agent="Mozilla/5.0",
    )

    audit = AuditLog.model_validate(audit_in)
    db.add(audit)
    db.commit()
    db.refresh(audit)

    # Verify audit log was created
    assert audit.audit_log_id is not None
    assert audit.entity_type == "project"
    assert audit.action == "create"
    assert audit.user_id == user.id
    assert audit.ip_address == "192.168.1.1"
    assert hasattr(audit, "user")  # Relationship should exist


def test_audit_log_action_enum(db: Session) -> None:
    """Test that action is validated."""
    email = f"user_{uuid.uuid4().hex[:8]}@example.com"
    password = "testpassword123"
    user_in = UserCreate(email=email, password=password)
    user = crud.create_user(session=db, user_create=user_in)

    valid_actions = ["create", "update", "delete", "approve", "reject", "implement"]
    for action in valid_actions:
        audit_in = AuditLogCreate(
            entity_type="project",
            entity_id=uuid.uuid4(),
            action=action,
            user_id=user.id,
        )
        audit = AuditLog.model_validate(audit_in)
        db.add(audit)
        db.commit()
        db.refresh(audit)
        assert audit.action == action


def test_audit_log_public_schema() -> None:
    """Test AuditLogPublic schema for API responses."""
    import datetime

    audit_id = uuid.uuid4()
    entity_id = uuid.uuid4()
    user_id = uuid.uuid4()
    timestamp = datetime.datetime.now(datetime.timezone.utc)

    audit_public = AuditLogPublic(
        audit_log_id=audit_id,
        entity_type="cost_element",
        entity_id=entity_id,
        action="update",
        field_name="budget_bac",
        old_value="10000.00",
        new_value="12000.00",
        reason="Scope increase",
        user_id=user_id,
        timestamp=timestamp,
        ip_address="10.0.0.1",
        user_agent="curl/7.68.0",
    )

    assert audit_public.audit_log_id == audit_id
    assert audit_public.entity_type == "cost_element"
    assert audit_public.action == "update"
    assert audit_public.old_value == "10000.00"
    assert audit_public.new_value == "12000.00"
