# ACT: E2E Test Data Isolation - Standardization & Closure

**Iteration:** E2E Test Data Isolation
**Date:** 2026-01-09
**Status:** ✅ **CLOSED**

---

## Standardization

### Solution Adopted

**Global Database Reset & Reseed** via Playwright `globalSetup`.

**Pattern:**

1. **Truncate:** Aggressively clean all business data tables (`TRUNCATE ... CASCADE`).
2. **Reseed:** Run `scripts/reseed.py` to restore static reference data (Users, Departments, Types).
3. **Execute:** Run tests against this known clean state.

### Updated Standards

**1. E2E Testing Guidelines:**

- **Pre-requisite:** All E2E runs now automatically trigger a DB reset.
- **Reference Data:** Tests should assume standard seed data exists (e.g., `admin@backcast.org`).
- **Isolation:** Tests must not depend on data from previous suites (guaranteed by this fix).

**2. New Infrastructure:**

- `frontend/tests/setup/globalSetup.ts`: Central registry for test database initialization.
- `scripts/reseed.py`: Python script for generating baseline test data.

---

## Lessons Learned

1. **Clean Slate vs. usable Slate:**

   - Truncation alone is insufficient because the app requires baseline data (Users, Departments) to function.
   - **Improvement:** Always pair Truncate with Reseed for integration/E2E environments.

2. **Cross-Language Integration:**

   - Leveraging existing Python seeding logic from Node/Playwright context proved efficient (`execSync`).
   - Avoids duplicating seeding logic in TypeScript.

3. **ES Modules in Node:**
   - Playwright runs in a Node environment where ES modules require explicit `import.meta.url` handling for file paths.

---

## Future Improvements (Backlog)

| Item                        | Description                                                                                           | Priority |
| --------------------------- | ----------------------------------------------------------------------------------------------------- | -------- |
| **Dynamic Table Discovery** | Auto-discover tables to truncate instead of hardcoding list to avoid maintenance drift.               | Low      |
| **Optimized Seeding**       | Python reseed script takes ~1-2s. Could be optimized or replaced with a SQL dump restore for speed.   | Low      |
| **Per-File Isolation**      | If tests manage to pollute state _during_ a parallel run significantly, granular hooks may be needed. | Low      |

---

## Closure Status

- **Technical Debt Item:** TD-012
- **Resolution:** Fixed.
- **Verification:** Completed in CHECK phase.
- **Docs Updated:** Technical Debt Register, Project Plan.

**Iteration Closed.**
