"""Tests for UserRoleAssignment entity."""

from datetime import UTC, datetime
from uuid import uuid4

import pytest

from app.models.domain.user_role_assignment import (
    ScopeType,
    UserRoleAssignment,
)


class TestScopeType:
    """Tests for ScopeType enum."""

    def test_global_value(self) -> None:
        assert ScopeType.GLOBAL.value == "global"

    def test_project_value(self) -> None:
        assert ScopeType.PROJECT.value == "project"

    def test_change_order_value(self) -> None:
        assert ScopeType.CHANGE_ORDER.value == "change_order"

    def test_from_string(self) -> None:
        assert ScopeType("global") == ScopeType.GLOBAL
        assert ScopeType("project") == ScopeType.PROJECT
        assert ScopeType("change_order") == ScopeType.CHANGE_ORDER

    def test_invalid_scope_type(self) -> None:
        with pytest.raises(ValueError):
            ScopeType("invalid")

class TestUserRoleAssignmentEntity:
    """Tests for UserRoleAssignment model."""

    def test_create_assignment(self) -> None:
        user_id = uuid4()
        role_id = uuid4()
        assignment = UserRoleAssignment(
            user_id=user_id,
            role_id=role_id,
            scope_type=ScopeType.GLOBAL,
            scope_id=None,
        )
        assert assignment.user_id == user_id
        assert assignment.role_id == role_id
        assert assignment.scope_type == ScopeType.GLOBAL
        assert assignment.scope_id is None

    def test_create_project_scoped_assignment(self) -> None:
        user_id = uuid4()
        role_id = uuid4()
        project_id = uuid4()
        assignment = UserRoleAssignment(
            user_id=user_id,
            role_id=role_id,
            scope_type=ScopeType.PROJECT,
            scope_id=project_id,
        )
        assert assignment.scope_type == ScopeType.PROJECT
        assert assignment.scope_id == project_id

    def test_create_with_metadata(self) -> None:
        user_id = uuid4()
        role_id = uuid4()
        metadata = {"authority_level": "HIGH", "department": "Engineering"}
        assignment = UserRoleAssignment(
            user_id=user_id,
            role_id=role_id,
            scope_type=ScopeType.CHANGE_ORDER,
            scope_id=uuid4(),
            metadata_=metadata,
        )
        assert assignment.metadata_ == metadata
        assert assignment.metadata_["authority_level"] == "HIGH"

    def test_repr(self) -> None:
        user_id = uuid4()
        assignment = UserRoleAssignment(
            user_id=user_id,
            role_id=uuid4(),
            scope_type=ScopeType.GLOBAL,
        )
        repr_str = repr(assignment)
        assert "UserRoleAssignment" in repr_str
        assert str(user_id) in repr_str
        assert "global" in repr_str

    def test_granted_by_field(self) -> None:
        user_id = uuid4()
        granted_by = uuid4()
        assignment = UserRoleAssignment(
            user_id=user_id,
            role_id=uuid4(),
            scope_type=ScopeType.GLOBAL,
            granted_by=granted_by,
        )
        assert assignment.granted_by == granted_by

    def test_expires_at_field(self) -> None:
        expires = datetime(2026, 12, 31, tzinfo=UTC)
        assignment = UserRoleAssignment(
            user_id=uuid4(),
            role_id=uuid4(),
            scope_type=ScopeType.GLOBAL,
            expires_at=expires,
        )
        assert assignment.expires_at == expires

    def test_global_scope_has_null_scope_id(self) -> None:
        assignment = UserRoleAssignment(
            user_id=uuid4(),
            role_id=uuid4(),
            scope_type=ScopeType.GLOBAL,
            scope_id=None,
        )
        assert assignment.scope_id is None

    def test_change_order_scoped_assignment(self) -> None:
        co_id = uuid4()
        assignment = UserRoleAssignment(
            user_id=uuid4(),
            role_id=uuid4(),
            scope_type=ScopeType.CHANGE_ORDER,
            scope_id=co_id,
            metadata_={"authority_level": "CRITICAL"},
        )
        assert assignment.scope_type == ScopeType.CHANGE_ORDER
        assert assignment.scope_id == co_id
