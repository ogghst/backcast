# PLAN: E2E Test Data Isolation

**Iteration:** E2E Test Data Isolation  
**Date:** 2026-01-09  
**Status:** 📋 **PLANNED** - Ready for Implementation  
**Priority:** High (TD-012 - First in paydown plan)

---

## Phase 1: Context Analysis

### Documentation Review

**Architecture Context:**

- **Coding Standards:** Testing isolation as core principle
- **Backend Pattern:** `backend/tests/conftest.py` implements TRUNCATE cleanup
- **Current E2E Setup:** No cleanup hooks, tests use timestamps for uniqueness
- **Technical Debt:** TD-012 identified test flakiness from shared database state

**Recent Work:**

- **2026-01-09:** E2E Test Stabilization completed
- **2026-01-08:** Server-side filtering Phase 2 completed
- Current focus: Technical debt paydown

### Codebase Analysis

**Affected Files:**

1. **NEW:** `frontend/tests/setup/globalSetup.ts` - Database cleanup logic
2. **MODIFIED:** `frontend/playwright.config.ts` - Add globalSetup configuration
3. **NEW:** `frontend/tests/setup/.env.test` - Test environment variables (optional)
4. **MODIFIED:** `frontend/package.json` - Add `pg` dependency

**Existing Infrastructure:**

- ✅ Playwright test framework configured
- ✅ Backend database with known schema
- ✅ Environment variables in `.env` file
- ✅ Backend cleanup pattern to reference

**Database Credentials:**

```env
POSTGRES_USER=backcast
POSTGRES_PASSWORD=backcast
POSTGRES_DB=backcast_evs
POSTGRES_SERVER=localhost
POSTGRES_PORT=5433
```

---

## Phase 2: Problem Definition

### Problem Statement

**What:** E2E tests share database state, causing occasional flakiness when tests create data that affects pagination or search results in other tests.

**Why Important:** Test flakiness reduces confidence in CI/CD pipeline and slows down development velocity.

**Business Impact:**

- **Severity:** Medium - Affects developer productivity
- **User Impact:** Indirect (developers waste time debugging false failures)
- **Scope:** All 9 E2E test files
- **Root Cause:** No database cleanup between test suite runs

**What happens if not addressed:**

- Continued test flakiness and false failures
- Developers lose trust in E2E test results
- Increased time debugging test failures vs real bugs
- Difficulty scaling E2E test coverage

**Business Value:**

- Reliable test suite enables confident deployments
- Faster feedback loop for developers
- Foundation for expanding E2E test coverage

### Success Criteria (Measurable)

**Functional Criteria:**

- [ ] Database is cleaned before each test suite run
- [ ] All tables are truncated with identity reset
- [ ] Tests pass consistently across multiple runs
- [ ] No test data pollution between runs
- [ ] Cleanup completes in <500ms

**Technical Criteria:**

- [ ] TypeScript type checking passes
- [ ] No changes required to existing test files
- [ ] Works with parallel test execution (`--workers=4`)
- [ ] Clear error messages if cleanup fails
- [ ] Environment-aware (only runs in test environment)

**Test Coverage:**

- [ ] Verify cleanup executes before test suite
- [ ] Verify all tables are empty after cleanup
- [ ] Verify cleanup handles connection errors gracefully
- [ ] Verify cleanup logs success/failure clearly

**Edge Cases Handled:**

- [ ] Database connection failure → Fail test suite with clear error
- [ ] Missing environment variables → Fail with helpful message
- [ ] Tables don't exist yet → Handle gracefully (first run)
- [ ] Cleanup timeout → Fail after 5 seconds

### Scope Definition

**In Scope:**

1. **Global Setup Script:**

   - Create `frontend/tests/setup/globalSetup.ts`
   - Implement database connection logic
   - Execute TRUNCATE on all tables
   - Error handling and logging

2. **Playwright Configuration:**

   - Update `playwright.config.ts` to reference globalSetup
   - Configure environment variables

