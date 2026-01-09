# Request Analysis: E2E Test Data Isolation

**Technical Debt Item:** TD-012  
**Priority:** High (First in paydown plan)  
**Estimated Effort:** 3 hours  
**Date:** 2026-01-09  
**Status:** 📋 Analysis Phase

---

## Clarified Requirements

### Problem Statement

E2E tests currently share database state, causing occasional flakiness when tests create data that affects pagination or search results in other tests. This leads to false positives/negatives in the test suite and reduced confidence in test results.

**Functional Requirements:**

1. Each E2E test should execute in isolation without affecting other tests
2. Test data should be properly cleaned up after each test run (or before each test)
3. Tests should not depend on execution order or data created by other tests
4. Solution should work with existing Playwright infrastructure

**Non-Functional Requirements:**

- **Reliability:** Eliminate test flakiness caused by shared state
- **Performance:** Cleanup should not significantly slow down test execution (target: <500ms overhead per test)
- **Maintainability:** Solution should be easy to understand and maintain
- **Developer Experience:** Minimal changes to existing test code

**Constraints:**

- Must work with existing Playwright E2E test infrastructure
- Should not break currently passing tests
- 3-hour effort budget (medium priority technical debt)
- Must not require significant backend infrastructure changes

---

## Context Discovery Findings

### Product Scope

**Relevant User Stories:**

- As a developer, I want reliable E2E tests so I can confidently merge changes
- As a developer, I want fast test feedback so I can iterate quickly
- As a QA engineer, I want deterministic tests so I can trust the results

### Architecture Context

**Bounded Contexts Involved:**

- **Testing Infrastructure:** E2E test setup and teardown
- **Database Context:** Test database isolation
- **Cross-Cutting:** Test data management

**Existing Patterns:**

- **Backend:** Uses pytest fixtures with transaction rollback for unit tests (`backend/tests/conftest.py`)
- **Backend:** Implements `TRUNCATE TABLE` strategy for test cleanup (line 118 in conftest.py)
- **Frontend:** Playwright E2E tests with `beforeEach` login setup
- **Frontend:** No current database cleanup hooks in E2E tests

**Coding Standards:**

- Type safety enforced (strict TypeScript)
- Test isolation as core principle
- Clean architecture with separation of concerns

### Codebase Analysis

**Backend (`backend/tests/conftest.py`):**

```python
# Existing pattern for backend unit tests (lines 114-124)
async with async_session_maker() as session:
    try:
        await session.execute(
            text(
                "TRUNCATE TABLE cost_elements, cost_element_types, wbes, projects, departments, users RESTART IDENTITY CASCADE"
            )
        )
        await session.commit()
    except Exception:
        await session.rollback()
```

**Key Observations:**

- Backend unit tests already implement database cleanup via TRUNCATE
- TRUNCATE occurs **before** each test in the `db_session` fixture
- Uses `RESTART IDENTITY CASCADE` to reset auto-increment counters
- Tables hardcoded (not dynamically discovered)

**Frontend (`frontend/tests/e2e/`):**

- **Test Files:** 9 E2E test files found
- **Structure:** All use `test.beforeEach` for authentication setup
- **No Cleanup:** No `afterEach` or `afterAll` hooks for database cleanup
- **Playwright Config:** `playwright.config.ts` has no globalSetup/globalTeardown

**Key Files:**

- `frontend/tests/e2e/projects_crud.spec.ts` - Creates timestamped projects
- `frontend/tests/e2e/wbe_crud.spec.ts` - Creates WBEs
- `frontend/tests/e2e/cost_elements_crud.spec.ts` - Creates cost elements

**Test Data Patterns:**

```typescript
// All tests use timestamps for uniqueness
const timestamp = Date.now();
const projectCode = `E2E-${timestamp}`;
```

**Problem Manifestation:**

- Tests create unique data via timestamps (good for isolation)
- BUT data accumulates across test runs
- Pagination tests may show varying page counts
- Search tests may find unexpected results from previous runs
- No explicit cleanup between tests

---

## Solution Options

