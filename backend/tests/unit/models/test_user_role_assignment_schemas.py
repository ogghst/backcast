"""Tests for UserRoleAssignment Pydantic schemas."""

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.models.domain.user_role_assignment import ScopeType
from app.models.schemas.user_role_assignment import (
    UserRoleAssignmentCreate,
    UserRoleAssignmentResponse,
    UserRoleAssignmentUpdate,
)


class TestUserRoleAssignmentCreate:
    """Tests for UserRoleAssignmentCreate schema."""

    def test_valid_global_assignment(self) -> None:
        user_id = uuid4()
        role_id = uuid4()
        schema = UserRoleAssignmentCreate(
            user_id=user_id,
            role_id=role_id,
            scope_type=ScopeType.GLOBAL,
        )
        assert schema.user_id == user_id
        assert schema.scope_type == ScopeType.GLOBAL
        assert schema.scope_id is None

    def test_valid_project_assignment(self) -> None:
        project_id = uuid4()
        schema = UserRoleAssignmentCreate(
            user_id=uuid4(),
            role_id=uuid4(),
            scope_type=ScopeType.PROJECT,
            scope_id=project_id,
        )
        assert schema.scope_id == project_id

    def test_project_without_scope_id_fails(self) -> None:
        with pytest.raises(ValidationError, match="scope_id is required"):
            UserRoleAssignmentCreate(
                user_id=uuid4(),
                role_id=uuid4(),
                scope_type=ScopeType.PROJECT,
                scope_id=None,
            )

    def test_global_with_scope_id_fails(self) -> None:
        with pytest.raises(ValidationError, match="scope_id must be NULL"):
            UserRoleAssignmentCreate(
                user_id=uuid4(),
                role_id=uuid4(),
                scope_type=ScopeType.GLOBAL,
                scope_id=uuid4(),
            )

    def test_with_metadata(self) -> None:
        schema = UserRoleAssignmentCreate(
            user_id=uuid4(),
            role_id=uuid4(),
            scope_type=ScopeType.CHANGE_ORDER,
            scope_id=uuid4(),
            metadata_={"authority_level": "HIGH"},
        )
        assert schema.metadata_ == {"authority_level": "HIGH"}

    def test_with_expiration(self) -> None:
        expires = datetime(2026, 12, 31, tzinfo=UTC)
        schema = UserRoleAssignmentCreate(
            user_id=uuid4(),
            role_id=uuid4(),
            scope_type=ScopeType.GLOBAL,
            expires_at=expires,
        )
        assert schema.expires_at == expires

class TestUserRoleAssignmentUpdate:
    """Tests for UserRoleAssignmentUpdate schema."""

    def test_partial_update(self) -> None:
        schema = UserRoleAssignmentUpdate(role_id=uuid4())
        assert schema.role_id is not None
        assert schema.metadata_ is None
        assert schema.expires_at is None

    def test_update_metadata(self) -> None:
        schema = UserRoleAssignmentUpdate(metadata_={"authority_level": "CRITICAL"})
        assert schema.metadata_["authority_level"] == "CRITICAL"

    def test_empty_update(self) -> None:
        schema = UserRoleAssignmentUpdate()
        assert schema.role_id is None
        assert schema.metadata_ is None

class TestUserRoleAssignmentResponse:
    """Tests for UserRoleAssignmentResponse schema."""

    def test_from_attributes(self) -> None:
        """Test model_validate with a mock assignment object."""
        from types import SimpleNamespace

        now = datetime.now(UTC)
        aid = uuid4()
        uid = uuid4()
        rid = uuid4()

        mock_obj = SimpleNamespace(
            id=aid,
            user_id=uid,
            role_id=rid,
            scope_type="global",
            scope_id=None,
            metadata_=None,
            granted_by=None,
            granted_at=now,
            expires_at=None,
            created_at=now,
            updated_at=now,
        )

        response = UserRoleAssignmentResponse.model_validate(mock_obj)
        assert response.id == aid
        assert response.user_id == uid
        assert response.scope_type == "global"
        assert response.metadata_ is None

    def test_from_attributes_with_metadata(self) -> None:
        """Test model_validate reads metadata_ from ORM-like objects."""
        from types import SimpleNamespace

        now = datetime.now(UTC)
        mock_obj = SimpleNamespace(
            id=uuid4(),
            user_id=uuid4(),
            role_id=uuid4(),
            scope_type="project",
            scope_id=uuid4(),
            metadata_={"authority_level": "HIGH"},
            granted_by=uuid4(),
            granted_at=now,
            expires_at=None,
            created_at=now,
            updated_at=now,
        )

        response = UserRoleAssignmentResponse.model_validate(mock_obj)
        assert response.metadata_ == {"authority_level": "HIGH"}

    def test_serialization_uses_metadata_alias(self) -> None:
        """Test that JSON output uses 'metadata' (not 'metadata_')."""
        from types import SimpleNamespace

        now = datetime.now(UTC)
        mock_obj = SimpleNamespace(
            id=uuid4(),
            user_id=uuid4(),
            role_id=uuid4(),
            scope_type="global",
            scope_id=None,
            metadata_={"authority_level": "MEDIUM"},
            granted_by=None,
            granted_at=now,
            expires_at=None,
            created_at=now,
            updated_at=now,
        )

        response = UserRoleAssignmentResponse.model_validate(mock_obj)
        dumped = response.model_dump(by_alias=True)
        assert "metadata" in dumped
        assert "metadata_" not in dumped
        assert dumped["metadata"] == {"authority_level": "MEDIUM"}
