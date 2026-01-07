# PLAN Phase: Cost Elements & Cost Element Types Implementation

**Date:** 2026-01-06  
**Iteration:** Cost Elements & Budgeting (Vertical Slice Completion)  
**Epic:** E004 - Project Structure Management  
**Story:** [E04-U03] Create Cost Elements within WBEs + Cost Element Types  
**Story Points:** 13 (updated from 8)  
**Status:** Planning

---

## Phase 1: Context Analysis

### Documentation Review

**Product Scope:**

- **Vision:** Complete the Project → WBE → Cost Element hierarchy with standardized Cost Element Types to enable actual budget tracking, cross-project comparability, and EVM calculations.
- **Business Value:** HIGH - Enables transition from structure definition to actual financial data management WITH cost standardization.

**Architecture:**

- **Pattern Established:** Branchable entities (Project, WBE) using `BranchableProtocol`, Versionable entities (Department, User) using `VersionableProtocol`
- **Recent Completion:** Backend audit tracking (`created_by`/`deleted_by`) now available for all entities
- **Test Standards:** >80% coverage, MyPy strict mode, Ruff linting

**Current Context:**

- ✅ Projects implemented with branchable versioning
- ✅ WBEs implemented with parent relationship to Projects
- ✅ Departments implemented as versionable entities
- ❌ **Cost Element Types missing** - Organizational-level cost categories
- ❌ **Cost Elements missing** - The "leaf" level where budgets/costs are tracked
- 📊 **Backlog Impact:** Blocks 9 high-priority items in Epic 5 (Financial Data) and Epic 8 (EVM Calculations)

### Codebase Analysis

**Existing Patterns:**

```python
# Versionable Pattern (Department)
class Department(EntityBase, VersionableMixin):
    department_id: Mapped[UUID]  # Root ID
    code: Mapped[str]
    name: Mapped[str]
    # ... temporal fields from mixin

# Branchable Pattern (WBE)
class WBE(EntityBase, VersionableMixin, BranchableMixin):
    wbe_id: Mapped[UUID]  # Root ID
    project_id: Mapped[UUID]  # Parent FK
    code: Mapped[str]
    name: Mapped[str]
    budget_allocation: Mapped[Decimal]
    # ... temporal + branching fields from mixins
```

**Test Infrastructure:**

- Unit tests: `tests/unit/services/`
- Integration tests: `tests/integration/repositories/`
- API tests: `tests/api/`
- E2E tests: `frontend/tests/e2e/`

**Dependencies:**

- ✅ WBE entity (parent for Cost Elements)
- ✅ Department entity (owner for Cost Element Types)
- ✅ Command pattern infrastructure
- ✅ Generic `TemporalService`

---

## Phase 2: Problem Definition

### 1. Problem Statement

**What:** The system lacks two critical entities for standardized cost tracking:

1. **Cost Element Types:** Organizational-level cost categories (e.g., "Mechanical Installation", "Electrical Work", "Software Development") that enable cross-project comparability
2. **Cost Elements:** Project-specific instances of Cost Element Types where budgets are allocated and costs tracked

**Why Important:**

- **Standardization:** Without Cost Element Types, costs cannot be compared across projects (no common taxonomy)
- **Comparability:** Cross-project reporting requires consistent cost categorization
- **Domain Ownership:** Departments need to own specific cost types relevant to their domain (e.g., Electrical Dept owns "Electrical Installation" type)
- **Financial Tracking:** Without Cost Elements, Projects and WBEs are just structural containers with no actionable financial data
- **Downstream Dependencies:** Blocks all financial features (cost registration, forecasting, EVM metrics)

**Business Impact:**

- **Current State:** Projects are "hollow" - structure exists but no budget detail or cost standardization
- **Desired State:**
  - Departments define Cost Element Types organizationally (e.g., "Mechanical Installation" owned by Mechanical Dept)
  - Cost Elements in projects reference these standard types, ensuring consistency
  - Cross-project reporting is meaningful (all "Mechanical Installation" costs are comparable across projects)
  - Budget allocation at the Cost Element level enables granular tracking

**What Happens If Not Addressed:**

- Cannot implement Epic 5 (Financial Data Management)
- Cannot calculate EVM metrics (Epic 8)
- No cross-project cost benchmarking or analysis
- Ad-hoc cost categorization leads to inconsistent reporting
- System remains a "structure-only" tool with limited business value

**Example Use Case:**