### Option 1: Playwright Global Setup with Database Truncate (Recommended)

**Approach Summary:**

Create a Playwright global setup script that truncates the test database before the entire test suite runs. Use a dedicated backend API endpoint or direct database connection to perform the cleanup.

**Architecture & Design:**

```
Playwright Test Suite
├── globalSetup.ts (NEW)
│   ├── Connect to test database
│   ├── Execute TRUNCATE via backend API or direct connection
│   └── Verify cleanup success
├── playwright.config.ts (MODIFIED)
│   └── Configure globalSetup path
└── Individual test files (UNCHANGED)
```

**Component Structure:**

1. **`frontend/tests/setup/globalSetup.ts`** - Playwright global setup hook
2. **Backend API Endpoint (Option A):** `POST /api/v1/test/reset-database` (protected by env check)
3. **Direct DB Connection (Option B):** Use `pg` client to connect directly

**UX Design:**

- **Developer Experience:** No changes to individual test files
- **Visual Feedback:** Console log showing database reset status
- **Error Handling:** Clear error messages if cleanup fails

**Technical Implementation:**

**Option 1A: Backend API Endpoint Approach**

```typescript
// frontend/tests/setup/globalSetup.ts
import { chromium } from "@playwright/test";

async function globalSetup() {
  console.log("🧹 Resetting test database...");

  const browser = await chromium.launch();
  const context = await browser.newContext();
  const page = await context.newPage();

  // 1. Login as admin
  await page.goto("http://localhost:5173/login");
  await page.fill('input[id="login_email"]', "admin@backcast.org");
  await page.fill('input[id="login_password"]', "adminadmin");
  await page.click('button[type="submit"]');
  await page.waitForURL("/");

  // 2. Call cleanup endpoint
  const response = await page.request.post(
    "http://localhost:8000/api/v1/test/reset-database"
  );

  if (!response.ok()) {
    throw new Error(`Database reset failed: ${response.status()}`);
  }

  console.log("✅ Test database reset complete");

  await browser.close();
}

export default globalSetup;
```

```python
# backend/app/api/routes/test.py (NEW - only enabled in test mode)
from fastapi import APIRouter, Depends HTTPException, status
from sqlalchemy import text
from app.core.config import settings
from app.db.session import get_db

router = APIRouter(prefix="/test", tags=["test"])

@router.post("/reset-database")
async def reset_database(session: AsyncSession = Depends(get_db)):
    """Reset test database. Only available in test environment."""
    if settings.ENVIRONMENT != "test":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This endpoint is only available in test environment"
        )

    try:
        await session.execute(
            text(
                "TRUNCATE TABLE cost_elements, cost_element_types, wbes, projects, departments, users RESTART IDENTITY CASCADE"
            )
        )
        await session.commit()
        return {"status": "success", "message": "Database reset complete"}
    except Exception as e:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database reset failed: {str(e)}"
        ) from e
```

**Option 1B: Direct Database Connection Approach**

```typescript
// frontend/tests/setup/globalSetup.ts
import pg from "pg";

async function globalSetup() {
  console.log("🧹 Resetting test database (direct connection)...");

  const client = new pg.Client({
    connectionString:
      process.env.DATABASE_URL ||
      "postgresql://postgres:postgres@localhost:5432/backcast_evs",
  });

  try {
    await client.connect();
    await client.query(`
      TRUNCATE TABLE cost_elements, cost_element_types, wbes, projects, departments, users RESTART IDENTITY CASCADE
    `);
    console.log("✅ Test database reset complete");
  } catch (error) {
    console.error("❌ Database reset failed:", error);
    throw error;
  } finally {
    await client.end();
  }
}

export default globalSetup;
```

**Trade-offs:**

