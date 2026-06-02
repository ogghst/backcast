"""Edge case tests for GlobalSearchService.

Tests cover temporal and branch filtering in _apply_project_scope, verifying
that intermediate entity subqueries (WorkPackage, ControlAccount, CostElement,
WBSElement) correctly apply temporal/branch filters so deleted or past-version
intermediate entities do not leak results.
"""

import asyncio
from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.versioning.enums import BranchMode
from app.models.domain.cost_element import CostElement
from app.models.domain.project import Project
from app.models.domain.work_package import WorkPackage
from app.services.global_search_service import GlobalSearchService
from tests.conftest import TEST_USER_ID
from tests.factories import (
    create_test_control_account,
    create_test_cost_element,
    create_test_cost_element_type,
    create_test_org_unit,
    create_test_project,
    create_test_wbs_element,
    create_test_work_package,
)


@pytest.fixture
def service(db: AsyncSession) -> GlobalSearchService:
    return GlobalSearchService(db)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _create_document(
    session: AsyncSession,
    project_id: UUID,
    name: str,
    *,
    description: str | None = None,
    extension: str = "pdf",
    size_bytes: int = 1024,
) -> UUID:
    """Insert a Document row directly and return its id."""
    doc_id = uuid4()
    stmt = text(
        """
        INSERT INTO documents (id, project_id, name, extension, description,
                               tags, is_locked, locked_by, created_by, size_bytes)
        VALUES (:id, :project_id, :name, :extension, :description,
                '[]', false, NULL, :created_by, :size_bytes)
        """
    )
    await session.execute(
        stmt,
        {
            "id": doc_id,
            "project_id": str(project_id),
            "name": name,
            "extension": extension,
            "description": description,
            "created_by": str(TEST_USER_ID),
            "size_bytes": size_bytes,
        },
    )
    await session.flush()
    return doc_id


async def _soft_delete_wp(
    session: AsyncSession,
    work_package_id: UUID,
    actor_id: UUID,
) -> None:
    """Soft-delete the current version of a WorkPackage on main branch."""
    from app.core.branching.commands import BranchableSoftDeleteCommand

    await BranchableSoftDeleteCommand(
        entity_class=WorkPackage,
        root_id=work_package_id,
        actor_id=actor_id,
        branch="main",
    ).execute(session)
    await session.flush()


# ---------------------------------------------------------------------------
# Test 1: Search returns only current versions of entities
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_search_returns_only_current_versions(
    db: AsyncSession, actor_id: UUID, service: GlobalSearchService
) -> None:
    """Search returns only the current version, not historical versions."""
    unique_prefix = f"CURRVER_{uuid4().hex[:8]}"

    project = await create_test_project(
        db,
        actor_id,
        name=f"{unique_prefix}_project",
        description=f"{unique_prefix}_original_desc",
    )
    await db.commit()

    # Search should find the original description
    results = await service.search(
        unique_prefix,
        user_id=actor_id,
        project_id=project.project_id,
    )
    assert results.total >= 1
    matching = [
        r for r in results.results if r.description and unique_prefix in r.description
    ]
    assert len(matching) == 1
    assert matching[0].description is not None
    assert "original_desc" in matching[0].description

    # Update the project description using UpdateVersionCommand
    from app.core.versioning.commands import UpdateVersionCommand

    await UpdateVersionCommand(
        entity_class=Project,
        root_id=project.project_id,
        actor_id=actor_id,
        description=f"{unique_prefix}_updated_desc",
    ).execute(db)
    await db.commit()

    # Search should now return the updated version only
    results = await service.search(
        unique_prefix,
        user_id=actor_id,
        project_id=project.project_id,
    )
    matching = [
        r for r in results.results if r.description and unique_prefix in r.description
    ]
    assert len(matching) == 1
    assert matching[0].description is not None
    assert "updated_desc" in matching[0].description
    assert "original_desc" not in matching[0].description