3. **Dependencies:**

   - Add `pg` package for PostgreSQL connection
   - Add `dotenv` for environment variable loading

4. **Documentation:**
   - Update this PLAN document with implementation details
   - Create DO document during implementation
   - Document troubleshooting steps

**Out of Scope:**

- Per-test cleanup (not needed with global setup)
- Backend API endpoint for cleanup (using direct connection)
- Changes to existing test files
- Database migration or schema changes
- Transaction-based isolation (too complex)

**Deferred to Future:**

- Per-test-file cleanup hooks (only if global setup proves insufficient)
- Automated table discovery (hardcoded list is safer)
- Test data seeding (separate concern)

**Assumptions:**

- Database credentials are available in environment
- Test database is same as used by backend tests
- Playwright has network access to database
- Tables to truncate are known and stable

---

## Phase 3: Implementation Options

### Selected Option: Global Setup with Direct Database Connection

**Approach Summary:**

Create a Playwright global setup script that connects directly to the PostgreSQL test database and truncates all tables before the test suite runs. This leverages the same pattern used in `backend/tests/conftest.py`.

**Design Patterns:**

- **Global Setup Hook:** Playwright's built-in lifecycle hook
- **Direct Database Access:** PostgreSQL client library (`pg`)
- **Fail-Fast:** Abort test suite if cleanup fails
- **Environment-Aware:** Only operates on test database

**Architecture:**

```
Playwright Test Suite Execution
├── 1. globalSetup.ts executes (ONCE)
│   ├── Load environment variables
│   ├── Connect to PostgreSQL
│   ├── Execute TRUNCATE on all tables
│   ├── Verify success
│   └── Close connection
├── 2. All test files execute (PARALLEL)
│   └── Tests run with clean database
└── 3. Test suite completes
```

**Data Flow:**

```
.env file → globalSetup.ts → PostgreSQL Database
                ↓
         TRUNCATE TABLE cost_elements, cost_element_types,
         wbes, projects, departments, users
         RESTART IDENTITY CASCADE
                ↓
         Clean database state for all tests
```

**Pros:**

- ✅ Single cleanup point (runs once)
- ✅ Fast (no per-test overhead)
- ✅ No changes to existing test files
- ✅ Leverages existing backend pattern
- ✅ Works with parallel execution
- ✅ Self-contained (no backend changes)

**Cons:**

- ⚠️ Requires `pg` dependency
- ⚠️ Hardcoded table list (must maintain)
- ⚠️ Cleanup only at start (not between tests)

**Risk Level:** **Low**

- Well-established pattern (backend uses same approach)
- Simple implementation
- Easy to rollback (just remove globalSetup config)

**Estimated Complexity:** **Low**

- Single file creation
- Simple configuration change
- Straightforward database operation

---

## Phase 4: Technical Design

### TDD Test Blueprint

**Manual Verification Steps:**

```bash
# 1. Run tests multiple times to verify consistency
npm run e2e -- tests/e2e/projects_crud.spec.ts
npm run e2e -- tests/e2e/projects_crud.spec.ts  # Should pass again

# 2. Verify database is clean before tests
psql -h localhost -p 5433 -U backcast -d backcast_evs -c "SELECT COUNT(*) FROM projects;"
# Should return 0 after cleanup

# 3. Verify cleanup logs appear
npm run e2e 2>&1 | grep "Resetting test database"
# Should show cleanup message

# 4. Verify cleanup handles errors
# (Temporarily break DB connection string)
npm run e2e
# Should fail with clear error message
```

**Test Scenarios:**

1. **Happy Path:** Cleanup succeeds, tests run with clean database
2. **Connection Failure:** Invalid credentials → Clear error message
3. **Missing Tables:** First run → Graceful handling
4. **Timeout:** Slow database → Fail after timeout
5. **Parallel Execution:** Multiple workers → No conflicts

### Implementation Strategy

#### High-Level Approach

