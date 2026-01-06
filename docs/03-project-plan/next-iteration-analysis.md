# Next Iteration Analysis

## 1. Current State Assessment

**Recently Completed:**

- **Technical Foundation:** Backend refactoring (generic `TemporalService`), test suite stabilization (>80% coverage), and full linting/type-safety compliance (Ruff/MyPy strict).
- **Frontend Core:** Authentication/Authorization (RBAC), User & Department Management, and initial Project/WBE list views.
- **Project/WBE Structure:** Basic "Do" phase implementation of Project and WBE lists in frontend (Jan 5).

**Working Well:**

- **Quality Standards:** The strict linting and testing regime is effectively catching issues early.
- **Architecture:** The Bitemporal/EVCS Core pattern is established and seems robust (tested in User/Dept/Project domains).
- **Velocity:** Rapid iteration on frontend features (Auth -> Users -> Projects).

**Pain Points:**

- **Depth vs. Breadth:** We have the "top" of the hierarchy (Projects/WBEs) but lack the "leaves" (Cost Elements) where the actual data lives.
- **Feature Gap:** The "Change Order" capability (core value prop) is technically possible in backend but not exposed to users.

## 2. Gap Analysis

- **Product Gaps:**
  - **Cost Elements:** Users cannot yet define budgets or track costs at the departmental level (Epic 4).
  - **Financials:** No budget definition, generic cost registration, or forecasting (Epic 5).
  - **Change Management:** No UI for creating/merging branches or change orders (Epic 6).
- **Technical Gaps:**
  - **Backend:** Cost Element and Budget entities likely need implementation/refinement to match the generic patterns.
  - **Frontend:** Complex forms for hierarchical data (Budgeting) are missing.

## 3. Prioritization Factors

| Option                           | Business Value                                                  | Technical Urgency                                            | Dependencies        | Risk                             | Effort |
| :------------------------------- | :-------------------------------------------------------------- | :----------------------------------------------------------- | :------------------ | :------------------------------- | :----- |
| **A. Cost Elements & Budgeting** | **High**. Completes the data structure to make projects "real". | Medium. Patterns exist, just need implementation.            | Project/WBE (Done). | Low. Standard CRUD + Versioning. | Medium |
| **B. Change Order System**       | **Critical**. Core differentiator.                              | High. Needed to validate the "Branching" architecture fully. | Project/WBE (Done). | High. Complex state management.  | High   |
| **C. Financial Data (Actuals)**  | Medium. Requires Budgets first.                                 | Low.                                                         | B. Cost Elements.   | Low.                             | Medium |

## 4. Recommended Next Iteration

### Option 1: Cost Elements & Budgeting (Vertical Slice Completion)

**Goal:** Implement the `CostElement` entity and basic Budgeting capabilities to complete the Project -> WBE -> Cost Element hierarchy.

- **Expected Outcomes:** Users can define the full structure of a project and assign budgets to departments.
- **Why Now:** Builds directly on the recent Project/WBE work. Essential prerequisite for Financial Data (Epic 5).
- **Prerequisites:** Project & WBE Management (mostly done).

### Option 2: Change Order Foundation (The "Killer Feature")

**Goal:** Implement the Change Order lifecycle (Branch Creation, Editing in Branch, Merging).

- **Expected Outcomes:** A UI flow to create a "Change Order" (Branch), modify a Project/WBE in that branch, and view it isolated from Main.
- **Why Now:** We have the backend foundation. delaying this risks discovering architectural issues with branching late in the process.
- **Prerequisites:** Backend Branching Logic (in place but needs verifying/exposing).

## 5. Questions for Human Decision

1.  **Depth vs. Risk:** Do we want to finish the static data hierarchy (Option 1) to "setup" projects fully, or tackle the high-risk/high-reward comparison engine (Option 2) to prove the branching concept?
2.  **Resource Allocation:** Option 2 requires significant frontend logic for "Context Switching" (Branch Selection). Is the frontend foundation ready for this complexity?
