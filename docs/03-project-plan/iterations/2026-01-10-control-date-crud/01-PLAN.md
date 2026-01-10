# PLAN Phase: Control Date CRUD Operations

**Date:** 2026-01-10  
**Status:** 🔵 PLANNING  
**Iteration:** [2026-01-10-control-date-crud](./00-ANALYSIS.md)

---

## Phase 1: Context Summary

### Analysis Reference

See [00-ANALYSIS.md](./00-ANALYSIS.md) for full context including:

- Problem statement: CRUD operations ignore control date
- Bitemporal semantics analysis
- Three solution options compared
- Recommended: Option A (control_date for valid_time)

### Key Decision

**Use control date for `valid_time`, keep `transaction_time` as actual recording time.**

This preserves bitemporal correctness:

- `valid_time` = When the event occurred (user's control date)
- `transaction_time` = When it was recorded in database (now)

---

## Phase 2: Problem Definition

### 1. Problem Statement

**What:** CRUD operations use current timestamp instead of selected control date.

**Example:**

- User sets control date to `2026-03-03`
- Creates WBE
- Database shows `valid_time` starting at `2026-01-10` (current time)
- Expected: `valid_time` should start at `2026-03-03` (control date)

**Why Important:** Users cannot:

- Backdate legitimate data corrections
- Model historical "what-if" scenarios
- Reconstruct project baselines at specific past dates
- Record events at their actual occurrence time

**Business Impact:**

- Audit trail inaccurate (timestamps don't reflect reality)
- EVM calculations based on wrong dates
- Cannot comply with "as-built" documentation requirements

### 2. Success Criteria (Measurable)

**Functional Criteria:**

- [ ] Create operation: `valid_time.lower` = control_date
- [ ] Update operation: Old version closed at control_date, new version starts at control_date
- [ ] Delete operation: `deleted_at` = control_date
- [ ] `transaction_time` always = actual recording time (now)
- [ ] Default behavior (no control date) unchanged
- [ ] All existing tests still pass
- [ ] 5+ new tests for control date CRUD pass

**Technical Criteria:**

- [ ] MyPy strict mode passes
- [ ] Backward compatible (control_date parameter optional)
- [ ] No breaking API changes
- [ ] Frontend hooks updated to use TimeMachine state

**Business Criteria:**

- [ ] User can set control date and create entity at that date
- [ ] Audit trail shows both effective date and recording date
- [ ] Time-travel queries correctly show control-dated data

### 3. Scope Definition

**In Scope:**

| Item                 | Description                                        |
| -------------------- | -------------------------------------------------- |
| Backend: Commands    | Add control_date parameter to Create/Update/Delete |
| Backend: Services    | Pass control_date through service layer            |
| Backend: API         | Accept X-Control-Date header                       |
| Frontend: Hooks      | Read selectedTime from TimeMachine store           |
| Frontend: API Client | Send X-Control-Date header                         |
| Tests                | Unit & integration tests for control date CRUD     |

**Out of Scope (Technical Debt):**

| Item                                 | Reason                | TD ID  |
| ------------------------------------ | --------------------- | ------ |
| control_date >= last_edit validation | Complex, not blocking | TD-023 |
| Admin backdating override            | Lower priority        | TD-024 |
| Control date UX improvements         | Polish, not essential | TD-025 |
| Bulk import with control dates       | Future feature        | TD-026 |

---

## Phase 3: Implementation Tasks

### Task Breakdown

| #                 | Task                                       | Effort | Priority | Dependencies |
| ----------------- | ------------------------------------------ | ------ | -------- | ------------ |
| **Backend**       |
| 1                 | Add control_date to CreateVersionCommand   | 1h     | Critical | None         |
| 2                 | Add control_date to UpdateVersionCommand   | 1h     | Critical | Task 1       |
| 3                 | Add control_date to SoftDeleteCommand      | 0.5h   | Critical | Task 1       |
| 4                 | Update service layer methods               | 1h     | Critical | Tasks 1-3    |
| 5                 | Add X-Control-Date header to API routes    | 1h     | Critical | Task 4       |
| **Frontend**      |
| 6                 | Update API client base function            | 1h     | Critical | None         |
| 7                 | Update useCreateWBE hook                   | 0.5h   | High     | Task 6       |
| 8                 | Update useUpdateWBE hook                   | 0.5h   | High     | Task 6       |
| 9                 | Update useDeleteWBE hook                   | 0.5h   | High     | Task 6       |
| 10                | Apply pattern to Project/CostElement hooks | 1h     | Medium   | Tasks 7-9    |
| **Testing**       |
| 11                | Unit tests for commands with control_date  | 2h     | High     | Tasks 1-3    |
| 12                | Integration tests for API                  | 2h     | High     | Task 5       |
| 13                | Frontend hook tests                        | 1h     | Medium   | Tasks 7-9    |
| **Documentation** |
| 14                | Update architecture.md                     | 1h     | Medium   | All          |
| 15                | Update patterns.md                         | 1h     | Medium   | All          |
| 16                | Update API docs                            | 0.5h   | Low      | Task 5       |

**Total Estimated Effort:** 15 hours

---

## Phase 4: Technical Design

### 4.1 Backend: Command Layer

**CreateVersionCommand Enhancement:**

```python
class CreateVersionCommand(VersionedCommandABC[TVersionable]):
    def __init__(
        self,
        entity_class: type[TVersionable],
        root_id: UUID,
        actor_id: UUID,
        control_date: datetime | None = None,  # NEW
        **fields: Any,
    ) -> None:
        super().__init__(entity_class, root_id, actor_id)
        self.fields = fields
        self.control_date = control_date or datetime.now(UTC)

    async def execute(self, session: AsyncSession) -> TVersionable:
        """Create with valid_time set to control_date."""
        version = cast(Any, self.entity_class)(
            created_by=self.actor_id, **self.fields
        )
        session.add(version)
        await session.flush()

        # Set valid_time to control_date, transaction_time to now
        stmt = text(
            f"""
            UPDATE {self.entity_class.__tablename__}
            SET
                valid_time = tstzrange(:control_date, NULL, '[]'),
                transaction_time = tstzrange(clock_timestamp(), NULL, '[]')
            WHERE id = :version_id
            """
        )
        await session.execute(stmt, {
            "control_date": self.control_date,
            "version_id": version.id
        })
        await session.flush()
        await session.refresh(version)
        return cast(TVersionable, version)
```

**UpdateVersionCommand Enhancement:**

```python
async def execute(self, session: AsyncSession) -> TVersionable:
    """Update with version boundaries at control_date."""
    current = await self._get_current(session)
    if not current:
        raise ValueError(f"No active version found for {self.root_id}")

    # Close old version at control_date
    await self._close_version(current, session, close_at=self.control_date)

    # Create new version starting at control_date
    new_version = self._clone_version(current)
    # ... apply updates ...
    session.add(new_version)
    await session.flush()

    # Set temporal bounds
    stmt = text(f"""
        UPDATE {self.entity_class.__tablename__}
        SET
            valid_time = tstzrange(:control_date, NULL, '[]'),
            transaction_time = tstzrange(clock_timestamp(), NULL, '[]')
        WHERE id = :version_id
    """)
    await session.execute(stmt, {
        "control_date": self.control_date,
        "version_id": new_version.id
    })
    await session.refresh(new_version)
    return new_version
```

**SoftDeleteCommand Enhancement:**

```python
async def execute(self, session: AsyncSession) -> TVersionable:
    """Mark as deleted at control_date."""
    current = await self._get_current(session)
    if not current:
        raise ValueError(f"No active version found")

    current.deleted_at = self.control_date  # Use control_date
    current.deleted_by = self.actor_id
    await session.flush()
    return current
```

### 4.2 Backend: API Layer

**Add Header Parameter:**

```python
from datetime import datetime
from fastapi import Header

@router.post("/wbes", response_model=WBERead)
async def create_wbe(
    wbe: WBECreate,
    current_user: User = Depends(get_current_user),
    control_date: datetime | None = Header(
        None,
        alias="X-Control-Date",
        description="Effective date for the operation (default: now)"
    ),
    session: AsyncSession = Depends(get_session),
) -> WBE:
    """Create WBE with optional control date."""
    service = WBEService(session)
    return await service.create_wbe(
        wbe,
        current_user.id,
        control_date=control_date  # Pass through
    )
```

**No Validation Needed:**

```python
# Future dating ALLOWED for planning/forecasting
# Past dating ALLOWED for backdating/corrections
# Any control_date value is valid
```

### 4.3 Frontend: API Client

**Base Function Enhancement:**

```typescript
// src/lib/api/client.ts
import { useTimeMachineStore } from "@/stores/timeMachineStore";

export async function apiRequest<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const { selectedTime } = useTimeMachineStore.getState();

  const headers = {
    "Content-Type": "application/json",
    ...(selectedTime && {
      "X-Control-Date": selectedTime.toISOString(),
    }),
    ...options.headers,
  };

  const response = await fetch(`${API_BASE}${endpoint}`, {
    ...options,
    headers,
  });

  if (!response.ok) {
    throw new ApiError(await response.json());
  }

  return response.json();
}
```

**Hook Updates:**

```typescript
// src/hooks/useWBE.ts
export function useCreateWBE() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (data: WBECreate) => {
      // apiRequest will automatically add X-Control-Date header
      return apiRequest<WBERead>("/api/v1/wbes", {
        method: "POST",
        body: JSON.stringify(data),
      });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["wbes"] });
    },
  });
}
```

### 4.4 TDD Test Blueprint

```
├── Backend Unit Tests
│   ├── test_create_version_command_with_control_date
│   ├── test_create_version_command_with_future_date
│   ├── test_update_version_command_with_control_date
│   ├── test_soft_delete_command_with_control_date
│   └── test_default_control_date_uses_now
│
├── Backend Integration Tests
│   ├── test_create_wbe_with_past_control_date_header
│   ├── test_create_wbe_with_future_control_date_header
│   ├── test_update_wbe_with_control_date_header
│   ├── test_delete_wbe_with_control_date_header
│   ├── test_create_without_control_date_uses_now
│   └── test_time_travel_sees_control_dated_entity
│
└── Frontend Tests
    ├── test_api_client_sends_control_date_header
    ├── test_create_hook_respects_selected_time
    └── test_update_hook_respects_selected_time
```

### First 5 Test Cases (Ordered Simple to Complex)

**1. test_create_version_command_with_control_date** (Unit)

```python
async def test_create_version_command_with_control_date(db_session):
    """CreateVersionCommand should set valid_time to control_date."""
    control_date = datetime(2026, 3, 3, tzinfo=UTC)

    cmd = CreateVersionCommand(
        Project,
        uuid4(),
        uuid4(),
        control_date=control_date,
        name="Test",
        budget=100
    )

    project = await cmd.execute(db_session)

    # valid_time starts at control_date
    assert project.valid_time.lower == control_date
    # transaction_time starts at actual recording time (now)
    assert project.transaction_time.lower > control_date
```

**2. test_control_date_validation_future_rejected** (Unit)

```python
async def test_control_date_validation_future_rejected():
    """Should reject control_date in the future."""
    future_date = datetime.now(UTC) + timedelta(days=1)

    with pytest.raises(HTTPException) as exc:
        validate_control_date(future_date)

    assert exc.value.status_code == 400
    assert "future" in exc.value.detail.lower()
```

**3. test_create_wbe_with_control_date_header** (Integration)

```python
async def test_create_wbe_with_control_date_header(client, test_project):
    """API should accept X-Control-Date header."""
    control_date = datetime(2026, 3, 3, tzinfo=UTC)

    response = await client.post(
        "/api/v1/wbes",
        json={
            "project_id": test_project["project_id"],
            "code": "WBE-1",
            "name": "Test WBE",
            "budget_allocation": 50000,
            "level": 1,
        },
        headers={"X-Control-Date": control_date.isoformat()}
    )

    assert response.status_code == 201
    wbe = response.json()

    # Verify in database
    stmt = select(WBE).where(WBE.wbe_id == wbe["wbe_id"])
    result = await db_session.execute(stmt)
    db_wbe = result.scalar_one()

    assert db_wbe.valid_time.lower == control_date
    assert db_wbe.transaction_time.lower > control_date
```

**5. test_update_wbe_with_control_date_closes_at_control** (Integration)

```python
async def test_update_wbe_with_control_date_closes_at_control(client, wbe):
    """Update should close old version at control_date."""
    control_date = datetime(2026, 3, 3, tzinfo=UTC)

    response = await client.put(
        f"/api/v1/wbes/{wbe['wbe_id']}",
        json={"name": "Updated Name"},
        headers={"X-Control-Date": control_date.isoformat()}
    )

    assert response.status_code == 200

    # Check old version closed at control_date
    stmt = select(WBE).where(
        WBE.wbe_id == wbe["wbe_id"],
        func.upper(WBE.valid_time).is_not(None)
    )
    result = await db_session.execute(stmt)
    old_version = result.scalar_one()

    assert old_version.valid_time.upper == control_date
```

**6. test_time_travel_sees_control_dated_entity** (Integration)

```python
async def test_time_travel_sees_control_dated_entity(client, test_project):
    """Time travel query should see entity created at control date."""
    control_date = datetime(2026, 3, 3, tzinfo=UTC)

    # Create WBE at control date
    response = await client.post(
        "/api/v1/wbes",
        json={
            "project_id": test_project["project_id"],
            "code": "WBE-1",
            "name": "Backdated WBE",
            "budget_allocation": 50000,
            "level": 1,
        },
        headers={"X-Control-Date": control_date.isoformat()}
    )
    wbe_id = response.json()["wbe_id"]

    # Query before control date - should not see it
    before = datetime(2026, 3, 1, tzinfo=UTC)
    response = await client.get(
        f"/api/v1/wbes/{wbe_id}",
        params={"as_of": before.isoformat()}
    )
    assert response.status_code == 404

    # Query at control date - should see it
    response = await client.get(
        f"/api/v1/wbes/{wbe_id}",
        params={"as_of": control_date.isoformat()}
    )
    assert response.status_code == 200
    assert response.json()["name"] == "Backdated WBE"
```

---

## Phase 5: Risk Assessment

| Risk Type   | Description                       | Probability | Impact | Mitigation                                   |
| ----------- | --------------------------------- | ----------- | ------ | -------------------------------------------- |
| Technical   | Breaking existing CRUD            | Low         | High   | Default control_date=None preserves behavior |
| Technical   | Frontend hooks complexity         | Medium      | Medium | Centralize logic in API client               |
| Integration | Header not passed correctly       | Low         | Medium | Integration tests verify header              |
| UX          | User confusion about control date | High        | Medium | Clear UI indicators, documentation           |
| Data        | Invalid control dates             | Medium      | High   | Comprehensive validation                     |
| Performance | Additional UPDATE queries         | Low         | Low    | Minimal overhead                             |

---

## Phase 6: Effort Estimation

### Time Breakdown

| Phase                    | Tasks       | Effort    |
| ------------------------ | ----------- | --------- |
| **Backend Core**         | Tasks 1-5   | 4.5h      |
| **Frontend Integration** | Tasks 6-10  | 3.5h      |
| **Testing**              | Tasks 11-13 | 5h        |
| **Documentation**        | Tasks 14-16 | 2.5h      |
| **Total**                |             | **15.5h** |

### Prerequisites

1. ✅ TimeMachine store exists (already implemented)
2. ✅ Bitemporal infrastructure working (just fixed)
3. ⬜ No additional infrastructure needed

### Implementation Order

```
Phase 1: Backend Core (4.5h)
├── Task 1: CreateVersionCommand
├── Task 2: UpdateVersionCommand
├── Task 3: SoftDeleteCommand
├── Task 4: Service layer
└── Task 5: API routes

Phase 2: Frontend (3.5h) [can overlap with Phase 3]
├── Task 6: API client
└── Tasks 7-10: Hooks

Phase 3: Testing (5h)
├── Task 11: Unit tests
├── Task 12: Integration tests
└── Task 13: Frontend tests

Phase 4: Documentation (2.5h)
└── Tasks 14-16: Docs updates
```

---

## Approval Checklist

- [x] Problem statement clear
- [x] Success criteria measurable
- [x] Scope well-defined
- [x] Technical design sound
- [x] Risks identified and mitigated
- [x] Effort realistic

---

## Approval

**Status:** ✅ APPROVED - Ready for DO phase

**Key Points:**

1. Preserves bitemporal semantics (valid vs transaction time)
2. Backward compatible (optional parameter)
3. Clear audit trail maintained
4. Comprehensive testing planned

---

## Related Documents

- [Analysis](./00-ANALYSIS.md)
- [Previous Iteration](../2026-01-10-time-machine-production-hardening/)
- [EVCS Architecture](../../../02-architecture/backend/contexts/evcs-core/architecture.md)
- [Temporal Patterns](../../../02-architecture/backend/contexts/evcs-core/patterns.md)