```
Department: Mechanical Engineering
└── Cost Element Type: "Mechanical Installation"
    ├── Project A → WBE 1.2 → Cost Element: "Mechanical Install Phase 1" ($100,000)
    └── Project B → WBE 2.1 → Cost Element: "Mechanical Install Phase 2" ($150,000)

→ Total "Mechanical Installation" across organization: $250,000 (comparable!)
```

### 2. Success Criteria (Measurable)

**Functional Criteria:**

#### Cost Element Types

- [ ] **F1:** Cost Element Type entity created with all required fields (code, name, department_id, description)
- [ ] **F2:** Cost Element Types support full CRUD operations via API
- [ ] **F3:** Cost Element Types are versionable (track changes over time) but NOT branchable
- [ ] **F4:** Cost Element Types track `created_by`/`deleted_by` for audit
- [ ] **F5:** Foreign key constraint enforces Department ownership
- [ ] **F6:** Validation prevents duplicate codes within same department

#### Cost Elements

- [ ] **F7:** Cost Element entity created with all required fields (code, name, wbe_id, cost_element_type_id, budget_amount, description)
- [ ] **F8:** Cost Elements support full CRUD operations via API
- [ ] **F9:** Cost Elements are branchable (inherit branching from parent WBE)
- [ ] **F10:** Cost Elements track `created_by`/`deleted_by` for audit
- [ ] **F11:** Foreign key constraints enforce WBE and Cost Element Type relationships
- [ ] **F12:** Validation prevents orphaned Cost Elements (WBE and Cost Element Type must exist)
- [ ] **F13:** Department is derived from Cost Element Type (not stored directly on Cost Element)

**Technical Criteria:**

- [ ] **T1:** Unit test coverage ≥80% for both services
- [ ] **T2:** Integration tests verify repository operations
- [ ] **T3:** API tests cover all CRUD endpoints for both entities
- [ ] **T4:** MyPy strict mode passes with no type errors
- [ ] **T5:** Ruff linting passes with no violations
- [ ] **T6:** Alembic migrations apply cleanly (up/down) for both tables
- [ ] **T7:** Performance: List query <100ms for 1000 cost elements

**Business Criteria:**

- [ ] **B1:** Frontend can display Cost Element Types by department
- [ ] **B2:** Frontend can display Cost Elements in WBE context with type information
- [ ] **B3:** Users can create/edit/delete both entity types
- [ ] **B4:** E2E tests verify complete user workflows
- [ ] **B5:** Cross-project cost type reporting is demonstrable

### 3. Scope Definition

#### In Scope

**Backend:**

1. **Domain Models:**

   - `backend/app/models/domain/cost_element_type.py`
     - Versionable (not branchable) - organizational reference data
     - Fields: `cost_element_type_id`, `department_id`, `code`, `name`, `description`
   - `backend/app/models/domain/cost_element.py`
     - Branchable + Versionable - project-specific data
     - Fields: `cost_element_id`, `wbe_id`, `cost_element_type_id`, `code`, `name`, `budget_amount`, `description`
     - **NOTE:** Department is **derived** from Cost Element Type (not stored)

2. **Schemas:**

   - `backend/app/models/schemas/cost_element_type.py`
   - `backend/app/models/schemas/cost_element.py`

3. **Services:**

   - `backend/app/services/cost_element_type_service.py` (extends `TemporalService` - versionable)
   - `backend/app/services/cost_element_service.py` (extends `TemporalService` - branchable)

4. **API:**

   - `backend/app/api/routes/cost_element_types.py` - RESTful endpoints with RBAC
   - `backend/app/api/routes/cost_elements.py` - RESTful endpoints with RBAC

5. **Migrations:**

   - Alembic migration for `cost_element_types` table
   - Alembic migration for `cost_elements` table

6. **Tests:**
   - Unit tests for both services
   - Integration tests for repository operations
   - API tests for both endpoint sets

**Frontend:**

1. **Cost Element Types:**

   - List view (grouped by department)
   - Create/Edit modal
   - API client integration

2. **Cost Elements:**

   - List view (within WBE context, showing type)
   - Create/Edit modal (with Cost Element Type selector)
   - API client integration

3. **E2E Tests:**
   - Cost Element Type CRUD workflow
   - Cost Element CRUD workflow
   - Cross-entity validation

#### Out of Scope (Deferred to Future Iterations)

- ❌ Budget allocation validation logic (E04-U05)
- ❌ Cost registration against Cost Elements (E05-U01)
- ❌ Hierarchical Cost Element tree view (E04-U07)
- ❌ Budget rollup calculations to WBE/Project levels
- ❌ Cost variance alerts
- ❌ Earned Value (EV) calculations
- ❌ Import/export functionality
- ❌ Advanced cross-project reporting dashboards
- ❌ Cost Element Type hierarchies (e.g., parent types)