# ---------------------------------------------------------------------------
# Test 2: Search respects branch isolation
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_search_respects_branch_isolation(
    db: AsyncSession, actor_id: UUID, service: GlobalSearchService
) -> None:
    """Branch-only descriptions are invisible on main and visible on the branch."""
    unique_prefix = f"BRANCH_{uuid4().hex[:8]}"
    branch_name = f"change-order-{uuid4().hex[:6]}"

    project = await create_test_project(
        db,
        actor_id,
        name=f"{unique_prefix}_project",
        description=f"{unique_prefix}_main_desc",
    )
    await db.commit()

    # Search on main should find the main-only description
    results = await service.search(
        unique_prefix,
        user_id=actor_id,
        project_id=project.project_id,
        branch="main",
    )
    matching = [
        r for r in results.results if r.description and unique_prefix in r.description
    ]
    assert len(matching) >= 1
    assert all("main_desc" in (r.description or "") for r in matching)

    # Create a branch version of the project with a different description
    from app.core.branching.commands import UpdateCommand

    await UpdateCommand(
        entity_class=Project,
        root_id=project.project_id,
        actor_id=actor_id,
        updates={"description": f"{unique_prefix}_branch_desc"},
        branch=branch_name,
    ).execute(db)
    await db.commit()

    # Search on main should NOT find the branch-only description
    results_main = await service.search(
        unique_prefix,
        user_id=actor_id,
        project_id=project.project_id,
        branch="main",
        branch_mode=BranchMode.ISOLATED,
    )
    main_descs = [
        r.description
        for r in results_main.results
        if r.description and unique_prefix in r.description
    ]
    assert all("branch_desc" not in d for d in main_descs), (
        f"Branch-only description leaked to main: {main_descs}"
    )

    # Search on the branch with ISOLATED mode should find the branch description
    results_branch = await service.search(
        unique_prefix,
        user_id=actor_id,
        project_id=project.project_id,
        branch=branch_name,
        branch_mode=BranchMode.ISOLATED,
    )
    branch_descs = [
        r.description
        for r in results_branch.results
        if r.description and unique_prefix in r.description
    ]
    assert any("branch_desc" in d for d in branch_descs), (
        f"Branch description not found on branch {branch_name}: {branch_descs}"
    )


# ---------------------------------------------------------------------------
# Test 3: WBS element scoping filters through intermediate entities correctly
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_wbs_scoping_filters_through_intermediates(
    db: AsyncSession, actor_id: UUID, service: GlobalSearchService
) -> None:
    """Searching with wbe_id scope returns only descendants of that WBS element."""
    unique_prefix = f"WBSSCOPE_{uuid4().hex[:8]}"

    project = await create_test_project(db, actor_id)
    org = await create_test_org_unit(db, actor_id)
    ce_type = await create_test_cost_element_type(
        db, actor_id, org.organizational_unit_id
    )
    await db.commit()

    # Create two sibling WBS elements
    wbs_a = await create_test_wbs_element(
        db, actor_id, project.project_id, code=f"{unique_prefix}_A"
    )
    wbs_b = await create_test_wbs_element(
        db, actor_id, project.project_id, code=f"{unique_prefix}_B"
    )
    await db.commit()

    # Under A: CA -> WP -> CostElement with description ALPHA
    ca_a = await create_test_control_account(
        db, actor_id, wbs_a.wbs_element_id, org.organizational_unit_id
    )
    wp_a = await create_test_work_package(
        db, actor_id, ca_a.control_account_id, name=f"{unique_prefix}_wpA"
    )
    await create_test_cost_element(
        db,
        actor_id,
        wp_a.work_package_id,
        ce_type.cost_element_type_id,
        description=f"{unique_prefix}_ALPHA",
    )
    await db.commit()

    # Under B: CA -> WP -> CostElement with description BETA
    ca_b = await create_test_control_account(
        db, actor_id, wbs_b.wbs_element_id, org.organizational_unit_id
    )
    wp_b = await create_test_work_package(
        db, actor_id, ca_b.control_account_id, name=f"{unique_prefix}_wpB"
    )
    await create_test_cost_element(
        db,
        actor_id,
        wp_b.work_package_id,
        ce_type.cost_element_type_id,
        description=f"{unique_prefix}_BETA",
    )
    await db.commit()

    # Search scoped to WBS A should only find ALPHA
    results_a = await service.search(
        unique_prefix,
        user_id=actor_id,
        project_id=project.project_id,
        wbe_id=wbs_a.wbs_element_id,
    )
    alpha_found = any(
        r.description and "ALPHA" in r.description for r in results_a.results
    )
    beta_found = any(
        r.description and "BETA" in r.description for r in results_a.results
    )
    assert alpha_found, "ALPHA CostElement not found under WBS A scope"
    assert not beta_found, "BETA CostElement leaked from WBS B into WBS A scope"

    # Search scoped to WBS B should only find BETA
    results_b = await service.search(
        unique_prefix,
        user_id=actor_id,
        project_id=project.project_id,
        wbe_id=wbs_b.wbs_element_id,
    )
    beta_found_b = any(
        r.description and "BETA" in r.description for r in results_b.results
    )
    alpha_found_b = any(
        r.description and "ALPHA" in r.description for r in results_b.results
    )
    assert beta_found_b, "BETA CostElement not found under WBS B scope"
    assert not alpha_found_b, "ALPHA CostElement leaked from WBS A into WBS B scope"