| Aspect              | Assessment                                                                                                                                                                                                             |
| ------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Pros**            | ✅ Single cleanup point (runs once before all tests)<br>✅ Fast (no per-test overhead)<br>✅ No changes to existing test files<br>✅ Leverages existing backend cleanup logic<br>✅ Works with parallel test execution |
| **Cons**            | ⚠️ Requires backend API endpoint (Option A) or direct DB access (Option B)<br>⚠️ Cleanup only at start, not between tests<br>⚠️ Tests must still use unique identifiers (timestamps)                                   |
| **Complexity**      | **Low** - Single file addition, minimal backend changes                                                                                                                                                                |
| **Maintainability** | **Excellent** - Central cleanup logic, easy to update table list                                                                                                                                                       |
| **Performance**     | **Optimal** - Single cleanup operation (~100ms)                                                                                                                                                                        |

---

### Option 2: Per-Test Database Snapshots with Rollback

**Approach Summary:**

Use database transactions or snapshots to create a clean state before each test and rollback after completion, similar to backend unit test pattern.

**Architecture & Design:**

```
Each Test Execution
├── beforeEach: Start transaction/snapshot
├── Test executes
└── afterEach: Rollback transaction
```

**Technical Implementation:**

```typescript
// frontend/tests/setup/testHooks.ts
import { test as base } from "@playwright/test";
import pg from "pg";

export const test = base.extend({
  databaseIsolation: async ({}, use) => {
    const client = new pg.Client({
      /* ... */
    });
    await client.connect();

    // Start transaction
    await client.query("BEGIN");

    // Run test
    await use();

    // Rollback transaction
    await client.query("ROLLBACK");
    await client.end();
  },
});

// Usage in tests
test("should create project", async ({ page, databaseIsolation }) => {
  // Test code
});
```

**Trade-offs:**

| Aspect              | Assessment                                                                                                                                                                                                                                  |
| ------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Pros**            | ✅ True test isolation (each test starts with clean state)<br>✅ No test data pollution<br>✅ Matches backend unit test pattern                                                                                                             |
| **Cons**            | ❌ Complex to implement with frontend E2E tests<br>❌ Per-test overhead (~200-500ms per test)<br>❌ May conflict with backend API transactions<br>❌ Difficult to manage with parallel execution<br>❌ All existing tests need modification |
| **Complexity**      | **High** - Complex transaction management across API boundary                                                                                                                                                                               |
| **Maintainability** | **Poor** - Fragile, hard to debug transaction conflicts                                                                                                                                                                                     |
| **Performance**     | **Poor** - Significant per-test overhead                                                                                                                                                                                                    |

**Risk Level:** **High** - Transaction management across API boundary is error-prone

---

### Option 3: Per-Test Cleanup via `afterAll` Hook

**Approach Summary:**

Add `test.afterAll()` hooks to each test file to clean up data created by that specific test suite.

**Architecture & Design:**

```
Test File (projects_crud.spec.ts)
├── beforeEach: Login
├── test 1: Create project
├── test 2: Update project
├── test 3: Delete project
└── afterAll: Cleanup all projects created in this file
```

**Technical Implementation:**