#### Assumptions Requiring Validation

1. **Assumption:** Cost Element Types are **versionable but NOT branchable** (organizational reference data, not project-specific)
2. **Assumption:** Cost Elements get department from their Cost Element Type (derived, not stored)
3. **Assumption:** Cost Elements inherit branch from parent WBE (branchable)
4. **Assumption:** Budget amounts are positive decimals (validation in schema)
5. **Assumption:** Cost Element Type `code` is unique within a department (not globally)
6. **Assumption:** Cost Element `code` is scoped to WBE+branch (not globally unique)

---

## Phase 3: Implementation Options

### Option A: Two-Entity Model (Cost Element Type + Cost Element)

**Approach Summary:**

- **Cost Element Type:** Versionable, owned by Department, organizational reference data
- **Cost Element:** Branchable, references Cost Element Type, project-specific budget allocation
- Department is **derived** from Cost Element Type (not stored on Cost Element)

**Design Patterns:**

- Cost Element Type: `VersionableMixin` only (like Department)
- Cost Element: `VersionableMixin` + `BranchableMixin` (like WBE)
- Both use `TemporalService` with appropriate generics
- Command Pattern for all operations

**Pros:**

- ✅ **Strong standardization:** Enforces consistent cost categorization
- ✅ **Cross-project comparability:** All projects use same Cost Element Type taxonomy
- ✅ **Clear ownership:** Departments own their cost types
- ✅ **Flexible evolution:** Cost Element Types version independently of projects
- ✅ **Reduced duplication:** Department ownership defined once at type level

**Cons:**

- ⚠️ **Higher complexity:** Two entities instead of one
- ⚠️ **Additional API surface:** More endpoints to implement and test
- ⚠️ **Increased effort:** ~13 story points instead of 8

**Test Strategy Impact:**