# ---------------------------------------------------------------------------
# Test 4: Deleted intermediate entities don't leak results
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_deleted_intermediate_entity_does_not_leak(
    db: AsyncSession, actor_id: UUID, service: GlobalSearchService
) -> None:
    """Soft-deleting an intermediate WorkPackage hides its child CostElements from search."""
    unique_prefix = f"LEAKDEL_{uuid4().hex[:8]}"

    project = await create_test_project(db, actor_id, name=f"{unique_prefix}_project")
    org = await create_test_org_unit(db, actor_id)
    ce_type = await create_test_cost_element_type(
        db, actor_id, org.organizational_unit_id
    )
    wbs = await create_test_wbs_element(
        db, actor_id, project.project_id, name=f"{unique_prefix}_wbs"
    )
    ca = await create_test_control_account(
        db, actor_id, wbs.wbs_element_id, org.organizational_unit_id
    )
    wp = await create_test_work_package(
        db, actor_id, ca.control_account_id, name=f"{unique_prefix}_wp"
    )
    await create_test_cost_element(
        db,
        actor_id,
        wp.work_package_id,
        ce_type.cost_element_type_id,
        description=f"{unique_prefix}_TARGET",
    )
    await db.commit()

    # Verify search finds the CostElement before deletion
    results_before = await service.search(
        unique_prefix,
        user_id=actor_id,
        project_id=project.project_id,
    )
    assert any(
        r.description and "TARGET" in r.description for r in results_before.results
    ), "CostElement not found before WP deletion"

    # Soft-delete the WorkPackage
    await _soft_delete_wp(db, wp.work_package_id, actor_id)
    await db.commit()

    # Search should no longer find the CostElement (intermediate WP is deleted)
    results_after = await service.search(
        unique_prefix,
        user_id=actor_id,
        project_id=project.project_id,
    )
    leaked = [
        r for r in results_after.results if r.description and "TARGET" in r.description
    ]
    assert len(leaked) == 0, (
        f"CostElement leaked through deleted WP: {[r.description for r in leaked]}"
    )


# ---------------------------------------------------------------------------
# Test 5: Time-travel search respects as_of for intermediate entities
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_time_travel_search_respects_as_of(
    db: AsyncSession, actor_id: UUID, service: GlobalSearchService
) -> None:
    """Time-travel search with as_of returns the version valid at that timestamp."""
    unique_prefix = f"TT_{uuid4().hex[:8]}"

    project = await create_test_project(db, actor_id, name=f"{unique_prefix}_project")
    org = await create_test_org_unit(db, actor_id)
    ce_type = await create_test_cost_element_type(
        db, actor_id, org.organizational_unit_id
    )
    wbs = await create_test_wbs_element(
        db, actor_id, project.project_id, name=f"{unique_prefix}_wbs"
    )
    ca = await create_test_control_account(
        db, actor_id, wbs.wbs_element_id, org.organizational_unit_id
    )
    wp = await create_test_work_package(
        db, actor_id, ca.control_account_id, name=f"{unique_prefix}_wp"
    )
    ce = await create_test_cost_element(
        db,
        actor_id,
        wp.work_package_id,
        ce_type.cost_element_type_id,
        description=f"{unique_prefix}_ORIGINAL",
    )
    await db.commit()

    # Sleep briefly to ensure the original version's valid_time lower bound
    # is well-established before recording T1.
    await asyncio.sleep(0.05)

    # Record T1 between the two versions
    t1 = datetime.now(UTC)

    # Sleep to create a clear gap between T1 and the update's valid_time start
    await asyncio.sleep(0.05)

    # Update the CostElement to create a new version
    from app.core.versioning.commands import UpdateVersionCommand

    await UpdateVersionCommand(
        entity_class=CostElement,
        root_id=ce.cost_element_id,
        actor_id=actor_id,
        description=f"{unique_prefix}_UPDATED",
    ).execute(db)
    await db.commit()

    # Sleep again so T2 is definitely after the new version's valid_time start
    await asyncio.sleep(0.05)

    # Record T2 well after the new version's valid_time lower bound
    t2 = datetime.now(UTC)

    # Time-travel to T1: should find the ORIGINAL description
    results_t1 = await service.search(
        unique_prefix,
        user_id=actor_id,
        project_id=project.project_id,
        as_of=t1,
    )
    t1_descs = [
        r.description
        for r in results_t1.results
        if r.description and unique_prefix in r.description
    ]
    assert any("ORIGINAL" in d for d in t1_descs), (
        f"ORIGINAL not found at T1: {t1_descs}"
    )

    # Time-travel to T2: should find the UPDATED description
    results_t2 = await service.search(
        unique_prefix,
        user_id=actor_id,
        project_id=project.project_id,
        as_of=t2,
    )
    t2_descs = [
        r.description
        for r in results_t2.results
        if r.description and unique_prefix in r.description
    ]
    assert any("UPDATED" in d for d in t2_descs), f"UPDATED not found at T2: {t2_descs}"


