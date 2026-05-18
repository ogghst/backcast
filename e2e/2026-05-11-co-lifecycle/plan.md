# E2E Test Plan: Change Order Full Lifecycle

## Iteration: 2026-05-11-co-lifecycle
## Objective: Validate the complete change order lifecycle from creation through implementation, including role-based approval and branch isolation

---

## Prerequisites

- [x] Frontend running on `http://localhost:5173`
- [x] Backend running on `http://localhost:8020`
- [x] Test project: CO-E2E-ROBOT exists with WBEs
- [x] Test users available: admin, pm, dept.head, director, viewer

## Test Steps

### Step 1: Create Change Order (Draft)
- **Action**: Login as admin, navigate to Change Orders, create new CO
- **Expected UI**: Status = "Draft", Edit enabled, branch unlocked
- **Expected DB**: `change_orders.status = 'draft'`, `branch_locked = false`
- **API**: `POST /api/v1/change-orders` → 201

### Step 2: Submit for Approval
- **Action**: Open CO detail → Workflow tab → Submit
- **Expected UI**: Status = "Under Review", Edit disabled, branch locked warning
- **Expected DB**: `status = 'under_review'`, `branch_locked = true`, `impact_level = 'LOW'`, `assigned_approver_id` set, `sla_due_date` set
- **API**: `PUT /api/v1/change-orders/{id}/submit-for-approval` → 200

### Step 3: Verify Wrong User Cannot Approve
- **Action**: Stay as admin, attempt to approve
- **Expected UI/API**: 400 Bad Request with authorization error
- **Expected DB**: Status unchanged (`under_review`)

### Step 4: Approve as Correct User (PM)
- **Action**: Logout, login as pm@backcast.org, approve CO
- **Expected UI**: Status = "Approved", "Merge to Main" button visible
- **Expected DB**: `status = 'approved'`, audit log entry created
- **API**: `PUT /api/v1/change-orders/{id}/approve` → 200

### Step 5: Merge to Main
- **Action**: Click "Merge to Main" in Workflow tab
- **Expected UI**: Status = "Implemented", only "Archive" action available
- **Expected DB**: `status = 'implemented'`, branch status = 'archived'
- **API**: `POST /api/v1/change-orders/{id}/merge` → 200

### Step 6: Test Rejection Workflow
- **Action**: Find existing CO in "Under Review", click Reject
- **Expected UI**: Status = "Rejected", Edit re-enabled, Submit available
- **Expected DB**: `status = 'rejected'`, `branch_locked = false`
- **API**: `PUT /api/v1/change-orders/{id}/reject` → 200

### Step 7: Verify Viewer Cannot Create CO
- **Action**: Login as viewer@backcast.org, navigate to Change Orders
- **Expected UI**: "New Change Order" button disabled or hidden
