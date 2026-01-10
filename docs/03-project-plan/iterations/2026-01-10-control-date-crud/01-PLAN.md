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

**Mechanism Update:**
Control date will be passed via **request body** (Create/Update) or **query parameters** (Delete) instead of headers. This ensures:

1. No CORS issue with custom headers.
2. An unique source of truth in api request parameters.
3. Explicit visibility of the parameter in the data model.

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
- [ ] API Models reflect `control_date` field

**Business Criteria:**

- [ ] User can set control date and create entity at that date
- [ ] Audit trail shows both effective date and recording date
- [ ] Time-travel queries correctly show control-dated data

### 3. Scope Definition

**In Scope:**

| Item              | Description                                        |
| ----------------- | -------------------------------------------------- |
| Backend: Commands | Add control_date parameter to Create/Update/Delete |
| Backend: Services | Pass control_date through service layer            |
| Backend: API      | Add control_date to Pydantic models & Query param  |
| Frontend: Hooks   | Read selectedTime and inject into body/query       |
| Tests             | Unit & integration tests for control date CRUD     |

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
| 1                 | Add control_date to CreateVersionCommand   | 0.5h   | Critical | None         |
| 2                 | Add control_date to UpdateVersionCommand   | 0.5h   | Critical | Task 1       |
| 3                 | Add control_date to SoftDeleteCommand      | 0.5h   | Critical | Task 1       |
| 4                 | Update service layer methods               | 1h     | Critical | Tasks 1-3    |
| 5                 | Update API Schemas & Routes (Body/Query)   | 1.5h   | Critical | Task 4       |
| **Frontend**      |
| 6                 | Update useCreateWBE hook (Body)            | 0.5h   | High     | Task 5       |
| 7                 | Update useUpdateWBE hook (Body)            | 0.5h   | High     | Task 5       |
| 8                 | Update useDeleteWBE hook (Query)           | 0.5h   | High     | Task 5       |
| 9                 | Apply pattern to Project/CostElement hooks | 1h     | Medium   | Tasks 6-8    |
| **Testing**       |
| 10                | Unit tests for commands with control_date  | 2h     | High     | Tasks 1-3    |
| 11                | Integration tests for API (Body/Query)     | 2h     | High     | Task 5       |
| 12                | Frontend hook tests                        | 1h     | Medium   | Tasks 6-8    |
| **Documentation** |
| 13                | Update architecture.md                     | 1h     | Medium   | All          |
| 14                | Update patterns.md                         | 1h     | Medium   | All          |
| 15                | Update API docs                            | 0.5h   | Low      | Task 5       |

**Total Estimated Effort:** 13.5 hours

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

**Update Pydantic Models:**

```python
# app/schemas/wbe.py

class WBECreate(BaseModel):
    # ... existing fields ...
    control_date: datetime | None = None  # NEW

class WBEUpdate(BaseModel):
    # ... existing fields ...
    control_date: datetime | None = None  # NEW
```

**Update API Routes:**

```python
# app/api/routes/wbes.py

@router.post("/wbes", response_model=WBERead)
async def create_wbe(
    wbe: WBECreate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> WBE:
    """Create WBE. payload.control_date is used if present."""
    service = WBEService(session)
    # Extract control_date from payload, remove it from dict passed to command
    wbe_data = wbe.model_dump()
    control_date = wbe_data.pop("control_date", None)

    return await service.create_wbe(
        WBECreate(**wbe_data), # Re-wrap or pass dict if service accepts dict
        current_user.id,
        control_date=control_date
    )

@router.put("/wbes/{wbe_id}", response_model=WBERead)
async def update_wbe(
    wbe_id: UUID,
    wbe: WBEUpdate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> WBE:
    """Update WBE. payload.control_date is used if present."""
    service = WBEService(session)
    wbe_data = wbe.model_dump(exclude_unset=True)
    control_date = wbe_data.pop("control_date", None)

    return await service.update_wbe(
        wbe_id,
        WBEUpdate(**wbe_data),
        current_user.id,
        control_date=control_date
    )

@router.delete("/wbes/{wbe_id}")
async def delete_wbe(
    wbe_id: UUID,
    control_date: datetime | None = Query(None), # Query param for DELETE
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> None:
    """Delete WBE using optional control_date from query param."""
    service = WBEService(session)
    await service.delete_wbe(
        wbe_id,
        current_user.id,
        control_date=control_date
    )
```

### 4.3 Frontend: Hooks

**Hook Updates:**

