"""Test that ApprovalMatrixService.get_approver_for_impact scopes to project members.

This test verifies the fix for the bug where non-existent approvers were
assigned to change orders because the approver lookup queried all users
globally instead of preferring project members.

Bug: user 85b44758-76ab-5a80-9d47-836a09d00e03 was assigned as approver
for a LOW impact CO on project 3ab811cd, but this user ID didn't exist
in the users table. The system picked a user from a different project's
seed data instead of scoping to the current project's members.
"""

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.domain.user import User
from app.services.approval_matrix_service import ApprovalMatrixService


def _make_config_service() -> AsyncMock:
    """Create a mock config service with standard role/authority mappings."""
    config_service = AsyncMock()
    config_service.get_impact_authority_mapping.return_value = {
        "LOW": "LOW",
        "MEDIUM": "MEDIUM",
        "HIGH": "HIGH",
        "CRITICAL": "CRITICAL",
    }
    config_service.get_role_authority_mapping.return_value = {
        "viewer": "LOW",
        "editor_pm": "MEDIUM",
        "dept_head": "HIGH",
        "director": "HIGH",
        "admin": "CRITICAL",
    }
    config_service.get_authority_hierarchy.return_value = {
        "LOW": 1,
        "MEDIUM": 2,
        "HIGH": 3,
        "CRITICAL": 4,
    }
    return config_service


def _make_mock_user(role: str = "admin", is_active: bool = True) -> MagicMock:
    """Create a mock User with distinct PK and root IDs."""
    mock_user = MagicMock(spec=User)
    mock_user.id = uuid4()  # PK (version identifier)
    mock_user.user_id = uuid4()  # Root (stable identifier)
    mock_user.is_active = is_active
    mock_user.role = role
    return mock_user


class TestApproverForImpactProjectMemberScoping:
    """Test that get_approver_for_impact prefers project members over global users."""

    @pytest.mark.asyncio
    async def test_prefers_project_member_over_global_user(self) -> None:
        """When a project member with sufficient authority exists, use them.

        Verifies that the first query joins project_members to scope the
        approver search to the given project.
        """
        project_member_user = _make_mock_user(role="dept_head")
        global_user = _make_mock_user(role="admin")

        mock_session = AsyncMock(spec=AsyncSession)

        # The first execute call is the project member query, which returns a result
        project_member_result = MagicMock()
        project_member_result.scalar_one_or_none.return_value = project_member_user

        mock_session.execute.return_value = project_member_result

        config_service = _make_config_service()
        service = ApprovalMatrixService(mock_session, config_service)

        project_id = uuid4()
        result = await service.get_approver_for_impact(project_id, "LOW")

        # Should return the project member's root user_id
        assert result == project_member_user.user_id
        # Should NOT return the global user
        assert result != global_user.user_id

        # Verify only one DB query was made (project member path succeeded)
        assert mock_session.execute.call_count == 1

        # Verify the query joined project_members
        executed_stmt = mock_session.execute.call_args[0][0]

        stmt_str = str(executed_stmt)
        assert "project_members" in stmt_str, (
            "Query should join project_members table to scope to project"
        )

    @pytest.mark.asyncio
    async def test_falls_back_to_global_user_when_no_project_member(
        self,
    ) -> None:
        """When no project member is eligible, fall back to any eligible user.

        Verifies that a second fallback query is executed when the project
        member query returns no results.
        """
        global_user = _make_mock_user(role="admin")

        mock_session = AsyncMock(spec=AsyncSession)

        # First call: project member query returns None
        no_result = MagicMock()
        no_result.scalar_one_or_none.return_value = None

        # Second call: fallback global query returns a user
        fallback_result = MagicMock()
        fallback_result.scalar_one_or_none.return_value = global_user

        mock_session.execute.side_effect = [no_result, fallback_result]

        config_service = _make_config_service()
        service = ApprovalMatrixService(mock_session, config_service)

        project_id = uuid4()
        result = await service.get_approver_for_impact(project_id, "LOW")

        # Should return the global fallback user's root user_id
        assert result == global_user.user_id

        # Should have made exactly 2 DB queries (project member + fallback)
        assert mock_session.execute.call_count == 2

    @pytest.mark.asyncio
    async def test_returns_none_when_no_eligible_user_anywhere(self) -> None:
        """When no eligible user exists anywhere, return None."""
        mock_session = AsyncMock(spec=AsyncSession)

        # Both queries return None
        no_result = MagicMock()
        no_result.scalar_one_or_none.return_value = None

        mock_session.execute.side_effect = [no_result, no_result]

        config_service = _make_config_service()
        service = ApprovalMatrixService(mock_session, config_service)

        result = await service.get_approver_for_impact(uuid4(), "CRITICAL")

        assert result is None
        assert mock_session.execute.call_count == 2

    @pytest.mark.asyncio
    async def test_returns_root_user_id_not_pk(self) -> None:
        """Always returns user_id (root ID), never id (PK).

        Regression test: the original bug assigned the PK id field instead
        of the stable user_id field.
        """
        mock_user = _make_mock_user(role="admin")

        mock_session = AsyncMock(spec=AsyncSession)
        result = MagicMock()
        result.scalar_one_or_none.return_value = mock_user
        mock_session.execute.return_value = result

        config_service = _make_config_service()
        service = ApprovalMatrixService(mock_session, config_service)

        approver_id = await service.get_approver_for_impact(uuid4(), "LOW")

        assert approver_id == mock_user.user_id
        assert approver_id != mock_user.id

    @pytest.mark.asyncio
    async def test_no_eligible_roles_returns_none_without_query(self) -> None:
        """When config has no eligible roles for the authority level, return None early."""
        # Config where no role maps to CRITICAL authority
        config_service = AsyncMock()
        config_service.get_impact_authority_mapping.return_value = {
            "CRITICAL": "CRITICAL",
        }
        config_service.get_role_authority_mapping.return_value = {
            "viewer": "LOW",
        }
        config_service.get_authority_hierarchy.return_value = {
            "LOW": 1,
            "CRITICAL": 4,
        }

        mock_session = AsyncMock(spec=AsyncSession)
        service = ApprovalMatrixService(mock_session, config_service)

        result = await service.get_approver_for_impact(uuid4(), "CRITICAL")

        assert result is None
        # Should NOT have queried the database at all
        mock_session.execute.assert_not_called()
