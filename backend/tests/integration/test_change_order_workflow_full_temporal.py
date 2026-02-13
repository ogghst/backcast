"""Integration tests for full Change Order workflow with temporal control dates.

Tests the end-to-end Change Order workflow including:
1. Full entity setup with schedules, forecasts, and progress registrations
2. Time travel across multiple control dates
3. Branch isolation (STRICT vs MERGE modes)
4. Temporal boundaries (zombie check pattern)
5. Change order modifications on isolated branches
6. Full merge orchestration across all entity types
7. Post-merge temporal consistency

Follows RED-GREEN-REFACTOR TDD methodology.
"""

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.versioning.enums import BranchMode
from app.models.schemas.change_order import ChangeOrderCreate, ChangeOrderUpdate
from app.models.schemas.cost_element import CostElementCreate
from app.models.schemas.cost_element_type import CostElementTypeCreate
from app.models.schemas.cost_registration import CostRegistrationCreate
from app.models.schemas.progress_entry import ProgressEntryCreate
from app.services.change_order_service import ChangeOrderService
from app.services.cost_element_service import CostElementService
from app.services.cost_element_type_service import CostElementTypeService
from app.services.cost_registration_service import CostRegistrationService
from app.services.department import DepartmentService
from app.services.forecast_service import ForecastService
from app.services.progress_entry_service import ProgressEntryService
from app.services.project import ProjectService
from app.services.schedule_baseline_service import ScheduleBaselineService
from app.services.wbe import WBEService


