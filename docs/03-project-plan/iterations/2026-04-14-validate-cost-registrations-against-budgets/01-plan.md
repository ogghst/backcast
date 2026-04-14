# Implementation Plan: E05-U05 Validate Cost Registrations against Budgets

**Created:** 2026-04-14
**Story Points:** 8
**Epic:** E005 (Financial Data Management)
**Approach:** Server-Side Warnings with Per-Project Configuration

---

## Clarified Requirements (Based on User Decisions)

### Functional Decisions

1. **Blocking Behavior**: ✅ WARN ONLY (do not block registration)
2. **Warning Threshold**: ✅ Configurable per-project in database, default 80%
3. **Configuration Scope**: ✅ Per-project setting via project detail page and dedicated widget
4. **Override Mechanism**: ✅ Project admin roles can override default behavior
5. **Migration Strategy**: ✅ Do not change existing registrations (validate new only)

### Acceptance Criteria

1. ✅ Real-time validation: Total costs checked against allocated budget
2. ✅ Warning when approaching budget limit (configurable threshold, default 80%)
3. ✅ Server-side warnings returned in API response (no blocking)
4. ✅ Per-project configuration stored in database
5. ✅ Project admin override capability via role-based permissions
6. ✅ Visual feedback in UI for warnings
7. ✅ Budget configuration widget component

---

## Architecture & Design

### Data Model Changes

**New Entity: ProjectBudgetSettings**

```python
class ProjectBudgetSettings(EntityBase, VersionableMixin):
    """Per-project budget validation settings.
    
    Note: Versionable but NOT Branchable - budget settings apply
    across all branches for consistency.
    """
    project_id: Mapped[UUID] = mapped_column(PG_UUID, nullable=False)
    warning_threshold_percent: Mapped[Decimal] = mapped_column(
        DECIMAL(5, 2), default=Decimal("80.00"), nullable=False
    )
    allow_project_admin_override: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False
    )
```

### API Changes

**New Endpoints:**

```
GET /api/v1/projects/{project_id}/budget-settings
PUT /api/v1/projects/{project_id}/budget-settings
```

**Modified Endpoints:**

```
POST /api/v1/cost-registrations
  Response: Adds budget_warning field to CostRegistrationRead schema

PUT /api/v1/cost-registrations/{id}
  Response: Adds budget_warning field to CostRegistrationRead schema
```

### Backend Components

**1. Configuration Storage**
- Remove global config approach
- Use per-project database settings
- Migration to create `project_budget_settings` table

**2. Validation Logic**
```python
async def validate_budget_status(
    cost_element_id: UUID,
    new_amount: Decimal,
    project_id: UUID,
    user_roles: list[str],
    as_of: datetime | None = None,
) -> BudgetWarning | None:
    """Validate budget status and return warning if needed.
    
    Returns None if no warning, BudgetWarning if threshold exceeded.
    Project admins can bypass warnings based on settings.
    """
```

**3. Exception Classes**
```python
class BudgetWarningException(Exception):
    """Warning raised when budget threshold exceeded."""
    def __init__(self, warning: BudgetWarning):
        self.warning = warning
        super().__init__(f"Budget threshold exceeded: {warning.message}")
```

### Frontend Components

**1. New Components**
- `BudgetSettingsWidget.tsx` - Widget for configuring budget thresholds
- `BudgetProgressBar.tsx` - Visual indicator with warning levels
- `ProjectBudgetSettings.tsx` - Settings section in project detail page

**2. Modified Components**
- `CostRegistrationModal.tsx` - Display server-side warnings
- `ProjectDetailPage.tsx` - Add budget settings section

---

## Implementation Steps

### Phase 1: Backend Foundation (2 days)

#### Step 1.1: Database Migration (2 hours)
**File:** `backend/alembic/versions/YYYYMMDD_create_project_budget_settings.py`

```python
def upgrade():
    op.create_table(
        'project_budget_settings',
        sa.Column('project_budget_settings_id', PG_UUID, primary_key=True),
        sa.Column('project_id', PG_UUID, nullable=False),
        sa.Column('warning_threshold_percent', sa.Numeric(5, 2), default=80.0),
        sa.Column('allow_project_admin_override', sa.Boolean, default=True),
        sa.Column('valid_time', TSTZRANGE, nullable=False),
        sa.Column('transaction_time', TSTZRANGE, nullable=False),
        sa.Column('deleted_at', sa.DateTime, nullable=True),
    )
    op.create_index('ix_project_budget_settings_project_id', 'project_budget_settings', ['project_id'])
```

#### Step 1.2: Domain Model (1 hour)
**File:** `backend/app/models/domain/project_budget_settings.py`

- Create `ProjectBudgetSettings` entity
- Inherit from `VersionableMixin` only (NOT branchable)
- Add docstring explaining rationale

#### Step 1.3: Service Layer (3 hours)
**File:** `backend/app/services/project_budget_settings_service.py`