**Phase 1: Dependencies (5 minutes)**

- Install `pg` package
- Verify `dotenv` is available (already in project)

**Phase 2: Global Setup Script (30 minutes)**

- Create `frontend/tests/setup/globalSetup.ts`
- Implement database connection logic
- Implement TRUNCATE logic
- Add error handling and logging

**Phase 3: Configuration (10 minutes)**

- Update `playwright.config.ts`
- Configure environment variables
- Test configuration

**Phase 4: Verification (20 minutes)**

- Run tests multiple times
- Verify cleanup logs
- Test error scenarios
- Verify parallel execution

**Phase 5: Documentation (15 minutes)**

- Update this PLAN document
- Create DO document
- Add troubleshooting guide

**Total Estimated Time:** 1.5 hours

#### Key Technologies/Patterns

- **PostgreSQL Client:** `pg` library for Node.js
- **Environment Variables:** `dotenv` for configuration
- **Playwright Hooks:** `globalSetup` lifecycle hook
- **Error Handling:** Try-catch with descriptive messages
- **Logging:** Console output for visibility

#### Component Breakdown

**1. Global Setup Script (`frontend/tests/setup/globalSetup.ts`):**

```typescript
import { Client } from "pg";
import * as dotenv from "dotenv";
import * as path from "path";

/**
 * Playwright global setup hook.
 * Resets the test database before the entire test suite runs.
 */
async function globalSetup() {
  console.log("🧹 Resetting test database...");

  // Load environment variables from project root
  dotenv.config({ path: path.resolve(__dirname, "../../../.env") });

  // Build connection string from environment variables
  const connectionString = `postgresql://${process.env.POSTGRES_USER}:${process.env.POSTGRES_PASSWORD}@${process.env.POSTGRES_SERVER}:${process.env.POSTGRES_PORT}/${process.env.POSTGRES_DB}`;

  const client = new Client({ connectionString });

  try {
    // Connect to database
    await client.connect();
    console.log("✅ Connected to test database");

    // Truncate all tables with CASCADE to handle foreign keys
    // RESTART IDENTITY resets auto-increment counters
    await client.query(`
      TRUNCATE TABLE 
        cost_elements, 
        cost_element_types, 
        wbes, 
        projects, 
        departments, 
        users 
      RESTART IDENTITY CASCADE
    `);

    console.log("✅ Test database reset complete");
  } catch (error) {
    console.error("❌ Database reset failed:", error);
    throw new Error(
      `Failed to reset test database. Please check your database connection and credentials.\n${error}`
    );
  } finally {
    // Always close the connection
    await client.end();
  }
}

export default globalSetup;
```

**2. Playwright Configuration Update (`frontend/playwright.config.ts`):**

```typescript
import { defineConfig, devices } from "@playwright/test";

