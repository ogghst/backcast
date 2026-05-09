"""Test that ApprovalMatrixService returns root user_id not PK.

This test verifies the fix for the notification schema where the service
was returning the wrong user ID (PK instead of root user_id).
"""

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.domain.user import User
from app.services.approval_matrix_service import ApprovalMatrixService


@pytest.mark.unit
class TestApprovalMatrixServiceUserIDFix:
    """Test that get_approver_for_impact returns root user_id not PK."""

    async def test_returns_root_user_id_not_pk(self) -> None:
        """Test that get_approver_for_impact returns root user_id.

        The User model has two ID fields:
        - id: Primary key (version identifier, changes with each version)
        - user_id: Root entity identifier (stable across all versions)

        Notifications should reference user_id (root) not id (PK) because
        users are versioned entities.
        """
        # Create mock user with different PK and root IDs
        mock_user = MagicMock(spec=User)
        mock_user.id = uuid4()  # PK (version identifier)
        mock_user.user_id = uuid4()  # Root (stable identifier)
        mock_user.is_active = True
        mock_user.role = "admin"

        # Create mock database session
        mock_session = AsyncMock(spec=AsyncSession)

        # Setup mock to return our user
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_user
        mock_session.execute.return_value = mock_result

        # Create service with mock config
        config_service = AsyncMock()
        config_service.get_impact_authority_mapping.return_value = {"HIGH": "HIGH"}
        config_service.get_role_authority_mapping.return_value = {"admin": "HIGH"}
        config_service.get_authority_hierarchy.return_value = {
            "LOW": 1,
            "MEDIUM": 2,
            "HIGH": 3,
            "CRITICAL": 4,
        }

        service = ApprovalMatrixService(mock_session, config_service)

        # Call the method
        result = await service.get_approver_for_impact(uuid4(), "HIGH")

        # CRITICAL ASSERTION: Must return root user_id, NOT PK
        assert result == mock_user.user_id, (
            f"Expected root user_id ({mock_user.user_id}), but got PK ({mock_user.id})"
        )
        assert result != mock_user.id, (
            "Should return root user_id, not primary key (id)"
        )

    async def test_returns_none_when_no_approver_found(self) -> None:
        """Test that None is returned when no eligible approver exists."""
        # Create mock database session
        mock_session = AsyncMock(spec=AsyncSession)

        # Setup mock to return None (no user found)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        config_service = AsyncMock()
        config_service.get_impact_authority_mapping.return_value = {"HIGH": "HIGH"}
        config_service.get_role_authority_mapping.return_value = {"admin": "HIGH"}
        config_service.get_authority_hierarchy.return_value = {
            "LOW": 1,
            "MEDIUM": 2,
            "HIGH": 3,
            "CRITICAL": 4,
        }

        service = ApprovalMatrixService(mock_session, config_service)

        result = await service.get_approver_for_impact(uuid4(), "HIGH")

        assert result is None
