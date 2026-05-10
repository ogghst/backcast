# Change Order E2E Test Report

**Date:** 2026-05-10  
**Tester:** Claude AI (Automated UI Testing with Playwright)  
**Test Environment:** Development (localhost:5173 frontend, localhost:8020 backend)  
**Project:** CO E2E Robot Cell (CO-E2E-ROBOT)  

---

## Executive Summary

Comprehensive end-to-end testing of the Change Order lifecycle was performed using Playwright MCP in headless browser mode. The testing covered creation, draft workflow, submit for approval, and state transitions. Multiple issues were identified that require attention before production deployment.

**Overall Status:** ⚠️ **PARTIAL SUCCESS** - Core workflow functional but critical branch isolation issue found.

---

## Test Environment Setup

### Infrastructure
- **Backend:** Python/FastAPI on port 8020 (uvicorn server)
- **Frontend:** React/Vite on port 5173 (dev server)
- **Database:** PostgreSQL 15 (Docker container backcast-postgres-1)
- **Authentication:** JWT Bearer tokens

### Test Users Available
| Email | Role | Full Name |
|-------|------|-----------|
| admin@backcast.org | admin | System Administrator |
| pm@backcast.org | manager | Project Manager |
| dept.head@backcast.org | dept_head | Department Head |
| director@backcast.org | viewer | Director |
| viewer@backcast.org | viewer | Viewer User |

### Test Project
- **Project ID:** 406a9c3e-d35b-4340-897d-ba314feb9b64
- **Code:** CO-E2E-ROBOT
- **Name:** CO E2E Robot Cell
- **Status:** Active
- **Initial Budget:** €395,000
- **Root WBEs:** Control System (€105K), Robot Assembly (€230K), Safety Systems (€60K)

---

## Test Cases Executed

### ✅ Test 1: Change Order Creation (DRAFT)
**Status:** PASSED

**Steps:**
1. Navigated to Projects → CO E2E Robot Cell → Change Orders
2. Clicked "New Change Order" button
3. Filled in form:
   - Code: CO-2026-016 (auto-generated)
   - Title: "E2E Test Change Order - Budget Modification"
   - Description: Full test description
   - Justification: Testing full lifecycle
4. Clicked "Create"

**Result:**
- Change Order created successfully
- Status: Draft
- Branch created: BR-CO-2026-016
- Database verification: ✅ Confirmed in `change_orders` table

**API Calls:**
- POST `/api/v1/change-orders` → 201 Created

---

### ✅ Test 2: Branch Switching (DRAFT MODE)
**Status:** PASSED

**Steps:**
1. Clicked "Toggle time machine panel" button
2. Selected "[Draft] BR-CO-2026-016" from branch dropdown
3. Verified branch indicator changed from "main" to "BR-CO-2026-016"

**Result:**
- Successfully switched to change order branch
- UI shows correct branch context in header
- Time machine panel displays available branches

**Branches Available:**
- main (default)
- [Draft] BR-CO-2026-016
- [Implemented] BR-CO-2026-015
- [Under Review] BR-CO-2026-014
- [Implemented] BR-CO-2026-013

---

### ⚠️ Test 3: Draft Mode CRUD Operations - CRITICAL BUG FOUND
**Status:** FAILED - Branch isolation not working

**Steps:**
1. Navigated to Project Structure on BR-CO-2026-016 branch
2. Expanded Control System WBE to view cost elements
3. Clicked on "PLC Programming" cost element (CE-CTRL-02, €45,000)
4. Clicked "Edit" button
5. Modified budget from €45,000 to €55,000
6. Clicked "Save"

**Expected Result:**
- Cost element should be forked to BR-CO-2026-016 branch
- Original version on main branch should remain unchanged
- Changes should be isolated to change order branch

**Actual Result:**
❌ **CRITICAL BUG:** Cost element was updated on **main** branch, not the change order branch!