# ---------------------------------------------------------------------------
# Test 6: Documents are scoped correctly with wbe_ids
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_documents_scoped_with_wbe_ids(
    db: AsyncSession, actor_id: UUID, service: GlobalSearchService
) -> None:
    """Document search respects wbe_id scoping through project resolution."""
    unique_prefix = f"DOCWBE_{uuid4().hex[:8]}"

    project = await create_test_project(db, actor_id, name=f"{unique_prefix}_project")
    wbs = await create_test_wbs_element(
        db, actor_id, project.project_id, name=f"{unique_prefix}_wbs"
    )
    await db.commit()

    # Create a document under the project
    await _create_document(
        db,
        project.project_id,
        name=f"{unique_prefix}_report",
        description=f"{unique_prefix}_docdesc",
    )
    await db.commit()

    # Search with wbe_id pointing to the WBS under this project should find the doc
    results = await service.search(
        unique_prefix,
        user_id=actor_id,
        wbe_id=wbs.wbs_element_id,
    )
    doc_results = [r for r in results.results if r.entity_type == "document"]
    assert len(doc_results) >= 1, (
        f"Document not found when searching with matching wbe_id: {[r.entity_type for r in results.results]}"
    )

    # Search with a non-existent wbe_id should NOT find the doc
    bogus_wbe_id = uuid4()
    results_bogus = await service.search(
        unique_prefix,
        user_id=actor_id,
        wbe_id=bogus_wbe_id,
    )
    doc_results_bogus = [
        r for r in results_bogus.results if r.entity_type == "document"
    ]
    assert len(doc_results_bogus) == 0, (
        f"Document found with non-existent wbe_id: {[r.name for r in doc_results_bogus]}"
    )


# ---------------------------------------------------------------------------
# Test 7: Search result schema has wbs_element_id field
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_search_result_schema_has_wbs_element_id(
    db: AsyncSession, actor_id: UUID, service: GlobalSearchService
) -> None:
    """Search results have wbs_element_id field (not wbe_id) and WBSElement results
    have their own root_id as wbs_element_id."""
    unique_prefix = f"SCHEMA_{uuid4().hex[:8]}"

    project = await create_test_project(db, actor_id, name=f"{unique_prefix}_project")
    wbs = await create_test_wbs_element(
        db,
        actor_id,
        project.project_id,
        name=f"{unique_prefix}_wbs",
        description=f"{unique_prefix}_wbs_desc",
    )
    await db.commit()

    results = await service.search(
        unique_prefix,
        user_id=actor_id,
        project_id=project.project_id,
    )
    assert results.total >= 1

    # Verify every result has a wbs_element_id field (may be None for non-WBS entities)
    for r in results.results:
        assert hasattr(r, "wbs_element_id"), (
            f"SearchResultItem missing wbs_element_id: {r.entity_type}"
        )

    # WBSElement results should have their own root_id as wbs_element_id
    wbs_results = [r for r in results.results if r.entity_type == "wbs_element"]
    assert len(wbs_results) >= 1, "No WBSElement results found"
    for wbs_r in wbs_results:
        assert wbs_r.wbs_element_id == wbs_r.root_id, (
            f"WBSElement result wbs_element_id ({wbs_r.wbs_element_id}) "
            f"!= root_id ({wbs_r.root_id})"
        )
        assert wbs_r.wbs_element_id == wbs.wbs_element_id, (
            f"WBSElement wbs_element_id does not match created WBS: "
            f"{wbs_r.wbs_element_id} != {wbs.wbs_element_id}"
        )