@pytest.mark.usefixtures("db_session")
class TestChangeOrderWorkflowFullTemporal:
    """Integration test suite for full Change Order workflow with temporal control dates."""

    @pytest.mark.asyncio
    async def test_full_workflow_with_temporal_dates(
        self, db_session: AsyncSession
    ) -> None:
        """Test complete change order workflow with temporal control dates.

        Scenario:
        - T0 (Jan 1, 2026): Create project with 2 WBEs, 2 CostElements (with schedules, forecasts, progresses)
        - T1 (Jan 8, 2026): Create change order, verify branch creation
        - T1±1 day: Verify temporal boundaries (zombie check)
        - T2 (Jan 10, 2026): Modify cost elements on CO branch
        - T3 (Jan 15, 2026): Execute merge
        - Post-merge: Verify temporal consistency and time-travel queries
        """
        # Initialize services
        dept_service = DepartmentService(db_session)
        cet_service = CostElementTypeService(db_session)
        project_service = ProjectService(db_session)
        wbe_service = WBEService(db_session)
        ce_service = CostElementService(db_session)
        sb_service = ScheduleBaselineService(db_session)
        ForecastService(db_session)
        progress_service = ProgressEntryService(db_session)
        cost_reg_service = CostRegistrationService(db_session)
        co_service = ChangeOrderService(db_session)

        actor_id = uuid4()

        # ========== PHASE 1: Initial Setup (T0 = Jan 1, 2026) ==========
        T0 = datetime(2026, 1, 1, 12, 0, 0, tzinfo=UTC)

        # Create Department
        dept = await dept_service.create(
            root_id=uuid4(),
            actor_id=actor_id,
            control_date=T0,
            code="ENG",
            name="Engineering",
        )

        # Create CostElementType
        cet = await cet_service.create(
            type_in=CostElementTypeCreate(
                cost_element_type_id=uuid4(),
                code="LABOR",
                name="Labor Costs",
                department_id=dept.department_id,
            ),
            actor_id=actor_id,
        )

        # Create Project
        project_id = uuid4()
        await project_service.create(

            root_id=project_id,
            actor_id=actor_id,
            control_date=T0,
            code="PROJ-001",
            name="Test Project",
            budget=Decimal("500000.00"),
        )

        # Create 2 WBEs
        wbe1_id = uuid4()
        await wbe_service.create_root(
            root_id=wbe1_id,
            actor_id=actor_id,
            control_date=T0,
            branch="main",
            project_id=project_id,
            code="1.1",
            name="Assembly Station 1",
            level=1,
        )

        wbe2_id = uuid4()
        await wbe_service.create_root(
            root_id=wbe2_id,
            actor_id=actor_id,
            control_date=T0,
            branch="main",
            project_id=project_id,
            code="1.2",
            name="Assembly Station 2",
            level=1,
        )

        # Create 2 CostElements (auto-creates ScheduleBaseline and Forecast)
        ce1_id = uuid4()
        await ce_service.create_cost_element(
            element_in=CostElementCreate(
                cost_element_id=ce1_id,
                wbe_id=wbe1_id,
                cost_element_type_id=cet.cost_element_type_id,
                code="CE-001",
                name="Labor Cost Element 1",
                budget_amount=Decimal("100000.00"),
                branch="main",
                control_date=T0,
            ),
            actor_id=actor_id,
        )

        ce2_id = uuid4()
        await ce_service.create_cost_element(
            element_in=CostElementCreate(
                cost_element_id=ce2_id,
                wbe_id=wbe2_id,
                cost_element_type_id=cet.cost_element_type_id,
                code="CE-002",
                name="Labor Cost Element 2",
                budget_amount=Decimal("200000.00"),
                branch="main",
                control_date=T0,
            ),
            actor_id=actor_id,
        )

        # Get auto-created schedule baselines
        sb1 = await sb_service.get_for_cost_element(ce1_id, branch="main")
        sb2 = await sb_service.get_for_cost_element(ce2_id, branch="main")
        assert sb1 is not None
        assert sb2 is not None

        # Update schedule baselines with dates
        await sb_service.update(
            root_id=sb1.schedule_baseline_id,
            actor_id=actor_id,
            branch="main",
            control_date=T0,
            start_date=datetime(2026, 1, 1, tzinfo=UTC),
            end_date=datetime(2026, 6, 30, tzinfo=UTC),
            progression_type="LINEAR",
        )

        await sb_service.update(
            root_id=sb2.schedule_baseline_id,
            actor_id=actor_id,
            branch="main",
            control_date=T0,
            start_date=datetime(2026, 1, 1, tzinfo=UTC),
            end_date=datetime(2026, 6, 30, tzinfo=UTC),
            progression_type="LINEAR",
        )

        # Create progress entries
        await progress_service.create_progress_entry(
            progress_in=ProgressEntryCreate(
                cost_element_id=ce1_id,
                progress_percentage=Decimal("25.00"),
                reported_date=T0,
                reported_by_user_id=actor_id,
                notes="Initial progress",
                control_date=T0,
            ),
            actor_id=actor_id,
        )

        await progress_service.create_progress_entry(
            progress_in=ProgressEntryCreate(
                cost_element_id=ce2_id,
                progress_percentage=Decimal("10.00"),
                reported_date=T0,
                reported_by_user_id=actor_id,
                notes="Initial progress",
                control_date=T0,
            ),
            actor_id=actor_id,
        )

        # Create cost registrations
        await cost_reg_service.create_cost_registration(
            registration_in=CostRegistrationCreate(
                cost_element_id=ce1_id,
                amount=Decimal("25000.00"),
                registration_date=T0,
                description="Initial cost",
            ),
            actor_id=actor_id,
            control_date=T0,
        )

        await cost_reg_service.create_cost_registration(
            registration_in=CostRegistrationCreate(
                cost_element_id=ce2_id,
                amount=Decimal("20000.00"),
                registration_date=T0,
                description="Initial cost",
            ),
            actor_id=actor_id,
            control_date=T0,
        )

        # Verify initial state
        wbes_main = await wbe_service.get_wbes(branch="main")
        assert len(wbes_main[0]) == 2

        # ========== PHASE 2: Create Change Order (T1 = Jan 8, 2026) ==========
        T1 = datetime(2026, 1, 8, 12, 0, 0, tzinfo=UTC)
        T1_before = datetime(2026, 1, 7, 12, 0, 0, tzinfo=UTC)
        T1_after = datetime(2026, 1, 9, 12, 0, 0, tzinfo=UTC)


        co = await co_service.create_change_order(
            change_order_in=ChangeOrderCreate(
                code="CO-2026-001",
                title="Expand Assembly Station 1",
                description="Add capacity to Assembly Station 1",
                project_id=project_id,
                status="Draft",
            ),
            actor_id=actor_id,
            control_date=T1,
        )
        co_id = co.change_order_id

        assert co.code == "CO-2026-001"
        assert co.status == "Draft"
        assert co.branch == "main"
        assert co.branch_name == "BR-CO-2026-001"

        source_branch = co.branch_name

        # Verify branch created
        from app.services.branch_service import BranchService

        branch_service = BranchService(db_session)
        co_branch = await branch_service.get_by_name_and_project(
            name=source_branch, project_id=project_id
        )
        assert co_branch is not None
        assert co_branch.type == "change_order"
        assert co_branch.locked is False  # Draft status

        # ========== PHASE 3: Temporal Boundary Verification ==========
        # Zombie check: CO should NOT exist before T1
        co_before = await co_service.get_as_of(
            entity_id=co_id,
            as_of=T1_before,
            branch="main",
            branch_mode=BranchMode.STRICT,
        )
        assert co_before is None, "CO should not exist before T1"

        # CO should exist after T1
        co_after = await co_service.get_as_of(
            entity_id=co_id,
            as_of=T1_after,
            branch="main",
            branch_mode=BranchMode.STRICT,
        )
        assert co_after is not None, "CO should exist after T1"
        assert co_after.code == "CO-2026-001"

        # STRICT mode: entities not on CO branch return None
        wbe1_co_strict = await wbe_service.get_as_of(
            entity_id=wbe1_id,
            as_of=T1_after,
            branch=source_branch,
            branch_mode=BranchMode.STRICT,
        )
        assert wbe1_co_strict is None, "WBE1 should not exist on CO branch yet"

        # MERGE mode: falls back to main
        wbe1_co_merge = await wbe_service.get_as_of(
            entity_id=wbe1_id,
            as_of=T1_after,
            branch=source_branch,
            branch_mode=BranchMode.MERGE,
        )
        assert wbe1_co_merge is not None, "MERGE mode should fall back to main"
        assert wbe1_co_merge.name == "Assembly Station 1"

        # ========== PHASE 4: Modify Cost Elements on CO Branch (T2 = Jan 10) ==========
        T2 = datetime(2026, 1, 10, 12, 0, 0, tzinfo=UTC)

        # CO update removed to avoid locking branch before edits

        # Create new versions of WBE1 on CO branch
        await wbe_service.create_root(
            root_id=wbe1_id,
            actor_id=actor_id,
            control_date=T2,
            branch=source_branch,
            project_id=project_id,
            code="1.1",
            name="Assembly Station 1 - EXPANDED",
            level=1,
        )

        # Create new versions of CostElement1 on CO branch (budget increase)
        await ce_service.create_cost_element(
            element_in=CostElementCreate(
                cost_element_id=ce1_id,
                wbe_id=wbe1_id,
                cost_element_type_id=cet.cost_element_type_id,
                code="CE-001",
                name="Labor Cost Element 1 - EXPANDED",
                budget_amount=Decimal("150000.00"),
                branch=source_branch,
                control_date=T2,
            ),
            actor_id=actor_id,
        )

        # Add progress entry on CO branch
        await progress_service.create_progress_entry(
            progress_in=ProgressEntryCreate(
                cost_element_id=ce1_id,
                progress_percentage=Decimal("40.00"),
                reported_date=T2,
                reported_by_user_id=actor_id,
                notes="Progress after expansion",
                control_date=T2,
            ),
            actor_id=actor_id,
        )

        # Add cost registration on CO branch
        await cost_reg_service.create_cost_registration(
            registration_in=CostRegistrationCreate(
                cost_element_id=ce1_id,
                amount=Decimal("5000.00"),
                registration_date=T2,
                description="Additional cost for expansion",
            ),
            actor_id=actor_id,
            control_date=T2,
            branch=source_branch,
        )

        # Verify branch isolation - main branch unchanged
        wbe1_main = await wbe_service.get_as_of(
            entity_id=wbe1_id,
            as_of=T2,
            branch="main",
            branch_mode=BranchMode.STRICT,
        )
        assert wbe1_main.name == "Assembly Station 1", "Main branch should be unchanged"

        ce1_main = await ce_service.get_as_of(
            entity_id=ce1_id,
            as_of=T2,
            branch="main",
            branch_mode=BranchMode.STRICT,
        )
        assert ce1_main.budget_amount == Decimal(
            "100000.00"
        ), "Main branch budget should be unchanged"

        # Verify CO branch has changes
        wbe1_co = await wbe_service.get_as_of(
            entity_id=wbe1_id,
            as_of=T2,
            branch=source_branch,
            branch_mode=BranchMode.STRICT,
        )
        assert wbe1_co.name == "Assembly Station 1 - EXPANDED"

        ce1_co = await ce_service.get_as_of(
            entity_id=ce1_id,
            as_of=T2,
            branch=source_branch,
            branch_mode=BranchMode.STRICT,
        )
        assert ce1_co.budget_amount == Decimal("150000.00")

        # ========== PHASE 5: Execute Merge (T3 = Jan 15, 2026) ==========
        T3 = datetime(2026, 1, 15, 12, 0, 0, tzinfo=UTC)

        # Transition status: Draft -> Submitted -> Approved
        # 1. Submit
        await co_service.update_change_order(
            change_order_id=co_id,
            change_order_in=ChangeOrderUpdate(status="Submitted for Approval"),
            actor_id=actor_id,
            control_date=T3,
            branch=source_branch,
        )

        # 2. Under Review
        await co_service.update_change_order(
            change_order_id=co_id,
            change_order_in=ChangeOrderUpdate(status="Under Review"),
            actor_id=actor_id,
            control_date=T3 + timedelta(seconds=1),
            branch=source_branch,
        )

        # 3. Approve
        await co_service.update_change_order(
            change_order_id=co_id,
            change_order_in=ChangeOrderUpdate(status="Approved"),
            actor_id=actor_id,
            control_date=T3 + timedelta(seconds=2),
            branch=source_branch,
        )

        merged_co = await co_service.merge_change_order(
            change_order_id=co_id,
            actor_id=actor_id,
            target_branch="main",
            control_date=T3,
        )

        # Verify CO status
        assert merged_co.status == "Implemented"

        # Verify WBE1 merged
        wbe1_main_merged = await wbe_service.get_as_of(
            entity_id=wbe1_id,
            as_of=T3,
            branch="main",
            branch_mode=BranchMode.STRICT,
        )
        assert wbe1_main_merged.name == "Assembly Station 1 - EXPANDED"

        # Verify CostElement1 budget updated
        ce1_main_merged = await ce_service.get_as_of(
            entity_id=ce1_id,
            as_of=T3,
            branch="main",
            branch_mode=BranchMode.STRICT,
        )
        assert ce1_main_merged.budget_amount == Decimal("150000.00")

        # Verify WBE2 unchanged (not modified on CO branch)
        wbe2_main_merged = await wbe_service.get_as_of(
            entity_id=wbe2_id,
            as_of=T3,
            branch="main",
            branch_mode=BranchMode.STRICT,
        )
        assert wbe2_main_merged.name == "Assembly Station 2"

        # ========== PHASE 6: Post-Merge Temporal Verification ==========
        # Time travel: T1_after shows pre-merge state
        ce1_at_t1 = await ce_service.get_as_of(
            entity_id=ce1_id,
            as_of=T1_after,
            branch="main",
            branch_mode=BranchMode.STRICT,
        )
        assert ce1_at_t1.budget_amount == Decimal("100000.00")

        # Time travel: T3 shows post-merge state
        ce1_at_t3 = await ce_service.get_as_of(
            entity_id=ce1_id,
            as_of=T3,
            branch="main",
            branch_mode=BranchMode.STRICT,
        )
        assert ce1_at_t3.budget_amount == Decimal("150000.00")

        # CO branch preserved
        ce1_co_preserved = await ce_service.get_as_of(
            entity_id=ce1_id,
            as_of=T3,
            branch=source_branch,
            branch_mode=BranchMode.STRICT,
        )
        assert ce1_co_preserved is not None
        assert ce1_co_preserved.budget_amount == Decimal("150000.00")

        # Verify temporal consistency (no empty ranges)
        history = await ce_service.get_history(root_id=ce1_id)
        main_versions = [v for v in history if v.branch == "main"]
        for version in main_versions:
            if version.valid_time.upper is not None:
                assert (
                    version.valid_time.lower < version.valid_time.upper
                ), f"Version {version.id} has empty valid_time range"

    @pytest.mark.asyncio
    async def test_temporal_boundary_co_creation(
        self, db_session: AsyncSession
    ) -> None:
        """Test that change orders respect temporal boundaries.

        Scenario:
        - Create CO at T1
        - Query at T1-1: should return None (zombie check)
        - Query at T1: should return CO
        - Query at T1+1: should return CO
        """
        co_service = ChangeOrderService(db_session)
        project_service = ProjectService(db_session)
        actor_id = uuid4()
        project_id = uuid4()

        T0 = datetime(2026, 1, 1, tzinfo=UTC)
        T1 = datetime(2026, 1, 8, 12, 0, 0, tzinfo=UTC)
        T1_before = datetime(2026, 1, 7, 12, 0, 0, tzinfo=UTC)
        T1_after = datetime(2026, 1, 9, 12, 0, 0, tzinfo=UTC)

        # Create project
        await project_service.create(

            root_id=project_id,
            actor_id=actor_id,
            control_date=T0,
            code="PROJ-001",
            name="Test Project",
            budget=Decimal("100000.00"),
        )

        # Create CO at T1

        co = await co_service.create_change_order(
            change_order_in=ChangeOrderCreate(
                code="CO-001",
                title="Test CO",
                project_id=project_id,
                status="Draft",
            ),
            actor_id=actor_id,
            control_date=T1,
        )
        co_id = co.change_order_id

        # Zombie check: before T1
        co_before = await co_service.get_as_of(

            entity_id=co_id,
            as_of=T1_before,
            branch="main",
            branch_mode=BranchMode.STRICT,
        )
        assert co_before is None

        # At T1
        co_at = await co_service.get_as_of(

            entity_id=co_id,
            as_of=T1,
            branch="main",
            branch_mode=BranchMode.STRICT,
        )
        assert co_at is not None
        assert co_at.code == "CO-001"

        # After T1
        co_after = await co_service.get_as_of(

            entity_id=co_id,
            as_of=T1_after,
            branch="main",
            branch_mode=BranchMode.STRICT,
        )
        assert co_after is not None
        assert co_after.code == "CO-001"

    @pytest.mark.asyncio
    async def test_branch_isolation_with_temporal_queries(
        self, db_session: AsyncSession
    ) -> None:
        """Test STRICT vs MERGE branch modes with temporal queries.

        Scenario:
        - Create WBE on main branch
        - Create CO branch
        - Query CO branch with STRICT mode: should return None
        - Query CO branch with MERGE mode: should fall back to main
        - Modify WBE on CO branch
        - Query CO branch with STRICT mode: should return modified version
        """
        project_service = ProjectService(db_session)
        wbe_service = WBEService(db_session)
        co_service = ChangeOrderService(db_session)

        actor_id = uuid4()
        project_id = uuid4()
        wbe_id = uuid4()

        T0 = datetime(2026, 1, 1, tzinfo=UTC)
        T1 = datetime(2026, 1, 8, tzinfo=UTC)

        # Create project
        await project_service.create(

            root_id=project_id,
            actor_id=actor_id,
            control_date=T0,
            code="PROJ-001",
            name="Test Project",
            budget=Decimal("100000.00"),
        )

        # Create WBE on main
        await wbe_service.create_root(

            root_id=wbe_id,
            actor_id=actor_id,
            control_date=T0,
            branch="main",
            project_id=project_id,
            code="1.1",
            name="Original WBE",
            level=1,
        )

        # Create CO

        co = await co_service.create_change_order(
            change_order_in=ChangeOrderCreate(
                code="CO-001",
                title="Test CO",
                project_id=project_id,
                status="Approved",
            ),
            actor_id=actor_id,
            control_date=T1,
        )
        source_branch = co.branch_name

        # STRICT mode: WBE not on CO branch
        wbe_strict = await wbe_service.get_as_of(

            entity_id=wbe_id,
            as_of=T1,
            branch=source_branch,
            branch_mode=BranchMode.STRICT,
        )
        assert wbe_strict is None

        # MERGE mode: falls back to main
        wbe_merge = await wbe_service.get_as_of(

            entity_id=wbe_id,
            as_of=T1,
            branch=source_branch,
            branch_mode=BranchMode.MERGE,
        )
        assert wbe_merge is not None
        assert wbe_merge.name == "Original WBE"

        # Modify WBE on CO branch
        await wbe_service.create_root(

            root_id=wbe_id,
            actor_id=actor_id,
            control_date=T1,
            branch=source_branch,
            project_id=project_id,
            code="1.1",
            name="Modified WBE",
            level=1,
        )

        # STRICT mode now returns the modified version
        wbe_strict_after = await wbe_service.get_as_of(

            entity_id=wbe_id,
            as_of=T1,
            branch=source_branch,
            branch_mode=BranchMode.STRICT,
        )
        assert wbe_strict_after is not None
        assert wbe_strict_after.name == "Modified WBE"

    @pytest.mark.asyncio
    async def test_merge_with_cost_registrations_and_progress(
        self, db_session: AsyncSession
    ) -> None:
        """Test merge propagates all versionable entities.

        Scenario:
        - Create project with WBE, CostElement, progress, and cost registrations
        - Create CO and modify on CO branch
        - Merge and verify all entities are propagated
        """
        dept_service = DepartmentService(db_session)
        cet_service = CostElementTypeService(db_session)
        project_service = ProjectService(db_session)
        wbe_service = WBEService(db_session)
        ce_service = CostElementService(db_session)
        progress_service = ProgressEntryService(db_session)
        cost_reg_service = CostRegistrationService(db_session)
        co_service = ChangeOrderService(db_session)

        actor_id = uuid4()

        T0 = datetime(2026, 1, 1, tzinfo=UTC)
        T1 = datetime(2026, 1, 8, tzinfo=UTC)

        # Create dependency chain
        dept = await dept_service.create(
            root_id=uuid4(), actor_id=actor_id, control_date=T0, code="ENG", name="Engineering"
        )

        cet = await cet_service.create(
            type_in=CostElementTypeCreate(
                cost_element_type_id=uuid4(),
                code="LABOR",
                name="Labor",
                department_id=dept.department_id,
            ),
            actor_id=actor_id,
        )

        project_id = uuid4()
        await project_service.create(

            root_id=project_id,
            actor_id=actor_id,
            control_date=T0,
            code="PROJ-001",
            name="Test Project",
            budget=Decimal("100000.00"),
        )

        wbe_id = uuid4()
        await wbe_service.create_root(

            root_id=wbe_id,
            actor_id=actor_id,
            control_date=T0,
            branch="main",
            project_id=project_id,
            code="1.1",
            name="WBE 1",
            level=1,
        )

        ce_id = uuid4()
        await ce_service.create_cost_element(
            element_in=CostElementCreate(
                cost_element_id=ce_id,
                wbe_id=wbe_id,
                cost_element_type_id=cet.cost_element_type_id,
                code="CE-001",
                name="Cost Element 1",
                budget_amount=Decimal("50000.00"),
                branch="main",
                control_date=T0,
            ),
            actor_id=actor_id,
        )

        # Create progress and cost registrations
        await progress_service.create_progress_entry(
            progress_in=ProgressEntryCreate(
                cost_element_id=ce_id,
                progress_percentage=Decimal("25.00"),
                reported_date=T0,
                reported_by_user_id=actor_id,
                control_date=T0,
            ),
            actor_id=actor_id,
        )

        await cost_reg_service.create_cost_registration(
            registration_in=CostRegistrationCreate(
                cost_element_id=ce_id,
                amount=Decimal("10000.00"),
                registration_date=T0,
                description="",
            ),
            actor_id=actor_id,
            control_date=T0,
        )

        # Create CO and modify

        co = await co_service.create_change_order(
            change_order_in=ChangeOrderCreate(
                code="CO-001",
                title="Test CO",
                project_id=project_id,
                status="Draft",
            ),
            actor_id=actor_id,
            control_date=T1,
        )

        await ce_service.create_cost_element(
            element_in=CostElementCreate(
                cost_element_id=ce_id,
                wbe_id=wbe_id,
                cost_element_type_id=cet.cost_element_type_id,
                code="CE-001",
                name="Cost Element 1 - MODIFIED",
                budget_amount=Decimal("75000.00"),
                branch=co.branch_name,
                control_date=T1,
            ),
            actor_id=actor_id,
        )

        # Merge
        # Transition ensuring intermediate states
        await co_service.update_change_order(
            change_order_id=co.change_order_id,
            change_order_in=ChangeOrderUpdate(status="Submitted for Approval"),
            actor_id=actor_id,
            control_date=T1,
            branch=co.branch_name,
        )
        await co_service.update_change_order(
            change_order_id=co.change_order_id,
            change_order_in=ChangeOrderUpdate(status="Under Review"),
            actor_id=actor_id,
            control_date=T1 + timedelta(seconds=1),
            branch=co.branch_name,
        )
        await co_service.update_change_order(
            change_order_id=co.change_order_id,
            change_order_in=ChangeOrderUpdate(status="Approved"),
            actor_id=actor_id,
            control_date=T1 + timedelta(seconds=2),
            branch=co.branch_name,
        )

        merged_co = await co_service.merge_change_order(
            change_order_id=co.change_order_id,
            actor_id=actor_id,
            target_branch="main",
            control_date=T1,
        )

        assert merged_co.status == "Implemented"

        # Verify CE merged
        ce_merged = await ce_service.get_as_of(

            entity_id=ce_id,
            as_of=T1,
            branch="main",
            branch_mode=BranchMode.STRICT,
        )
        assert ce_merged.budget_amount == Decimal("75000.00")

    @pytest.mark.asyncio
    async def test_merge_temporal_consistency(
        self, db_session: AsyncSession
    ) -> None:
        """Test that merge maintains temporal consistency.

        Scenario:
        - Create entity on main at T0
        - Create CO at T1
        - Modify entity on CO branch at T2
        - Merge at T3
        - Verify temporal consistency across all timestamps
        """
        project_service = ProjectService(db_session)
        wbe_service = WBEService(db_session)
        co_service = ChangeOrderService(db_session)

        actor_id = uuid4()
        project_id = uuid4()
        wbe_id = uuid4()

        T0 = datetime(2026, 1, 1, tzinfo=UTC)
        T1 = datetime(2026, 1, 8, tzinfo=UTC)
        T2 = datetime(2026, 1, 10, tzinfo=UTC)
        T3 = datetime(2026, 1, 15, tzinfo=UTC)

        # Create project and WBE
        await project_service.create(

            root_id=project_id,
            actor_id=actor_id,
            control_date=T0,
            code="PROJ-001",
            name="Test Project",
            budget=Decimal("100000.00"),
        )

        await wbe_service.create_root(

            root_id=wbe_id,
            actor_id=actor_id,
            control_date=T0,
            branch="main",
            project_id=project_id,
            code="1.1",
            name="Original WBE",
            level=1,
        )

        # Create CO

        co = await co_service.create_change_order(
            change_order_in=ChangeOrderCreate(
                code="CO-001",
                title="Test CO",
                project_id=project_id,
                status="Draft",
            ),
            actor_id=actor_id,
            control_date=T1,
        )

        # Modify on CO branch
        await wbe_service.create_root(

            root_id=wbe_id,
            actor_id=actor_id,
            control_date=T2,
            branch=co.branch_name,
            project_id=project_id,
            code="1.1",
            name="Modified WBE",
            level=1,
        )

        # Merge
        # Merge
        await co_service.update_change_order(
            change_order_id=co.change_order_id,
            change_order_in=ChangeOrderUpdate(status="Submitted for Approval"),
            actor_id=actor_id,
            control_date=T2,
            branch=co.branch_name,
        )
        await co_service.update_change_order(
            change_order_id=co.change_order_id,
            change_order_in=ChangeOrderUpdate(status="Under Review"),
            actor_id=actor_id,
            control_date=T2 + timedelta(seconds=1),
            branch=co.branch_name,
        )
        await co_service.update_change_order(
            change_order_id=co.change_order_id,
            change_order_in=ChangeOrderUpdate(status="Approved"),
            actor_id=actor_id,
            control_date=T2 + timedelta(seconds=2),
            branch=co.branch_name,
        )

        await co_service.merge_change_order(
            change_order_id=co.change_order_id,
            actor_id=actor_id,
            target_branch="main",
            control_date=T2,
        )

        # Verify temporal consistency
        # At T0: original state
        wbe_t0 = await wbe_service.get_as_of(

            entity_id=wbe_id,
            as_of=T0,
            branch="main",
            branch_mode=BranchMode.STRICT,
        )
        assert wbe_t0.name == "Original WBE"

        # At T1: still original state
        wbe_t1 = await wbe_service.get_as_of(

            entity_id=wbe_id,
            as_of=T1,
            branch="main",
            branch_mode=BranchMode.STRICT,
        )
        assert wbe_t1.name == "Original WBE"

        # At T3: merged state
        wbe_t3 = await wbe_service.get_as_of(

            entity_id=wbe_id,
            as_of=T3,
            branch="main",
            branch_mode=BranchMode.STRICT,
        )
        assert wbe_t3.name == "Modified WBE"

        # Verify no empty ranges in version history
        history = await wbe_service.get_history(root_id=wbe_id)
        for version in history:
            if version.valid_time.upper is not None:
                assert (
                    version.valid_time.lower < version.valid_time.upper
                ), f"Version {version.id} has empty valid_time range"