**Evidence:**
```sql
-- Before edit: Cost element on main branch
SELECT cost_element_id, branch FROM cost_elements 
WHERE cost_element_id = '0c77c4dd-30c0-46f2-a9f9-e5c03db50dcd';

-- After edit: NEW VERSION created on main (not BR-CO-2026-016)
valid_time: 2026-05-10 12:19:33 (main branch update)
```

**API Analysis:**
- Request: `PUT /api/v1/api/v1/cost-elements/0c77c4dd-30c0-46f2-a9f9-e5c03db50dcd`
- No branch parameter in request
- Response shows `"branch": "main"`

**Impact:**
- **HIGH** - Defeats the purpose of branch isolation
- Changes made while viewing change order branch are applied directly to main
- Breaks the EVCS lazy branching pattern
- Makes impact analysis unreliable

**Root Cause:**
The PUT request for cost element update does not include the current branch context. When editing from the change order branch view, the backend should:
1. Detect the change order context
2. Fork the entity to the change branch
3. Apply changes to the forked version
4. Leave main branch unchanged

---

### ✅ Test 4: Submit for Approval Workflow
**Status:** PASSED

**Steps:**
1. Navigated to Change Order CO-2026-016
2. Clicked "Workflow" tab
3. Clicked "Submit" button

**Result:**
- Status changed from "Draft" to "Submitted for Approval"
- Branch locked message displayed: "This change order is currently under review. The branch is locked and no modifications are allowed."
- Edit button disabled (expected)
- Impact analysis triggered
- Approver assigned: viewer@backcast.org (Viewer User)
- SLA status: pending
- Impact level calculated: LOW

**Database Verification:**
```sql
status | impact_level | assigned_approver_id | sla_status
------------------------+--------------+----------------------+------------
Submitted for Approval | LOW          | viewer@backcast.org | pending
```

**API Calls:**
- PUT `/api/v1/change-orders/35e2308d-d801-47a4-9e4b-7d66d8fe8d49/submit-for-approval` → 200 OK

**Available Transitions After Submission:**
- Under Review
- Approved
- Rejected

**Actions Available:**
- Put Under Review
- Approve
- Reject

---

## Issues Identified

### 🔴 Critical Issues

#### 1. Branch Isolation Failure in Draft Mode
**Severity:** CRITICAL  
**Location:** Cost element update API  
**Description:** When editing a cost element while viewing a change order branch, changes are applied to main branch instead of being forked to the change branch.

**Steps to Reproduce:**
1. Create change order CO-XXX
2. Switch to change branch BR-CO-XXX
3. Navigate to a cost element
4. Edit and save
5. Check database - change is on main, not BR-CO-XXX

**Expected Behavior:**
- Entity should be forked to change order branch
- Main branch should remain unchanged

**Actual Behavior:**
- Entity updated on main branch
- No version created on change order branch

**Impact:**
- Breaks EVCS core principle of branch isolation
- Makes impact analysis unreliable
- Potential data corruption in production

**Recommendation:**
- Investigate cost element update API endpoint
- Ensure branch context is passed from frontend to backend
- Implement lazy forking when editing from change order branch view
- Add integration tests for branch isolation

---

### 🟡 Medium Issues

#### 2. Schedule Baseline Not Found on Change Branch
**Severity:** MEDIUM  
**Description:** When viewing cost element on change branch, schedule baseline returns 404.

**Evidence:**
```
GET /api/v1/cost-elements/0c77c4dd-30c0-46f2-a9f9-e5c03db50dcd/schedule-baseline?branch=BR-CO-2026-016
Result: 404 Not Found
```

**Impact:**
- Affects EVM calculations on change branch
- May cause incomplete impact analysis

**Recommendation:**
- Ensure schedule baselines are forked to change branches during submission
- Or provide fallback to main branch baseline for calculations

---

### 🟢 Low Priority Observations

#### 3. Console Warnings
**Description:** Various antd deprecation warnings in console output.