```typescript
// frontend/tests/e2e/projects_crud.spec.ts
test.describe("Project CRUD", () => {
  const createdProjectIds: string[] = [];

  test.beforeEach(async ({ page }) => {
    // Existing login logic
  });

  test.afterAll(async ({ request }) => {
    console.log(`Cleaning up ${createdProjectIds.length} test projects`);
    for (const id of createdProjectIds) {
      try {
        await request.delete(`http://localhost:8000/api/v1/projects/${id}`);
      } catch (error) {
        console.warn(`Failed to cleanup project ${id}:`, error);
      }
    }
  });

  test("should create project", async ({ page }) => {
    // ... create project ...
    // Track ID for cleanup
    const projectId = await page
      .locator('[data-test-id="project-id"]')
      .textContent();
    createdProjectIds.push(projectId);
  });
});
```

**Trade-offs:**

| Aspect              | Assessment                                                                                                                                                                                  |
| ------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Pros**            | ✅ Granular cleanup (only data from this test file)<br>✅ No global state dependency<br>✅ Works with parallel execution                                                                    |
| **Cons**            | ❌ Requires modifying ALL test files (~9 files)<br>❌ Must track entity IDs across tests<br>❌ Cleanup logic duplicated per file<br>❌ Delete operations may fail if test assertions failed |
| **Complexity**      | **Moderate** - Repetitive but straightforward                                                                                                                                               |
| **Maintainability** | **Fair** - Duplication across test files                                                                                                                                                    |
| **Performance**     | **Moderate** - Cleanup overhead per test file                                                                                                                                               |

---

## Comparison Summary

| Criteria                  | Option 1: Global Setup | Option 2: Snapshot/Rollback  | Option 3: afterAll Cleanup |
| ------------------------- | ---------------------- | ---------------------------- | -------------------------- |
| **Implementation Effort** | 1-2 hours              | 4-6 hours                    | 2-3 hours                  |
| **Test File Changes**     | None                   | All (~9 files)               | All (~9 files)             |
| **Performance Impact**    | Minimal (once)         | High (per-test)              | Moderate (per-file)        |
| **Isolation Quality**     | Good (start clean)     | Excellent (per-test)         | Good (per-file)            |
| **Complexity**            | Low                    | High                         | Moderate                   |
| **Maintainability**       | Excellent              | Poor                         | Fair                       |
| **Parallel Execution**    | ✅ Compatible          | ⚠️ Difficult                 | ✅ Compatible              |
| **Risk Level**            | Low                    | High                         | Medium                     |
| **Best For**              | Quick wins, full reset | Perfect isolation (overkill) | Gradual migration          |

---

## Recommendation

**Selected Option: Option 1 - Global Setup with Database Truncate (Variant B: Direct Connection)**

### Justification

1. **Effort vs Impact:** Highest value-to-effort ratio (1-2 hours vs 3-hour budget)
2. **Minimal Disruption:** No changes to existing test files
3. **Performance:** Single cleanup operation, no per-test overhead
4. **Simplicity:** Leverages existing backend cleanup pattern
5. **Maintainability:** Central point of control
6. **Aligns with Backend Pattern:** Matches the `backend/tests/conftest.py` approach

**Why Direct Connection (1B) over API Endpoint (1A):**

- **Simpler:** No backend code changes required
- **Faster:** No HTTP round-trip or authentication
- **Self-Contained:** Frontend test infrastructure is independent
- **Lower Risk:** No new API endpoints to secure

**Hybrid Enhancement (Optional):**

After implementing Option 1, we can **gradually** add `afterAll` cleanup hooks (Option 3) to high-churn test files for additional cleanup of test-specific data. This provides:

- Immediate baseline via global setup
- Incremental refinement for problem areas
- No blocking dependency

---

## Alternative Consideration

**When to choose Option 2 (Snapshot/Rollback):**

Only if we experience severe test interference issues AFTER implementing Option 1 and it proves insufficient. Current evidence suggests Option 1 will resolve most flakiness.

**When to choose Option 3 (afterAll):**

If we want fine-grained cleanup without global setup, or if test data accumulates significantly within a single test suite run.

---

## Questions for Decision

1. **Database Access:** Do we have direct database connection credentials available in the E2E test environment?  
   ✅ **Assumed Yes** - can use same DATABASE_URL as backend tests

2. **Table List Maintenance:** Should we auto-discover tables or maintain hardcoded list?  
   ✅ **Recommended: Hardcoded** - Explicit list prevents accidental deletion of non-test tables

3. **Cleanup Timing:** Run cleanup before tests, after tests, or both?  
   ✅ **Recommended: Before** - Ensures clean slate regardless of previous run state

4. **Error Handling:** Should test suite fail if cleanup fails?  
   ✅ **Recommended: Yes** - Fail-fast prevents cascading failures from dirty state

---

## Related Documentation

- [Technical Debt Register](../../technical-debt-register.md) - TD-012
- [Backend Test Patterns](../../../backend/tests/conftest.py) - Reference implementation
- [Coding Standards](../../../02-architecture/coding-standards.md) - Testing principles
- [Playwright Documentation](https://playwright.dev/docs/test-global-setup-teardown) - Global setup patterns

---

**Next Phase:** PLAN - Detailed implementation plan for Option 1B
