"""Tests for BranchableService.get_as_of() with empty valid_time ranges.

Regression test for BUG-2: The time-travel path (as_of is provided) was missing
the `NOT isempty(valid_time)` check that the current-version path already had.
This allowed empty-range versions (created during soft-delete / resubmission flows)
to be returned instead of the correct non-empty version.
"""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.branching.service import BranchableService
from app.core.versioning.commands import CreateVersionCommand
from app.models.domain.wbe import WBE


class TestGetAsOfEmptyValidTime:
    """Tests ensuring get_as_of never returns empty-range versions."""

    @pytest.mark.asyncio
    async def test_get_as_of_with_as_of_excludes_empty_valid_time(
        self, db_session: AsyncSession
    ) -> None:
        """BUG-2 regression: time-travel path must exclude empty valid_time ranges.

        Arrange:
            - Create a WBE version V1 with valid_time = [Now-10d, Infinity)
            - Insert a second version V2 with valid_time = empty and deleted_at set
              on the same root_id and branch, with open transaction_time.
              The deleted_at is set so the partial unique index (which filters
              deleted_at IS NULL) is not violated.
        Act:
            - Call get_as_of(root_id, as_of=datetime.now(UTC), branch="main")
        Assert:
            - V1 (non-empty range) is returned, NOT V2 (empty range).
        """
        root_id = uuid4()
        actor_id = uuid4()
        now = datetime.now(UTC)

        # 1. Create V1: a normal WBE with valid_time covering NOW
        v1 = await CreateVersionCommand(
            entity_class=WBE,
            root_id=root_id,
            actor_id=actor_id,
            control_date=now - timedelta(days=10),
            name="Valid Version",
            code="WBE-EMPTY-TEST",
            project_id=uuid4(),
            level=1,
            branch="main",
        ).execute(db_session)

        # 2. Insert V2 with an empty valid_time range via raw SQL.
        #    deleted_at is set to a future time so the version passes the
        #    deleted_at coalesce check in get_as_of but still violates the
        #    unique constraint exclusion. This simulates a residual zombie
        #    version from soft-delete / resubmission flows.
        v2_id = uuid4()
        future = now + timedelta(days=365)
        await db_session.execute(
            text("""
                INSERT INTO wbes (
                    id, wbe_id, project_id, code, name, level,
                    valid_time, transaction_time,
                    created_by, branch, parent_id, deleted_at, deleted_by
                ) VALUES (
                    :id, :wbe_id, :project_id, :code, :name, :level,
                    'empty'::tstzrange,
                    tstzrange(:tx_start, NULL, '[)'),
                    :created_by, :branch, :parent_id, :deleted_at, :deleted_by
                )
            """),
            {
                "id": v2_id,
                "wbe_id": root_id,
                "project_id": v1.project_id,
                "code": "WBE-EMPTY-TEST",
                "name": "Empty Range Zombie",
                "level": 1,
                "tx_start": now,
                "created_by": actor_id,
                "branch": "main",
                "parent_id": None,
                "deleted_at": future,
                "deleted_by": actor_id,
            },
        )
        await db_session.flush()

        # 3. Act: query with as_of (time-travel path)
        service = BranchableService(WBE, db_session)
        result = await service.get_as_of(
            entity_id=root_id,
            as_of=now,
            branch="main",
        )

        # 4. Assert: the normal version V1 is returned, not the empty-range V2
        assert result is not None
        assert result.id == v1.id
        assert result.name == "Valid Version"

    @pytest.mark.asyncio
    async def test_get_as_of_without_as_of_excludes_empty_valid_time(
        self, db_session: AsyncSession
    ) -> None:
        """Confirm the current-version path (as_of=None) already excludes empty ranges.

        This is a baseline test confirming the existing behavior is correct,
        and should pass even before the BUG-2 fix.
        """
        root_id = uuid4()
        actor_id = uuid4()
        now = datetime.now(UTC)

        # 1. Create V1 with valid_time covering NOW
        v1 = await CreateVersionCommand(
            entity_class=WBE,
            root_id=root_id,
            actor_id=actor_id,
            control_date=now - timedelta(days=10),
            name="Valid Version",
            code="WBE-EMPTY-TEST2",
            project_id=uuid4(),
            level=1,
            branch="main",
        ).execute(db_session)

        # 2. Insert V2 with empty valid_time and deleted_at (zombie)
        v2_id = uuid4()
        future = now + timedelta(days=365)
        await db_session.execute(
            text("""
                INSERT INTO wbes (
                    id, wbe_id, project_id, code, name, level,
                    valid_time, transaction_time,
                    created_by, branch, parent_id, deleted_at, deleted_by
                ) VALUES (
                    :id, :wbe_id, :project_id, :code, :name, :level,
                    'empty'::tstzrange,
                    tstzrange(:tx_start, NULL, '[)'),
                    :created_by, :branch, :parent_id, :deleted_at, :deleted_by
                )
            """),
            {
                "id": v2_id,
                "wbe_id": root_id,
                "project_id": v1.project_id,
                "code": "WBE-EMPTY-TEST2",
                "name": "Empty Range Zombie",
                "level": 1,
                "tx_start": now,
                "created_by": actor_id,
                "branch": "main",
                "parent_id": None,
                "deleted_at": future,
                "deleted_by": actor_id,
            },
        )
        await db_session.flush()

        # 3. Act: query without as_of (current-version path)
        service = BranchableService(WBE, db_session)
        result = await service.get_as_of(
            entity_id=root_id,
            as_of=None,
            branch="main",
        )

        # 4. Assert: V1 is returned, not V2
        assert result is not None
        assert result.id == v1.id
        assert result.name == "Valid Version"

    @pytest.mark.asyncio
    async def test_get_as_of_with_as_of_returns_none_when_only_empty_range_exists(
        self, db_session: AsyncSession
    ) -> None:
        """BUG-2 edge case: if only an empty-range version exists, get_as_of returns None.

        Arrange:
            - Insert a single version with empty valid_time and deleted_at on a root_id.
        Act:
            - Call get_as_of(root_id, as_of=now, branch="main").
        Assert:
            - Returns None (no valid version covers the requested timestamp).
        """
        root_id = uuid4()
        actor_id = uuid4()
        now = datetime.now(UTC)
        project_id = uuid4()
        future = now + timedelta(days=365)

        # Insert ONLY an empty-range version (deleted_at set to bypass unique constraint)
        await db_session.execute(
            text("""
                INSERT INTO wbes (
                    id, wbe_id, project_id, code, name, level,
                    valid_time, transaction_time,
                    created_by, branch, parent_id, deleted_at, deleted_by
                ) VALUES (
                    :id, :wbe_id, :project_id, :code, :name, :level,
                    'empty'::tstzrange,
                    tstzrange(:tx_start, NULL, '[)'),
                    :created_by, :branch, :parent_id, :deleted_at, :deleted_by
                )
            """),
            {
                "id": uuid4(),
                "wbe_id": root_id,
                "project_id": project_id,
                "code": "WBE-ONLY-EMPTY",
                "name": "Only Empty Range",
                "level": 1,
                "tx_start": now,
                "created_by": actor_id,
                "branch": "main",
                "parent_id": None,
                "deleted_at": future,
                "deleted_by": actor_id,
            },
        )
        await db_session.flush()

        # Act: query with as_of
        service = BranchableService(WBE, db_session)
        result = await service.get_as_of(
            entity_id=root_id,
            as_of=now,
            branch="main",
        )

        # Assert: no valid version found
        assert result is None