**Evidence:**
```
Warning: [antd: Modal] `destroyOnClose` is deprecated. Please use `destroyOnHidden` instead.
```

**Impact:**
- Cosmetic only
- Does not affect functionality

**Recommendation:**
- Update antd version or replace deprecated API usage

---

## What Was NOT Tested

Due to time and scope limitations, the following were not tested:

1. **Approval/Rejection Workflow** - Would require switching to approver user
2. **Merge to Main Workflow** - Requires Approved status first
3. **Rejection and Resubmission** - Requires rejection workflow
4. **Conflict Detection and Resolution** - Requires concurrent edits
5. **SLA Tracking and Escalation** - Requires time passage simulation
6. **Impact Analysis Accuracy** - Requires verification of calculated metrics
7. **Multi-entity Changes** - Only tested single cost element modification
8. **WBE Creation/Deletion** - Only tested cost element modification
9. **Permission Checks** - Verified assigned approver but not enforcement
10. **Notification Delivery** - Did not verify email/push notifications

---

## Project Changes Performed

### Database Changes

**New Change Order Created:**
- Table: `change_orders`
- ID: 35e2308d-d801-47a4-9e4b-7d66d8fe8d49
- Code: CO-2026-016
- Status: Submitted for Approval

**Cost Element Modified (BUG - on main instead of change branch):**
- Table: `cost_elements`
- ID: 0c77c4dd-30c0-46f2-a9f9-e5c03db50dcd
- Code: CE-CTRL-02
- Budget changed: €45,000 → €55,000
- Branch: main (INCORRECT - should be BR-CO-2026-016)

**New Version Created:**
- New cost element version on main branch at 2026-05-10 12:19:33

### Test Artifacts

**Screenshots Captured:**
- home-page.png
- login-page.png  
- after-login.png
- current-page.png
- home-after-login.png

**Console Logs:**
- Located in `.playwright-mcp/console-*.log` files

---

## Recommendations

### Immediate Actions Required

1. **Fix Branch Isolation Bug** (CRITICAL)
   - Priority: P0
   - Assign to: Backend Team
   - Estimated effort: 2-3 days
   - Investigation: Check cost element update endpoint, ensure branch context propagation

2. **Schedule Baseline Fallback**
   - Priority: P1
   - Assign to: Backend Team
   - Estimated effort: 1 day

### Future Improvements

1. **Add Integration Tests for Branch Isolation**
   - Test all CRUD operations on change branches
   - Verify entities are forked correctly
   - Test merge operations

2. **Improve User Feedback**
   - Show clear indication when editing on change branch
   - Add visual cues showing which branch will be modified
   - Display warnings before applying changes to main

3. **Permission Testing**
   - Create test users for each role
   - Test approval authority enforcement
   - Verify SLA escalation

4. **Comprehensive E2E Test Suite**
   - Cover full lifecycle: Draft → Submit → Approve → Merge
   - Test rejection and resubmission
   - Test conflict scenarios

---

## Conclusion

The change order system demonstrates good basic functionality with successful creation, branch switching, and submission workflows. However, a **critical branch isolation bug** was discovered that undermines the core EVCS principle of isolated change development.

**Recommendation:** Do not deploy to production until the branch isolation issue is resolved. This is a fundamental data integrity concern that could lead to unintended changes to production project data.

**Test Coverage Achieved:** ~40% of full change order lifecycle (due to bug halting further testing)

**Next Steps:**
1. Fix branch isolation bug
2. Re-test CRUD operations on change branch
3. Complete approval/rejection workflow testing
4. Perform full merge-to-main testing
5. Generate final report with all tests passed

---

**Report Generated:** 2026-05-10 12:22 UTC  
**Test Duration:** ~20 minutes  
**Browser:** Playwright Headless Chrome  
**Backend Server:** Uvicorn on port 8020  
**Frontend Server:** Vite dev server on port 5173