- Test both entities independently
- Test referential integrity (Cost Element → Cost Element Type → Department)
- Verify department derivation logic
- Test version independence (Cost Element Type changes don't affect Cost Elements)

**Risk Level:** Medium (new pattern combination: versionable reference + branchable instance)  
**Estimated Complexity:** Moderate-High

---

### Option B: Single-Entity Model (Cost Element only, direct department link)

**Approach Summary:**

- **Cost Element:** Branchable, directly references Department, no Cost Element Type
- Simpler but sacrifices standardization

**Design Patterns:**

- Cost Element: `VersionableMixin` + `BranchableMixin`
- Direct FK to Department

**Pros:**

- ✅ Simpler implementation (~8 story points)
- ✅ Fewer entities to maintain
- ✅ Faster time to market

**Cons:**

- ❌ **No standardization:** Each project defines cost elements ad-hoc
- ❌ **No cross-project comparability:** Cannot aggregate "Mechanical Installation" across projects
- ❌ **Duplicate definitions:** Same cost type defined differently in each project
- ❌ **No central taxonomy:** Departments don't control their cost categories
- ❌ **Business value loss:** Primary use case (comparability) not supported

**Test Strategy Impact:**

- Simpler test suite
- But loses key business value tests

**Risk Level:** Low (technical) but HIGH (business value)  
**Estimated Complexity:** Moderate

---

### Recommendation: **Option A - Two-Entity Model**

**Justification:**

1. **Business Requirements:** Cross-project cost comparability is a core value proposition explicitly stated by the user
2. **Standardization:** Cost Element Types provide the taxonomy layer essential for meaningful reporting
3. **Domain Ownership:** Departments naturally own cost types, not individual cost instances
4. **Future-Proof:** Supports advanced reporting, benchmarking, and analytics
5. **Separation of Concerns:**
   - Cost Element Type = "What kinds of costs exist?" (organizational)
   - Cost Element = "How much budget for this specific instance?" (project)
6. **Normalization:** Follows database normalization principles (Cost Element Type is a reference entity)

**Decision Point:**

> [!IMPORTANT]  
> **Human Approval Required:**
>
> 1. Confirm Option A (Two-Entity Model: Cost Element Type + Cost Element)?
> 2. Acknowledge increased story points (13 instead of 8)?
> 3. Confirm Cost Element Type is **versionable but NOT branchable** (organizational reference data)?

---

## Phase 4: Technical Design (Option A)

### 1. Database Schema

#### Cost Element Type (Organizational Reference Data)

**File:** `backend/app/models/domain/cost_element_type.py`

```python
"""Cost Element Type - organizational cost categorization standard."""

from uuid import UUID
from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column
from app.core.base.base import EntityBase
from app.models.mixins import VersionableMixin

class CostElementType(EntityBase, VersionableMixin):
    """Cost Element Type - standardized cost category owned by a department.

    Cost Element Types are organizational reference data that enable:
    - Consistent cost categorization across projects
    - Cross-project cost comparability
    - Department ownership of cost types

    Versionable but NOT branchable (organizational data, not project-specific).

    Attributes:
        cost_element_type_id: Root ID for the Cost Element Type aggregation.
        department_id: Owning department (e.g., Mechanical Dept owns "Mechanical Installation").
        code: Cost type code (e.g., "MECH-INST").
        name: Display name (e.g., "Mechanical Installation").
        description: Optional description.

    Examples:
        - Code: "ELECT-INST", Name: "Electrical Installation", Dept: Electrical Engineering
        - Code: "SW-DEV", Name: "Software Development", Dept: Software Engineering
        - Code: "QA-TEST", Name: "Quality Assurance Testing", Dept: Quality Assurance
    """
    __tablename__ = "cost_element_types"

    # Root ID (stable identity across versions)
    cost_element_type_id: Mapped[UUID] = mapped_column(PG_UUID, nullable=False, index=True)

    # Department ownership
    department_id: Mapped[UUID] = mapped_column(
        PG_UUID,
        ForeignKey("departments.department_id"),
        nullable=False,
        index=True
    )

    # Identity
    code: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)

    # Metadata
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Temporal fields from VersionableMixin:
    # - valid_time: TSTZRANGE
    # - transaction_time: TSTZRANGE
    # - deleted_at: datetime | None
    # - created_by: UUID
    # - deleted_by: UUID | None

    def __repr__(self) -> str:
        return (
            f"<CostElementType(id={self.id}, "
            f"cost_element_type_id={self.cost_element_type_id}, "
            f"code={self.code}, name={self.name})>"
        )
```

**Migration Strategy:**

```sql
-- Alembic migration: create_cost_element_types_table
CREATE TABLE cost_element_types (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    cost_element_type_id UUID NOT NULL,
    department_id UUID NOT NULL REFERENCES departments(department_id),
    code VARCHAR(50) NOT NULL,
    name VARCHAR(255) NOT NULL,
    description TEXT,

    -- Versioning (from VersionableMixin)
    valid_time TSTZRANGE NOT NULL,
    transaction_time TSTZRANGE NOT NULL DEFAULT tstzrange(now(), NULL),
    deleted_at TIMESTAMPTZ,
    created_by UUID NOT NULL,
    deleted_by UUID
);

-- Indexes
CREATE INDEX ix_cost_element_types_cost_element_type_id ON cost_element_types(cost_element_type_id);
CREATE INDEX ix_cost_element_types_department_id ON cost_element_types(department_id);
CREATE INDEX ix_cost_element_types_code ON cost_element_types(code);

-- Temporal indexes
CREATE INDEX ix_cost_element_types_valid_time ON cost_element_types USING GIST (valid_time);
CREATE INDEX ix_cost_element_types_transaction_time ON cost_element_types USING GIST (transaction_time);

-- Exclude constraint (prevent overlapping versions)
ALTER TABLE cost_element_types ADD CONSTRAINT cost_element_types_no_overlap
    EXCLUDE USING gist (
        cost_element_type_id WITH =,
        valid_time WITH &&
    ) WHERE (deleted_at IS NULL);
```

---

#### Cost Element (Project-Specific Budget Allocation)

**File:** `backend/app/models/domain/cost_element.py`

```python
"""Cost Element - project-specific budget allocation of a standardized cost type."""

from decimal import Decimal
from uuid import UUID
from sqlalchemy import DECIMAL, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column
from app.core.base.base import EntityBase
from app.models.mixins import BranchableMixin, VersionableMixin

class CostElement(EntityBase, VersionableMixin, BranchableMixin):
    """Cost Element - project-specific instance of a Cost Element Type.

    Cost Elements are the leaf level of the project hierarchy where:
    - Budgets are allocated
    - Actual costs are tracked
    - Earned value is calculated

    Branchable (supports change orders) and Versionable (tracks changes).

    Attributes:
        cost_element_id: Root ID for the Cost Element aggregation.
        wbe_id: Parent WBE root ID.
        cost_element_type_id: Reference to standardized cost type.
        code: Project-specific code (e.g., "001", "LAB-PHASE1").
        name: Display name (can be instance-specific, e.g., "Phase 1 Mechanical").
        budget_amount: Allocated budget for this cost element.
        description: Optional description.

    Note: Department is DERIVED from Cost Element Type, not stored here.

    Examples:
        - WBE: "1.2 - Site Preparation"
          └── Cost Element: "MECH-001" (Type: "Mechanical Installation", Budget: $50,000)
        - WBE: "2.1 - Software Module A"
          └── Cost Element: "SW-DEV-001" (Type: "Software Development", Budget: $120,000)
    """
    __tablename__ = "cost_elements"

    # Root ID
    cost_element_id: Mapped[UUID] = mapped_column(PG_UUID, nullable=False, index=True)

    # Parent relationships
    wbe_id: Mapped[UUID] = mapped_column(
        PG_UUID,
        ForeignKey("wbes.wbe_id"),
        nullable=False,
        index=True
    )
    cost_element_type_id: Mapped[UUID] = mapped_column(
        PG_UUID,
        ForeignKey("cost_element_types.cost_element_type_id"),
        nullable=False,
        index=True
    )

    # Identity
    code: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)

    # Financial
    budget_amount: Mapped[Decimal] = mapped_column(DECIMAL(15, 2), default=0, nullable=False)

    # Metadata
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Mixins provide:
    # - valid_time, transaction_time, deleted_at, created_by, deleted_by (VersionableMixin)
    # - branch, parent_id, merge_from_branch (BranchableMixin)

    # NOTE: Department is DERIVED via cost_element_type.department_id (not stored here)

    def __repr__(self) -> str:
        return (
            f"<CostElement(id={self.id}, cost_element_id={self.cost_element_id}, "
            f"wbe_id={self.wbe_id}, code={self.code}, name={self.name})>"
        )
```

**Migration Strategy:**

```sql
-- Alembic migration: create_cost_elements_table
CREATE TABLE cost_elements (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    cost_element_id UUID NOT NULL,
    wbe_id UUID NOT NULL REFERENCES wbes(wbe_id),
    cost_element_type_id UUID NOT NULL REFERENCES cost_element_types(cost_element_type_id),
    code VARCHAR(50) NOT NULL,
    name VARCHAR(255) NOT NULL,
    budget_amount NUMERIC(15, 2) NOT NULL DEFAULT 0,
    description TEXT,

    -- Versioning (from VersionableMixin)
    valid_time TSTZRANGE NOT NULL,
    transaction_time TSTZRANGE NOT NULL DEFAULT tstzrange(now(), NULL),
    deleted_at TIMESTAMPTZ,
    created_by UUID NOT NULL,
    deleted_by UUID,

    -- Branching (from BranchableMixin)
    branch VARCHAR(255) NOT NULL DEFAULT 'main',
    parent_id UUID,
    merge_from_branch VARCHAR(255)
);

-- Indexes
CREATE INDEX ix_cost_elements_cost_element_id ON cost_elements(cost_element_id);
CREATE INDEX ix_cost_elements_wbe_id ON cost_elements(wbe_id);
CREATE INDEX ix_cost_elements_cost_element_type_id ON cost_elements(cost_element_type_id);
CREATE INDEX ix_cost_elements_code ON cost_elements(code);
CREATE INDEX ix_cost_elements_branch ON cost_elements(branch);

-- Temporal indexes
CREATE INDEX ix_cost_elements_valid_time ON cost_elements USING GIST (valid_time);
CREATE INDEX ix_cost_elements_transaction_time ON cost_elements USING GIST (transaction_time);

-- Exclude constraint (prevent overlapping versions in same branch)
ALTER TABLE cost_elements ADD CONSTRAINT cost_elements_no_overlap
    EXCLUDE USING gist (
        cost_element_id WITH =,
        branch WITH =,
        valid_time WITH &&
    ) WHERE (deleted_at IS NULL);
```

### 2. Pydantic Schemas

#### Cost Element Type Schemas

**File:** `backend/app/models/schemas/cost_element_type.py`

```python
from uuid import UUID
from pydantic import BaseModel, Field

class CostElementTypeBase(BaseModel):
    """Shared properties for Cost Element Type."""
    code: str = Field(..., min_length=1, max_length=50)
    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = None

class CostElementTypeCreate(CostElementTypeBase):
    """Properties required for creating a Cost Element Type."""
    department_id: UUID

class CostElementTypeUpdate(BaseModel):
    """Properties that can be updated."""
    code: str | None = Field(None, min_length=1, max_length=50)
    name: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = None
    department_id: UUID | None = None

class CostElementTypeRead(CostElementTypeBase):
    """Properties returned to client."""
    id: UUID
    cost_element_type_id: UUID
    department_id: UUID
    created_by: UUID

    class Config:
        from_attributes = True
```

#### Cost Element Schemas

**File:** `backend/app/models/schemas/cost_element.py`

```python
from decimal import Decimal
from uuid import UUID
from pydantic import BaseModel, Field

class CostElementBase(BaseModel):
    """Shared properties for Cost Element."""
    code: str = Field(..., min_length=1, max_length=50)
    name: str = Field(..., min_length=1, max_length=255)
    budget_amount: Decimal = Field(ge=0, decimal_places=2)
    description: str | None = None

class CostElementCreate(CostElementBase):
    """Properties required for creating a Cost Element."""
    wbe_id: UUID
    cost_element_type_id: UUID

class CostElementUpdate(BaseModel):
    """Properties that can be updated."""
    code: str | None = Field(None, min_length=1, max_length=50)
    name: str | None = Field(None, min_length=1, max_length=255)
    budget_amount: Decimal | None = Field(None, ge=0, decimal_places=2)
    description: str | None = None
    cost_element_type_id: UUID | None = None

class CostElementRead(CostElementBase):
    """Properties returned to client."""
    id: UUID
    cost_element_id: UUID
    wbe_id: UUID
    cost_element_type_id: UUID
    branch: str
    created_by: UUID

    class Config:
        from_attributes = True

class CostElementReadWithType(CostElementRead):
    """Cost Element with denormalized type information for convenience."""
    cost_element_type_code: str
    cost_element_type_name: str
    department_id: UUID  # Derived from type
    department_name: str  # Derived from type
```

### 3. Service Layer

#### Cost Element Type Service

**File:** `backend/app/services/cost_element_type_service.py`

```python
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.versioning.service import TemporalService
from app.models.domain.cost_element_type import CostElementType
from app.models.schemas.cost_element_type import (
    CostElementTypeCreate,
    CostElementTypeUpdate
)

class CostElementTypeService(TemporalService[
    CostElementType,
    CostElementTypeCreate,
    CostElementTypeUpdate
]):
    """Service for Cost Element Type management (versionable, not branchable)."""

    def __init__(self, db: AsyncSession):
        super().__init__(db, CostElementType, root_id_field="cost_element_type_id")
```

#### Cost Element Service

**File:** `backend/app/services/cost_element_service.py`

```python
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.versioning.service import TemporalService
from app.models.domain.cost_element import CostElement
from app.models.schemas.cost_element import CostElementCreate, CostElementUpdate

class CostElementService(TemporalService[CostElement, CostElementCreate, CostElementUpdate]):
    """Service for Cost Element management (branchable + versionable)."""

    def __init__(self, db: AsyncSession):
        super().__init__(db, CostElement, root_id_field="cost_element_id")
```

### 4. API Endpoints

#### Cost Element Types API

**File:** `backend/app/api/routes/cost_element_types.py`

```python
from fastapi import APIRouter, Depends
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.deps import get_current_user, get_db
from app.core.security.rbac import RoleChecker
from app.services.cost_element_type_service import CostElementTypeService
from app.models.schemas.cost_element_type import (
    CostElementTypeCreate,
    CostElementTypeUpdate,
    CostElementTypeRead
)

router = APIRouter(prefix="/cost-element-types", tags=["cost-element-types"])

@router.get("/", dependencies=[Depends(RoleChecker(["admin", "project_manager", "viewer"]))])
async def list_cost_element_types(
    department_id: UUID | None = None,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
) -> list[CostElementTypeRead]:
    """List cost element types, optionally filtered by department."""
    service = CostElementTypeService(db)
    # Implementation uses TemporalService.list with filters
    ...

@router.post("/", dependencies=[Depends(RoleChecker(["admin"]))])
async def create_cost_element_type(
    data: CostElementTypeCreate,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
) -> CostElementTypeRead:
    """Create a new cost element type (admin only)."""
    service = CostElementTypeService(db)
    return await service.create(data, actor_id=current_user.id)

# ... update, delete, get endpoints
```

#### Cost Elements API

**File:** `backend/app/api/routes/cost_elements.py`

```python
from fastapi import APIRouter, Depends
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.deps import get_current_user, get_db
from app.core.security.rbac import RoleChecker
from app.services.cost_element_service import CostElementService
from app.models.schemas.cost_element import (
    CostElementCreate,
    CostElementUpdate,
    CostElementRead,
    CostElementReadWithType
)

router = APIRouter(prefix="/cost-elements", tags=["cost-elements"])

@router.get("/", dependencies=[Depends(RoleChecker(["admin", "project_manager", "viewer"]))])
async def list_cost_elements(
    wbe_id: UUID | None = None,
    cost_element_type_id: UUID | None = None,
    branch: str = "main",
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
) -> list[CostElementReadWithType]:
    """List cost elements with type information, optionally filtered."""
    service = CostElementService(db)
    # Implementation includes JOIN with cost_element_types and departments
    ...

@router.post("/", dependencies=[Depends(RoleChecker(["admin", "project_manager"]))])
async def create_cost_element(
    data: CostElementCreate,
    branch: str = "main",
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
) -> CostElementRead:
    """Create a new cost element."""
    service = CostElementService(db)
    return await service.create(data, actor_id=current_user.id, branch=branch)

# ... update, delete, get endpoints
```

### 5. TDD Test Blueprint

**Test Hierarchy:**

```
backend/tests/
├── unit/services/
│   ├── test_cost_element_type_service.py
│   │   ├── test_create_cost_element_type_success
│   │   ├── test_update_cost_element_type_creates_new_version
│   │   ├── test_list_cost_element_types_by_department
│   │   └── test_soft_delete_cost_element_type
│   └── test_cost_element_service.py
│       ├── test_create_cost_element_success
│       ├── test_create_cost_element_tracks_actor
│       ├── test_update_cost_element_creates_new_version
│       ├── test_soft_delete_cost_element
│       ├── test_list_cost_elements_by_wbe
│       ├── test_list_cost_elements_by_type
│       ├── test_branch_isolation
│       └── test_department_derivation
├── integration/repositories/
│   ├── test_cost_element_type_repository_integration.py
│   └── test_cost_element_repository_integration.py
└── api/
    ├── test_cost_element_types.py
    │   ├── test_create_cost_element_type_api
    │   ├── test_list_cost_element_types_api
    │   ├── test_update_cost_element_type_api
    │   ├── test_delete_cost_element_type_api
    │   └── test_rbac_permissions
    └── test_cost_elements.py
        ├── test_create_cost_element_api
        ├── test_list_cost_elements_api
        ├── test_update_cost_element_api
        ├── test_delete_cost_element_api
        ├── test_cost_element_with_type_info
        └── test_rbac_permissions
```

**First 8 Test Cases (Ordered by Complexity):**

#### Cost Element Type Tests

1. **Test 1: Create Cost Element Type (Happy Path)**

   ```python
   async def test_create_cost_element_type_success():
       # GIVEN: Valid Department exists
       # WHEN: Creating cost element type with valid data
       # THEN: Cost element type is created with correct root_id
       # AND: created_by matches actor_id
   ```

2. **Test 2: List Cost Element Types by Department**
   ```python
   async def test_list_by_department():
       # GIVEN: 3 types for Dept A, 2 types for Dept B
       # WHEN: Listing with department_id filter for Dept A
       # THEN: Returns only 3 types
   ```

#### Cost Element Tests

3. **Test 3: Create Cost Element (Happy Path)**

   ```python
   async def test_create_cost_element_success():
       # GIVEN: Valid WBE and Cost Element Type exist
       # WHEN: Creating cost element with valid data
       # THEN: Cost element is created with correct root_id
       # AND: created_by matches actor_id
   ```

4. **Test 4: Department Derivation**

   ```python
   async def test_department_derivation():
       # GIVEN: Cost Element Type owned by Department X
       # AND: Cost Element references that type
       # WHEN: Querying cost element with type info
       # THEN: Department ID matches Cost Element Type's department
   ```

5. **Test 5: Update Cost Element Creates New Version**

   ```python
   async def test_update_creates_new_version():
       # GIVEN: Cost element v1 exists
       # WHEN: Updating budget_amount
       # THEN: Version 2 created
       # AND: v1 valid_time is closed
       # AND: v2 created_by matches actor_id
   ```

6. **Test 6: List Cost Elements by WBE**

   ```python
   async def test_list_by_wbe():
       # GIVEN: 3 cost elements for WBE_A, 2 for WBE_B
       # WHEN: Listing with wbe_id filter for WBE_A
       # THEN: Returns only 3 cost elements
   ```

7. **Test 7: List Cost Elements by Type**

   ```python
   async def test_list_by_type():
       # GIVEN: Mixed cost elements of different types
       # WHEN: Filtering by cost_element_type_id
       # THEN: Returns only matching cost elements
   ```

8. **Test 8: Branch Isolation**
   ```python
   async def test_branch_isolation():
       # GIVEN: Cost element exists in 'main'
       # WHEN: Creating new version in 'co-123'
       # THEN: 'main' version unchanged
       # AND: 'co-123' has updated version
   ```

---

## Phase 5: Risk Assessment

### Risks and Mitigations

| Risk Type       | Description                                                                   | Probability | Impact | Mitigation Strategy                                              |
| --------------- | ----------------------------------------------------------------------------- | ----------- | ------ | ---------------------------------------------------------------- |
| **Technical**   | FK constraint failures if Cost Element Type deleted while Cost Elements exist | Medium      | High   | Implement cascade rules or block deletion with active references |
| **Technical**   | FK constraint failures if WBE/Department deleted                              | Medium      | High   | Add cascade rules; frontend validation                           |
| **Technical**   | Migration fails on constraint creation                                        | Low         | Medium | Test migrations on dev DB first; use defensive DDL               |
| **Scope**       | 13 points is high for one iteration                                           | Medium      | Medium | Split into 2 iterations if needed (Types first, then Elements)   |
| **Data**        | Department derivation logic adds JOIN complexity                              | Low         | Low    | Index on cost_element_type_id; test query performance            |
| **Schedule**    | Frontend E2E tests take longer than expected                                  | Medium      | Low    | Start with manual testing; automate E2E in parallel              |
| **Integration** | OpenAPI schema generation doesn't reflect new schemas                         | Low         | Low    | Auto-generate client after backend deployment                    |

---

## Phase 6: Effort Estimation

### Time Breakdown (Updated for Two Entities)

- **Development:**
  - Domain Models (both) + Migrations: 2 hours
  - Schemas (both): 1 hour
  - Service Layer (both): 1.5 hours
  - API Endpoints (both): 2 hours
  - **Subtotal:** 6.5 hours
- **Testing:**
  - Unit Tests (both services): 3 hours
  - Integration Tests (both): 1.5 hours
  - API Tests (both endpoint sets): 2 hours
  - **Subtotal:** 6.5 hours
- **Frontend:**
  - Cost Element Type views: 2 hours
  - Cost Element views (with type selector): 3 hours
  - E2E Tests (both): 2 hours
  - **Subtotal:** 7 hours
- **Documentation:**
  - API Documentation: 1 hour
  - Architecture Updates: 0.5 hours
  - **Subtotal:** 1.5 hours
- **Review & Deployment:**
  - Code Review: 1.5 hours
  - Migration Deployment: 0.5 hours
  - **Subtotal:** 2 hours

**Total Estimated Effort:** 23.5 hours (~3 days)

### Prerequisites

- [x] WBE entity implemented
- [x] Department entity implemented
- [x] `TemporalService` generic implementation
- [x] Command pattern infrastructure
- [x] Audit tracking (`created_by`/`deleted_by`)
- [ ] **Migration environment verified** (test DB connection)
- [ ] **OpenAPI schema generator configured**

---

## Alternative: Split Into Two Iterations

Given the increased complexity (13 points → potentially 2 iterations):

### Iteration 6A: Cost Element Types (5 points)

- Implement Cost Element Types entity fully
- Backend + Frontend + Tests
- Establish pattern for versionable reference data

### Iteration 6B: Cost Elements (8 points) - **Original Plan**

- Implement Cost Elements entity
- Reference Cost Element Types
- Complete hierarchy

**Pros:**

- Smaller, more manageable chunks
- Earlier feedback on Cost Element Type pattern
- Lower risk per iteration

**Cons:**

- Delayed value (needs both entities to be useful)
- Context switching overhead

---

## Approval

**Status:** ⏳ Awaiting Approval  
**Approver:** Human  
**Approval Date:** _Pending_

**Questions for Approval:**

1. **Confirm Option A (Two-Entity Model)?**

   - Cost Element Type (versionable, not branchable, owned by Department)
   - Cost Element (branchable, references Cost Element Type)
   - Department derived from Cost Element Type

2. **Scope Decision:**

   - **Option 1:** Full implementation in single iteration (13 points, ~3 days)
   - **Option 2:** Split into two iterations (Types first 5pts, then Elements 8pts)

3. **Priority:** Backend-first or full-stack for both entities?

---

## Related Documentation

- **Architecture:** [`docs/02-architecture/contexts/evcs-core/architecture.md`](../../02-architecture/contexts/evcs-core/architecture.md)
- **Epic Definition:** [`docs/03-project-plan/epics.md#E004`](../epics.md)
- **Product Backlog:** [`docs/03-project-plan/product-backlog.md`](../product-backlog.md)
- **Recent Audit Work:** [`iterations/2026-01-06-backend-audit/`](../iterations/2026-01-06-backend-audit/)