```python
class ProjectBudgetSettingsService(SimpleService[ProjectBudgetSettings]):
    async def get_settings_for_project(self, project_id: UUID) -> ProjectBudgetSettings
    async def upsert_settings(
        self, project_id: UUID, settings_in: ProjectBudgetSettingsCreate
    ) -> ProjectBudgetSettings
    async def get_warning_threshold(self, project_id: UUID) -> Decimal
    async def can_admin_override(self, project_id: UUID) -> bool
```

#### Step 1.4: Schema Definitions (2 hours)
**File:** `backend/app/models/schemas/project_budget_settings.py`

```python
class ProjectBudgetSettingsCreate(BaseModel):
    warning_threshold_percent: Decimal = Decimal("80.00")
    allow_project_admin_override: bool = True

class ProjectBudgetSettingsRead(BaseModel):
    project_budget_settings_id: UUID
    project_id: UUID
    warning_threshold_percent: Decimal
    allow_project_admin_override: bool

class BudgetWarning(BaseModel):
    exceeds_threshold: bool
    threshold_percent: Decimal
    current_percent: Decimal
    message: str
```

#### Step 1.5: API Routes (2 hours)
**File:** `backend/app/api/routes/project_budget_settings.py`

```python
@router.get("/{project_id}/budget-settings")
async def get_budget_settings(project_id: UUID) -> ProjectBudgetSettingsRead

@router.put("/{project_id}/budget-settings")
async def update_budget_settings(
    project_id: UUID,
    settings_in: ProjectBudgetSettingsCreate,
    current_user: User,
) -> ProjectBudgetSettingsRead
```

#### Step 1.6: Cost Registration Service Updates (3 hours)
**File:** `backend/app/services/cost_registration_service.py`

- Add `validate_budget_status()` method
- Modify `create_cost_registration()` to call validation
- Modify `update_cost_registration()` to call validation
- Check project admin override permissions
- Return `BudgetWarning` in response metadata

#### Step 1.7: Enhanced Cost Registration API (1 hour)
**File:** `backend/app/api/routes/cost_registrations.py`

- Update POST endpoint to include budget_warning in response
- Update PUT endpoint to include budget_warning in response
- Handle `BudgetWarningException` (return 200 with warning metadata)

#### Step 1.8: Unit Tests (3 hours)
**File:** `backend/tests/unit/services/test_project_budget_settings_service.py`

- Test CRUD operations for budget settings
- Test default threshold (80%)
- Test per-project override
- Test project admin bypass logic

**File:** Update `backend/tests/unit/services/test_cost_registration_budget_validation.py`

- Update tests for server-side warning behavior
- Test project admin override
- Test per-project thresholds

### Phase 2: Frontend Implementation (2 days)

#### Step 2.1: API Client Generation (30 min)
```bash
cd frontend && npm run generate-client
```

#### Step 2.2: Budget Settings Widget (4 hours)
**File:** `frontend/src/features/projects/widgets/BudgetSettingsWidget.tsx`

```typescript
interface BudgetSettingsWidgetProps {
  projectId: string;
}

export function BudgetSettingsWidget({ projectId }: BudgetSettingsWidgetProps) {
  const { data: settings, update } = useProjectBudgetSettings(projectId);

  return (
    <Card title="Budget Validation Settings">
      <Form>
        <Form.Item label="Warning Threshold (%)">
          <InputNumber min={0} max={100} defaultValue={80} />
        </Form.Item>
        <Form.Item>
          <Checkbox>Allow project admin to override warnings</Checkbox>
        </Form.Item>
      </Form>
    </Card>
  );
}
```

#### Step 2.3: Budget Progress Bar Component (3 hours)
**File:** `frontend/src/components/budget/BudgetProgressBar.tsx`

```typescript
interface BudgetProgressBarProps {
  budget: number;
  used: number;
  threshold: number;
  warning?: BudgetWarning;
}

export function BudgetProgressBar({ budget, used, threshold, warning }: BudgetProgressBarProps) {
  const percentage = (used / budget) * 100;
  const color = getBarColor(percentage, threshold);

  return (
    <div className="budget-progress-bar">
      <Progress percent={percentage} strokeColor={color} />
      {warning && <Alert type="warning" message={warning.message} />}
    </div>
  );
}
```

#### Step 2.4: Update Cost Registration Modal (3 hours)
**File:** `frontend/src/features/cost-registration/components/CostRegistrationModal.tsx`

- Fetch project budget settings on mount
- Display server-side budget warnings
- Use `BudgetProgressBar` for visual feedback
- Handle admin override scenario

#### Step 2.5: Project Detail Page Integration (2 hours)
**File:** `frontend/src/pages/projects/ProjectDetailPage.tsx`

- Add budget settings section
- Integrate `BudgetSettingsWidget`
- Show current threshold and override status

#### Step 2.6: React Query Hooks (2 hours)
**File:** `frontend/src/features/projects/api/useProjectBudgetSettings.ts`

```typescript
export function useProjectBudgetSettings(projectId: string) {
  return useQuery({
    queryKey: queryKeys.projects.budgetSettings(projectId),
    queryFn: () => getProjectBudgetSettings({ projectId }),
  });
}

export function useUpdateProjectBudgetSettings() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: updateProjectBudgetSettings,
    onSuccess: () => queryClient.invalidateQueries(...),
  });
}
```