```typescript
// src/hooks/useWBE.ts

export function useCreateWBE() {
  const queryClient = useQueryClient();
  // Get selected time from store
  const selectedTime = useTimeMachineStore((s) => s.selectedTime);

  return useMutation({
    mutationFn: async (data: WBECreate) => {
      const payload = {
        ...data,
        // Inject control_date if selectedTime exists
        control_date: selectedTime ? selectedTime.toISOString() : undefined,
      };
      return apiRequest<WBERead>("/api/v1/wbes", {
        method: "POST",
        body: JSON.stringify(payload),
      });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["wbes"] });
    },
  });
}

export function useDeleteWBE() {
  const queryClient = useQueryClient();
  const selectedTime = useTimeMachineStore((s) => s.selectedTime);

  return useMutation({
    mutationFn: async (wbeId: string) => {
      const params = new URLSearchParams();
      if (selectedTime) {
        params.append("control_date", selectedTime.toISOString());
      }
      return apiRequest(`/api/v1/wbes/${wbeId}?${params.toString()}`, {
        method: "DELETE",
      });
      // Note: apiRequest should handle empty body for DELETE if not provided
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
│   ├── test_create_wbe_with_control_date_body
│   ├── test_update_wbe_with_control_date_body
│   ├── test_delete_wbe_with_control_date_query
│   └── test_time_travel_sees_control_dated_entity
│
└── Frontend Tests
    ├── test_create_hook_injects_control_date_in_body
    └── test_delete_hook_injects_control_date_in_query
```

### First 5 Test Cases (Ordered Simple to Complex)

**1. test_create_version_command_with_control_date** (Unit)
(Remains same as previous plan, unrelated to HTTP transport)

**2. test_create_wbe_with_control_date_body** (Integration)

```python
async def test_create_wbe_with_control_date_body(client, test_project):
    """API should accept control_date in body."""
    control_date = datetime(2026, 3, 3, tzinfo=UTC)

    response = await client.post(
        "/api/v1/wbes",
        json={
            "project_id": test_project["project_id"],
            "code": "WBE-1",
            "name": "Test WBE",
            "budget_allocation": 50000,
            "level": 1,
            "control_date": control_date.isoformat() # IN BODY
        }
    )

    assert response.status_code == 201
    wbe = response.json()
    # verify valid_time in DB...
```

**3. test_delete_wbe_with_control_date_query** (Integration)

```python
async def test_delete_wbe_with_control_date_query(client, wbe):
    """API should accept control_date in query for DELETE."""
    control_date = datetime(2026, 3, 3, tzinfo=UTC)

    response = await client.delete(
        f"/api/v1/wbes/{wbe['wbe_id']}",
        params={"control_date": control_date.isoformat()} # IN QUERY
    )
    assert response.status_code == 200
    # verify deleted_at in DB...
```

---

## Phase 5: Risk Assessment

| Risk Type   | Description                       | Probability | Impact | Mitigation                                   |
| ----------- | --------------------------------- | ----------- | ------ | -------------------------------------------- |
| Technical   | Breaking existing CRUD            | Low         | High   | Default control_date=None preserves behavior |
| Technical   | Frontend hooks payload overrides  | Low         | Medium | Ensure manual control_date takes precedence? |
| Integration | Parameter not extracted correctly | Low         | Medium | Integration tests verify flow                |
| Data        | Invalid control dates             | Medium      | High   | Validation in Pydantic models                |

---

## Phase 6: Effort Estimation

### Time Breakdown

| Phase                    | Tasks       | Effort    |
| ------------------------ | ----------- | --------- |
| **Backend Core**         | Tasks 1-5   | 4h        |
| **Frontend Integration** | Tasks 6-9   | 3h        |
| **Testing**              | Tasks 10-12 | 4h        |
| **Documentation**        | Tasks 13-15 | 2.5h      |
| **Total**                |             | **13.5h** |

### Prerequisites

1. ✅ TimeMachine store exists
2. ✅ Bitemporal infrastructure working

### Implementation Order

```
Phase 1: Backend Core
├── Task 1-3: Commands (Already done/refined)
├── Task 4: Content Service Layer (Already done/refined)
└── Task 5: API Schemas & Routes (REFOCUS HERE)

Phase 2: Frontend
└── Tasks 6-9: Hooks (Update to pass data)

Phase 3: Testing
└── Integration tests (Update to match new API)
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

**Status:** ✅ APPROVED - Updated for Data/Query Params

**Key Points:**

1. **Explicit Data Model:** control_date is part of the entity schema.
2. **Standard REST:** Body for mutation, Query for deletion.

---

## Related Documents

- [Analysis](./00-ANALYSIS.md)
- [Previous Iteration](../2026-01-10-time-machine-production-hardening/)
- [EVCS Architecture](../../../02-architecture/backend/contexts/evcs-core/architecture.md)
- [Temporal Patterns](../../../02-architecture/backend/contexts/evcs-core/patterns.md)
