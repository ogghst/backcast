# Plan: Merge Branch Logic for Change Orders

**Created:** 2026-01-26
**Based on:** [00-analysis.md](./00-analysis.md)
**Approved Option:** Option 1 - Iterative Merge Service

---

## Scope & Success Criteria

### Approved Approach Summary

- **Selected Option**: Option 1 - Iterative Merge Service
- **Architecture**: The `ChangeOrderService.merge_change_order` method currently only merges the Change Order entity itself. It must be enhanced to orchestrate the merge of ALL branch content (WBEs, CostElements, and potentially Projects) from the source branch (`co-{code}`) to the target branch (typically `main`).
- **Key Decisions**:
  1. Leverage existing `BranchableService.merge_branch` and `MergeBranchCommand` for individual entity merges
  2. Implement discovery logic to identify all modified entities in the source branch
  3. Iterate through each entity type and invoke merge for each modified entity
  4. Update CO status to "Implemented" after successful merge
  5. Maintain transactional integrity - all merges succeed or all fail

### Success Criteria

**Functional Criteria:**

- [ ] **Merge orchestrates all branch content** - When `merge_change_order` is called, it merges the Change Order entity AND all WBEs, CostElements, and Projects that exist in the source branch VERIFIED BY: Integration test checking entity counts on target branch post-merge
- [ ] **Handles newly created entities** - Entities created in the source branch (don't exist on target) are created on target during merge VERIFIED BY: Integration test with new WBE/CostElement in source branch
- [ ] **Handles modified entities** - Entities modified in both source and target branches merge correctly (source overwrites target) VERIFIED BY: Integration test with conflicting modifications
- [ ] **Handles deleted entities** - Entities soft-deleted in source branch are soft-deleted on target during merge VERIFIED BY: Integration test with soft-deleted WBE
- [ ] **Updates CO status** - Change Order status transitions to "Implemented" after successful merge VERIFIED BY: Unit test checking status field
- [ ] **Transactional integrity** - If merge fails for any entity, no changes are applied to any entity VERIFIED BY: Integration test simulating merge failure
- [ ] **Conflict detection** - System detects and reports merge conflicts before attempting merge VERIFIED BY: Unit test for `_detect_merge_conflicts` invocation

**Technical Criteria:**

- [ ] Performance: Merge completes within 5 seconds for 100 entities VERIFIED BY: Performance test with pytest-benchmark
- [ ] Code Quality: MyPy strict mode (zero errors), Ruff (zero errors) VERIFIED BY: CI pipeline checks
- [ ] Test Coverage: ≥80% coverage for new merge orchestration logic VERIFIED BY: pytest-cov report

**TDD Criteria:**

- [ ] All tests written **before** implementation code
- [ ] Each test failed first (documented in DO phase log)
- [ ] Test coverage ≥80%
- [ ] Tests follow Arrange-Act-Assert pattern

### Scope Boundaries

**In Scope:**

- Enhancement of `ChangeOrderService.merge_change_order` to orchestrate full branch content merge
- Discovery logic to find all modified entities in source branch
- Iterative merge of WBEs, CostElements, and Projects
- Transactional integrity handling
- API endpoint testing for merge orchestration
- Integration tests for multi-entity merge scenarios
- Unit tests for conflict detection invocation

**Out of Scope:**

- Frontend changes (UI already exists and calls the API)
- Conflict resolution UI (conflicts are detected but not resolved in this iteration)
- Merge of other entity types beyond WBEs, CostElements, and Projects
- Performance optimization beyond basic functionality
- Merge conflict resolution strategy (beyond detection)
- Recursive merge of child entities (WBEs and CostElements are treated as independent roots)

---

## Work Decomposition

### Task Breakdown

| #   | Task                                                                 | Files                                                                                 | Dependencies  | Success Criteria                                                                                               | Complexity   |
| --- | -------------------------------------------------------------------- | ------------------------------------------------------------------------------------- | ------------- | -------------------------------------------------------------------------------------------------------------- | ------------ |
| 1   | **Create entity discovery service**                                  | `app/services/entity_discovery_service.py` (new)                                     | None          | Service can query and return all branchable entities (WBEs, CostElements, Projects) existing in a given branch | Medium       |
| 2   | **Add unit tests for entity discovery**                              | `tests/unit/services/test_entity_discovery_service.py` (new)                        | Task 1        | All tests pass: test_discover_wbes, test_discover_cost_elements, test_discover_projects                       | Low          |
| 3   | **Enhance ChangeOrderService.merge_change_order**                    | `app/services/change_order_service.py` (modify merge_change_order method)           | Task 1, 2     | Method orchestrates discovery and iterative merge of all entities                                              | High         |
| 4   | **Add unit tests for merge orchestration**                           | `tests/unit/services/test_change_order_merge_orchestration.py` (new)                | Task 3        | Tests verify: discovery invocation, iterative merge calls, status update, transaction rollback on failure      | High         |
| 5   | **Add integration test for multi-entity merge**                      | `tests/integration/test_change_order_full_merge.py` (new)                           | Task 3, 4     | End-to-end test: CO with WBEs + CostElements merges all entities to main                                      | High         |
| 6   | **Add API test for merge endpoint**                                  | `tests/api/test_change_order_merge_endpoint.py` (new)                               | Task 5        | Test POST /api/v1/change-orders/{id}/merge orchestrates full branch merge                                     | Medium       |
| 7   **Add performance test for merge**                              | `tests/performance/test_merge_performance.py` (new)                                | Task 5        | Merge of 100 entities completes within 5 seconds                                                                 | Medium       |
| 8   | **Update API documentation**                                        | `docs/api/change-orders.md` (update)                                                 | Task 6        | Documentation reflects enhanced merge behavior                                                                  | Low          |

**Task Ordering Principles:**

1. **Database/Models first**: Entity discovery requires no schema changes (queries existing tables)
2. **Backend before Frontend**: No frontend changes needed (UI exists)
3. **Tests defined alongside each task**: Following TDD principles
4. **Incremental complexity**: Discovery → Orchestration → Integration → Performance

### Test-to-Requirement Traceability

| Acceptance Criterion | Test ID | Test File                                              | Expected Behavior |
| -------------------- | ------- | ------------------------------------------------------ | ----------------- |
| Merge orchestrates all branch content | T-001 | `tests/integration/test_change_order_full_merge.py` | Post-merge, target branch contains all WBEs, CostElements from source |
| Handles newly created entities | T-002 | `tests/integration/test_change_order_full_merge.py::test_merge_creates_new_entities` | New WBE/CostElement from source appears on target |
| Handles modified entities | T-003 | `tests/integration/test_change_order_full_merge.py::test_merge_overwrites_modified_entities` | Modified WBE on target matches source values |
| Handles deleted entities | T-004 | `tests/integration/test_change_order_full_merge.py::test_merge_soft_deletes_entities` | Soft-deleted WBE on source is soft-deleted on target |
| Updates CO status | T-005 | `tests/unit/services/test_change_order_merge_orchestration.py::test_merge_updates_status_to_implemented` | CO.status == "Implemented" after successful merge |
| Transactional integrity | T-006 | `tests/unit/services/test_change_order_merge_orchestration.py::test_merge_rolls_back_on_failure` | Failed merge leaves target branch unchanged |
| Conflict detection | T-007 | `tests/unit/services/test_change_order_merge_orchestration.py::test_merge_detects_conflicts` | Conflicting merge raises ConflictError |
| Performance: 100 entities < 5s | T-008 | `tests/performance/test_merge_performance.py` | Benchmark verifies execution time |

---

## Test Specification

### Test Hierarchy

```
├── Unit Tests (tests/unit/services/)
│   ├── test_entity_discovery_service.py
│   │   ├── test_discover_wbes_in_branch
│   │   ├── test_discover_cost_elements_in_branch
│   │   ├── test_discover_projects_in_branch
│   │   ├── test_discover_returns_empty_for_nonexistent_branch
│   │   └── test_discover_filters_deleted_entities
│   └── test_change_order_merge_orchestration.py
│       ├── test_merge_calls_discovery_service
│       ├── test_merge_iterates_wbes
│       ├── test_merge_iterates_cost_elements
│       ├── test_merge_iterates_projects
│       ├── test_merge_updates_status_to_implemented
│       ├── test_merge_rolls_back_on_failure
│       └── test_merge_raises_on_conflicts
├── Integration Tests (tests/integration/)
│   └── test_change_order_full_merge.py
│       ├── test_merge_happy_path
│       ├── test_merge_creates_new_entities
│       ├── test_merge_overwrites_modified_entities
│       ├── test_merge_soft_deletes_entities
│       ├── test_merge_with_empty_branch
│       └── test_merge_preserves_target_branch_other_entities
├── API Tests (tests/api/)
│   └── test_change_order_merge_endpoint.py
│       ├── test_merge_endpoint_returns_200
│       ├── test_merge_endpoint_returns_404_for_invalid_co
│       └── test_merge_endpoint_returns_400_for_locked_branch
└── Performance Tests (tests/performance/)
    └── test_merge_performance.py
        └── test_merge_100_entities_under_5_seconds
```

### Test Cases (first 8)

| Test ID | Test Name                                              | Criterion | Type | Verification |
| ------- | ------------------------------------------------------ | --------- | ---- | ------------ |
| T-001   | test_discover_wbes_in_branch_returns_all_active_wbes   | Discovery | Unit | Returns list of WBEs with matching branch, deleted_at IS NULL |
| T-002   | test_discover_cost_elements_in_branch_filters_deleted  | Discovery | Unit | Excludes CostElements where deleted_at IS NOT NULL |
| T-003   | test_merge_calls_discovery_for_all_entity_types        | Orchestration | Unit | Mock discovery service called once for each entity type |
| T-004   | test_merge_iterates_wbes_and_calls_branchable_merge    | Orchestration | Unit | BranchableService.merge_branch called for each discovered WBE |
| T-005   | test_merge_updates_status_to_implemented_on_success    | Status Update | Unit | CO.status equals "Implemented" after all entities merged |
| T-006   | test_merge_rolls_back_on_wbe_merge_failure             | Transactional | Unit | Session.rollback called when WBE merge raises exception |
| T-007   | test_merge_full_branch_creates_wbes_on_target          | Integration | Integration | WBE count on main increases by source WBE count |
| T-008   | test_merge_full_branch_overwrites_cost_elements        | Integration | Integration | CostElement on main has values from source branch version |

### Test Infrastructure Needs

- **Fixtures needed**:
  - `db_session` (from conftest.py) - AsyncSession for database operations
  - `test_project_with_wbes_and_cost_elements` - New fixture creating a project with nested WBEs and CostElements
  - `test_change_order_with_branch` - New fixture creating a CO with associated `co-{code}` branch

- **Mocks/stubs**:
  - Mock `BranchableService.merge_branch` for unit tests
  - Mock entity discovery service for orchestration unit tests

- **Database state**:
  - Seed data: Projects, WBEs, CostElements on main branch
  - Branch data: Modified WBEs/CostElements on `co-{code}` branch
  - Test isolation: Each test uses unique root IDs to avoid interference

---

## Risk Assessment

| Risk Type   | Description                                                                 | Probability | Impact | Mitigation |
| ----------- | --------------------------------------------------------------------------- | ----------- | ------ | ---------- |
| Technical   | Entity discovery query performance degradation with large datasets         | Medium      | High   | Use indexed queries (branch column indexed), add pagination for discovery |
| Technical   | Transaction timeout when merging large number of entities                  | Medium      | High   | Set reasonable timeout, batch merges in future iteration (not in scope) |
| Integration | Orphaned entities if merge fails mid-operation                              | Low         | High   | Use database transactions with rollback, test rollback scenarios thoroughly |
| Integration | Merge conflicts not detected before merge operation                        | Low         | Medium | Invoke `_detect_merge_conflicts` before merge, raise if conflicts exist |
| Integration | Frontend expects different API response format                              | Low         | Medium | Verify existing API contract, ensure response unchanged |

---

## Task Dependency Graph

```yaml
# Task Dependency Graph
tasks:
  - id: BE-001
    name: "Create entity discovery service"
    agent: pdca-backend-do-executor
    dependencies: []

  - id: BE-002
    name: "Add unit tests for entity discovery"
    agent: pdca-backend-do-executor
    dependencies: [BE-001]

  - id: BE-003
    name: "Enhance ChangeOrderService.merge_change_order"
    agent: pdca-backend-do-executor
    dependencies: [BE-001, BE-002]

  - id: BE-004
    name: "Add unit tests for merge orchestration"
    agent: pdca-backend-do-executor
    dependencies: [BE-003]

  - id: BE-005
    name: "Add integration test for multi-entity merge"
    agent: pdca-backend-do-executor
    dependencies: [BE-003, BE-004]

  - id: BE-006
    name: "Add API test for merge endpoint"
    agent: pdca-backend-do-executor
    dependencies: [BE-005]

  - id: BE-007
    name: "Add performance test for merge"
    agent: pdca-backend-do-executor
    dependencies: [BE-005]

  - id: BE-008
    name: "Update API documentation"
    agent: pdca-backend-do-executor
    dependencies: [BE-006]
```

**Parallelization Notes:**
- BE-001 can start immediately
- BE-002 depends on BE-001 (unit tests for discovery)
- BE-003 depends on both BE-001 and BE-002 (service must exist and be tested)
- BE-004 depends on BE-003 (orchestration tests require implementation)
- BE-005 depends on BE-003 and BE-004 (integration tests require implementation and unit tests)
- BE-006 depends on BE-005 (API test requires integration test infrastructure)
- BE-007 depends on BE-005 (performance test requires merge implementation)
- BE-008 depends on BE-006 (documentation requires API verification)

---

## Documentation References

### Required Reading

- **Coding Standards**: `/home/nicola/dev/backcast_evs/docs/00-meta/coding_standards.md`
- **Bounded Contexts**: `/home/nicola/dev/backcast_evs/docs/02-architecture/01-bounded-contexts.md` (Change Management section)
- **Change Management User Stories**: FR-8.4.12, FR-8.4.13 (merge workflow requirements)
- **Architecture Decision Records**: `/home/nicola/dev/backcast_evs/docs/02-architecture/decisions/adr-index.md` (relevant branching/merge ADRs)

### Code References

- **Backend pattern - BranchableService**: `/home/nicola/dev/backcast_evs/backend/app/core/branching/service.py` (lines 276-287: `merge_branch` method)
- **Backend pattern - MergeBranchCommand**: `/home/nicola/dev/backcast_evs/backend/app/core/branching/commands.py` (lines 294-368)
- **Current implementation**: `/home/nicola/dev/backcast_evs/backend/app/services/change_order_service.py` (lines 567-617: existing `merge_change_order` method)
- **Test pattern - Conflict detection**: `/home/nicola/dev/backcast_evs/backend/tests/unit/core/test_merge_conflict_detection.py`
- **Test fixture pattern**: `/home/nicola/dev/backcast_evs/backend/tests/conftest.py`

### Key Entities to Merge

- **WBE (Work Breakdown Element)**: `/home/nicola/dev/backcast_evs/backend/app/models/domain/wbe.py`
- **CostElement**: `/home/nicola/dev/backcast_evs/backend/app/models/domain/cost_element.py`
- **Project**: `/home/nicola/dev/backcast_evs/backend/app/models/domain/project.py`

---

## Prerequisites

### Technical

- [ ] Database migrations applied (no schema changes needed for this iteration)
- [ ] Dependencies installed (uv sync in backend directory)
- [ ] Environment configured (PostgreSQL running via docker-compose)
- [ ] Existing tests passing: `cd backend && uv run pytest`

### Documentation

- [x] Analysis phase approved (00-analysis.md complete with Option 1 recommendation)
- [ ] Architecture docs reviewed (BranchableService, MergeBranchCommand)
- [ ] Existing test patterns understood (test_merge_conflict_detection.py)

---

## Key Principles

1. **Define WHAT, not HOW**: This plan specifies test cases and success criteria. The DO phase will determine implementation details (e.g., specific SQL queries, error handling patterns).
2. **Measurable**: All success criteria are objectively verifiable through tests, logs, or measurements.
3. **Sequential**: Tasks ordered with clear dependencies. Discovery must exist before orchestration can use it.
4. **Traceable**: Every acceptance criterion maps to one or more test specifications (T-001 through T-008).
5. **Actionable**: Each task is specific enough for the DO phase to execute without ambiguity.

---

## Output Summary

This plan drives the DO phase to implement the **Merge Branch Logic** iteration. The work focuses on enhancing `ChangeOrderService.merge_change_order` to orchestrate the merge of ALL branch content, not just the Change Order entity itself.

**Critical Success Factor**: The enhanced merge must discover and merge WBEs, CostElements, and Projects from the source branch while maintaining transactional integrity and updating the CO status to "Implemented".

**Next Step**: Proceed to DO phase with task BE-001 (Create entity discovery service).