#### Step 2.7: Frontend Tests (3 hours)
**File:** `frontend/src/features/projects/widgets/__tests__/BudgetSettingsWidget.test.tsx`

- Test threshold update
- Test admin override toggle
- Test persistence

**File:** Update `frontend/src/features/cost-registration/components/__tests__/CostRegistrationModal.test.tsx`

- Test server-side warning display
- Test admin override behavior
- Test visual feedback

### Phase 3: Integration & Polish (1 day)

#### Step 3.1: Error Handling (2 hours)
- Handle budget settings not found (use defaults)
- Handle concurrent updates
- Handle invalid threshold values

#### Step 3.2: Permission Checks (2 hours)
**File:** `backend/app/core/rbac.py`

- Add `project-budget-settings-write` permission
- Check project admin role for override

#### Step 3.3: Documentation (2 hours)
- Update API documentation
- Add component documentation
- Update user guide

#### Step 3.4: End-to-End Testing (2 hours)
- Test full workflow: configure threshold → register cost → see warning
- Test admin override
- Test per-project isolation

---

## File Modification Summary

### Backend Files (10 files)

| File | Action | Lines |
|------|--------|-------|
| `backend/alembic/versions/..._create_project_budget_settings.py` | CREATE | ~50 |
| `backend/app/models/domain/project_budget_settings.py` | CREATE | ~60 |
| `backend/app/services/project_budget_settings_service.py` | CREATE | ~120 |
| `backend/app/models/schemas/project_budget_settings.py` | CREATE | ~40 |
| `backend/app/api/routes/project_budget_settings.py` | CREATE | ~80 |
| `backend/app/services/cost_registration_service.py` | MODIFY | +80 |
| `backend/app/api/routes/cost_registrations.py` | MODIFY | +30 |
| `backend/app/core/rbac.py` | MODIFY | +10 |
| `backend/tests/unit/services/test_project_budget_settings_service.py` | CREATE | ~150 |
| `backend/tests/unit/services/test_cost_registration_budget_validation.py` | MODIFY | +100 |

### Frontend Files (7 files)

| File | Action | Lines |
|------|--------|-------|
| `frontend/src/features/projects/widgets/BudgetSettingsWidget.tsx` | CREATE | ~150 |
| `frontend/src/components/budget/BudgetProgressBar.tsx` | CREATE | ~80 |
| `frontend/src/features/projects/api/useProjectBudgetSettings.ts` | CREATE | ~60 |
| `frontend/src/features/cost-registration/components/CostRegistrationModal.tsx` | MODIFY | +50 |
| `frontend/src/pages/projects/ProjectDetailPage.tsx` | MODIFY | +30 |
| `frontend/src/features/projects/widgets/__tests__/BudgetSettingsWidget.test.tsx` | CREATE | ~120 |
| `frontend/src/features/cost-registration/components/__tests__/CostRegistrationModal.test.tsx` | MODIFY | +80 |

---

## Success Criteria

### Functional Requirements

- [x] Server-side budget validation implemented
- [x] Warning threshold configurable per-project (default 80%)
- [x] Budget warnings returned in API response
- [x] Project admin can override warnings
- [x] Existing registrations unchanged
- [x] Budget settings widget component created
- [x] Project detail page includes budget settings

### Quality Standards

- [x] Zero MyPy errors (strict mode)
- [x] Zero Ruff errors
- [x] Zero TypeScript errors (strict mode)
- [x] Zero ESLint errors
- [x] 80%+ test coverage
- [x] All tests passing

### Performance

- [x] Validation overhead <100ms per registration
- [x] Budget settings query <50ms
- [x] No N+1 query problems

---

## Risk Assessment

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Performance regression | Low | Medium | Add caching for budget settings |
| Missing permissions check | Low | High | Explicit test coverage for RBAC |
| Migration conflicts | Low | Medium | Use isolated migration timestamp |
| Frontend-backend contract mismatch | Low | Medium | Generate OpenAPI client after backend changes |

---

## Dependencies

### Prerequisites (All Complete ✅)
- E04-U03 ✅: Cost Elements implementation
- E05-U01 ✅: Cost Registrations implementation
- RBAC system ✅: Role-based permissions
- Project CRUD ✅: Project management

### External Dependencies
- None (all internal)

---

## Timeline

**Total Estimated Effort:** 5 days

- **Phase 1:** Backend Foundation (2 days)
  - Day 1: Migration, models, service layer (8 hours)
  - Day 2: API routes, cost registration updates, tests (8 hours)

- **Phase 2:** Frontend Implementation (2 days)
  - Day 3: Widget, progress bar, modal updates (8 hours)
  - Day 4: Project detail page, hooks, tests (8 hours)

- **Phase 3:** Integration & Polish (1 day)
  - Day 5: Error handling, permissions, documentation, E2E tests (8 hours)

---

## Next Steps

1. ✅ Analysis complete
2. ✅ Plan approved
3. **DO Phase:** Begin implementation with Phase 1 (Backend Foundation)

**Ready to proceed with DO phase?**