export default defineConfig({
  testDir: "./tests/e2e",
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,
  reporter: "html",

  // Add global setup
  globalSetup: "./tests/setup/globalSetup.ts",

  use: {
    baseURL: "http://localhost:5173",
    trace: "on-first-retry",
  },
  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"] },
    },
  ],
  webServer: {
    command: "npm run dev",
    url: "http://localhost:5173",
    reuseExistingServer: !process.env.CI,
  },
});
```

**3. Package.json Update:**

```json
{
  "devDependencies": {
    "@playwright/test": "^1.49.0",
    "pg": "^8.13.1",
    "dotenv": "^16.4.7"
    // ... other dependencies
  }
}
```

#### Integration Points

**Environment Variables:**

- Read from `.env` file in project root
- Same credentials as backend tests
- No new environment setup required

**Database Connection:**

- Direct PostgreSQL connection via `pg` client
- Same database as backend tests (`backcast_evs`)
- Same port (5433) and credentials

**Playwright Lifecycle:**

- `globalSetup` runs **once** before all tests
- Executes before `beforeEach` hooks in test files
- Failures abort the entire test suite

**Table List Maintenance:**

```typescript
// Tables to truncate (in dependency order)
const TABLES_TO_TRUNCATE = [
  "cost_elements", // Child of wbes
  "cost_element_types", // Standalone
  "wbes", // Child of projects
  "projects", // Child of departments
  "departments", // Standalone
  "users", // Standalone
];
```

**Note:** Order doesn't matter with `CASCADE`, but explicit ordering improves readability.

---

## Phase 5: Risk Assessment

### Risks and Mitigations

| Risk Type       | Description                          | Probability | Impact | Mitigation Strategy                                                                                                  |
| --------------- | ------------------------------------ | ----------- | ------ | -------------------------------------------------------------------------------------------------------------------- |
| **Technical**   | Database connection failure          | Low         | High   | 1. Validate credentials in setup<br>2. Clear error messages<br>3. Fail-fast to prevent cascading failures            |
| **Technical**   | Missing environment variables        | Low         | High   | 1. Check for required vars<br>2. Provide helpful error message<br>3. Document required vars                          |
| **Technical**   | TRUNCATE fails on missing tables     | Low         | Medium | 1. Use try-catch<br>2. Log warning but continue<br>3. Handle gracefully on first run                                 |
| **Integration** | Conflicts with running backend tests | Low         | Medium | 1. Document that E2E tests should not run concurrently with backend tests<br>2. Use same database (already the case) |
| **Performance** | Cleanup takes too long               | Very Low    | Low    | 1. Set timeout (5 seconds)<br>2. Monitor execution time<br>3. Optimize if needed                                     |
| **Maintenance** | Table list becomes outdated          | Medium      | Low    | 1. Document update process<br>2. Add comment linking to schema<br>3. Consider automated discovery in future          |

### Critical Integration Points

**Risk: Environment Variable Loading**

- **Issue:** `.env` file not found or variables not loaded
- **Mitigation:** Use absolute path resolution, validate vars exist
- **Validation:** Log loaded values (mask password)

**Risk: Database Connection Timeout**

- **Issue:** Database not available or slow to respond
- **Mitigation:** Set connection timeout, fail with clear message
- **Validation:** Test with database stopped

**Risk: Parallel Test Execution**

- **Issue:** Multiple workers trying to cleanup simultaneously
- **Mitigation:** Global setup runs **once** before workers start (Playwright guarantee)
- **Validation:** Run with `--workers=4` and verify single cleanup

---

## Phase 6: Effort Estimation

### Time Breakdown

**Development:**

- Install dependencies: 5 minutes
- Create globalSetup.ts: 30 minutes
- Update playwright.config.ts: 5 minutes
- **Subtotal:** **40 minutes**

**Testing:**

- Manual verification (multiple runs): 10 minutes
- Error scenario testing: 10 minutes
- Parallel execution testing: 5 minutes
- **Subtotal:** **25 minutes**

**Documentation:**

- Update PLAN document: 10 minutes
- Create DO document: 10 minutes
- Add troubleshooting guide: 5 minutes
- **Subtotal:** **25 minutes**

**Total Estimated Effort:** **1.5 hours** (within 3-hour budget)

### Effort by Phase

| Phase          | Minutes | Description                           |
| -------------- | ------- | ------------------------------------- |
| Dependencies   | 5       | Install `pg` package                  |
| Implementation | 35      | Create globalSetup.ts, update config  |
| Testing        | 25      | Verify cleanup works, test edge cases |
| Documentation  | 25      | Update docs, create DO                |
| **Total**      | **90**  | **1.5 hours**                         |

### Prerequisites

**Before Starting:**

- [x] Database credentials confirmed in `.env` file
- [ ] Backend is running (for E2E tests)
- [ ] No other test suites running (to avoid conflicts)
- [ ] Create feature branch: `fix/e2e-test-isolation`

**During Development:**

- [ ] Update sprint backlog with task breakdown
- [ ] Create this PLAN document ✅
- [ ] Track time spent vs estimate

**Infrastructure Needed:**

- [x] PostgreSQL database running on port 5433
- [x] Node.js environment with npm
- [x] Playwright installed
- [x] Environment variables configured

---

## Implementation Task Breakdown

### Phase 1: Dependencies (5 minutes)

- [ ] Install `pg` package: `npm install --save-dev pg @types/pg`
- [ ] Verify `dotenv` is available (already in dependencies)
- [ ] Commit dependency changes

### Phase 2: Global Setup Script (35 minutes)

**Create File (20 minutes):**

- [ ] Create directory: `frontend/tests/setup/`
- [ ] Create file: `frontend/tests/setup/globalSetup.ts`
- [ ] Implement database connection logic
- [ ] Implement TRUNCATE logic
- [ ] Add error handling and logging
- [ ] Add TypeScript types

**Configuration Update (5 minutes):**

- [ ] Update `frontend/playwright.config.ts`
- [ ] Add `globalSetup: './tests/setup/globalSetup.ts'`
- [ ] Verify TypeScript compilation

**Code Review (10 minutes):**

- [ ] Review code for type safety
- [ ] Verify error messages are clear
- [ ] Check logging is informative
- [ ] Ensure connection is always closed

### Phase 3: Testing (25 minutes)

**Happy Path (10 minutes):**

- [ ] Run E2E tests: `npm run e2e`
- [ ] Verify cleanup message appears in console
- [ ] Verify tests pass
- [ ] Run tests again to verify consistency
- [ ] Check database is empty after cleanup

**Error Scenarios (10 minutes):**

- [ ] Test with invalid database credentials
- [ ] Verify clear error message
- [ ] Test with database stopped
- [ ] Verify timeout behavior

**Parallel Execution (5 minutes):**

- [ ] Run with `--workers=4`
- [ ] Verify single cleanup execution
- [ ] Verify all tests pass

### Phase 4: Documentation (25 minutes)

**Update PLAN Document (10 minutes):**

- [ ] Mark tasks as complete
- [ ] Update status to "Complete"
- [ ] Add any lessons learned

**Create DO Document (10 minutes):**

- [ ] Document implementation steps taken
- [ ] Include code snippets
- [ ] Note any deviations from plan
- [ ] Record actual time spent

**Troubleshooting Guide (5 minutes):**

- [ ] Document common errors
- [ ] Add resolution steps
- [ ] Include verification commands

---

## Approval

**Status:** 📋 **READY FOR IMPLEMENTATION**

**Approved By:** Nicola (User)  
**Approval Date:** 2026-01-09  
**Implementation Start:** 2026-01-09

---

## Related Documentation

- **Analysis:** [00-ANALYSIS.md](./00-ANALYSIS.md)
- **Technical Debt Register:** [TD-012](../../technical-debt-register.md)
- **Backend Test Pattern:** `backend/tests/conftest.py` (reference implementation)
- **Coding Standards:** [Testing Principles](../../../02-architecture/coding-standards.md#23-testing-strategy)
- **Playwright Docs:** [Global Setup](https://playwright.dev/docs/test-global-setup-teardown)

---

## Implementation Checklist

### Pre-Implementation

- [x] Analysis document approved
- [x] Database credentials confirmed
- [ ] Feature branch created: `fix/e2e-test-isolation`
- [ ] Backend server running
- [ ] No conflicting test runs

### Implementation

- [ ] Install `pg` dependency
- [ ] Create `globalSetup.ts` file
- [ ] Update `playwright.config.ts`
- [ ] Verify TypeScript compilation
- [ ] Test cleanup execution
- [ ] Test error scenarios
- [ ] Test parallel execution

### Post-Implementation

- [ ] All E2E tests pass
- [ ] Cleanup logs visible in console
- [ ] Database verified empty after cleanup
- [ ] Documentation updated
- [ ] DO document created
- [ ] Code reviewed
- [ ] Merge to main branch

---

**Next Phase:** DO - Implementation with verification testing
