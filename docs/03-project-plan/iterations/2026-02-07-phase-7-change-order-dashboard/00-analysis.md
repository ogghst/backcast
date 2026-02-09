# Analysis: Phase 7 - Change Order Dashboard & Reporting

## Purpose

Design a comprehensive analytics and reporting dashboard for Change Orders to provide project-level visibility into cost, schedule, and risk impacts, as well as approval workflow bottlenecks.

**Output**: An approved approach for removing visibility gaps in the Change Order process.

---

## Phase 1: Requirements Clarification

### 1.1 User Intent

The user (Project Managers, Controls Team, Executives) needs to see the "big picture" of how Change Orders are affecting the project over time. While Phase 6 provided detailed impact for *single* change orders, Phase 7 focuses on **aggregated trends and workflow performance**.

### 1.2 Functional Requirements

1. **Impact Analytics Dashboard**:
    * Total potential cost/schedule exposure (Approved + Pending).
    * Change Order count by status and priority.
    * Cumulative cost impact over time (Trend).
2. **Approval Workload Metrics**:
    * Count of COs pending approval by department/approver.
    * Average time-to-approval.
3. **Status Reporting**:
    * List of "Stuck" or "Aging" change orders.
    * High-impact COs requiring attention.

### 1.3 Constraints

* **Tech Stack**: Frontend must use **Ant Design Charts** (consistent with existing `WaterfallChart`).
* **Performance**: Aggregations must be efficient; considering potential heavy queries on the temporal `change_orders` table.

---

## Phase 2: Context Discovery

### 2.1 Documentation & Codebase Review

* **Existing Dashboard**: `ImpactAnalysisDashboard.tsx` exists for *individual* CO context.
* **Chart Library**: `frontend/src/features/change-orders/components/WaterfallChart.tsx` confirms usage of `@ant-design/charts`.
* **Backend Support**: Currently, `ChangeOrderService` focuses on CRUD and single-entity transitions. We lack aggregated reporting endpoints.
* **Data Model**: Use `change_orders` table. Key fields: `status`, `impact_score`, `impact_level`, `submit_date`, `approval_date` (need to check if these dates exist or are derived from history).

---

## Phase 3: Solution Design

### Option 1: Embedded "Analytics" Tab in Change Order List (Recommended)

Add an "Analytics" tab to the existing `/projects/:id/change-orders` page.

#### 1. Architecture

* **Frontend**: New `ChangeOrderAnalytics` component using `@ant-design/charts`.
* **Backend**: New `ChangeOrderReportingService` and specialized endpoints (e.g., `/projects/:id/stats/change-orders`).
* **State**: React Query for fetching aggregated stats.

#### 2. UX Design

* **Layout**:
  * **Top Cards**: Total Count, Total Value, Avg Approval Time.
  * **Row 1**: Bar chart (COs by Status), Pie chart (Impact Level distribution).
  * **Row 2**: Line chart (Cumulative Cost Impact over time).
  * **Row 3**: "Aging Items" list (COs in 'SUBMITTED' > 7 days).
* **Navigation**: Toggle between "List View" and "Analytics View".

#### 3. Technical Implementation

* **New Service**: `backend/app/services/reporting_service.py`.
* **New API**: `backend/app/api/routes/reporting.py`.
* **Aggregations**: Use SQLAlchemy `func.count`, `func.sum`, `func.avg` with `group_by`.

#### 4. Trade-offs

* **Pros**: Contextual (stays in CO section), reuses existing layout, low friction.
* **Cons**: Might clutter the List view if not separated well.
* **Complexity**: Medium.

---

### Option 2: Dedicated "Project Dashboard" Module

Create a completely new top-level navigation item "Dashboard" that aggregates *all* project controls (EVM + COs + Schedule).

#### 1. Architecture

* **Frontend**: New route `/projects/:id/dashboard`.
* **Backend**: Aggregated "Project Health" endpoints.

#### 2. Trade-offs

* **Pros**: Centralized view for executives.
* **Cons**: Scope creep (combines EVM and COs prematurely), might duplicate data shown in specific modules.
* **Complexity**: High (requires redesigning navigation and consolidating disparate data sources).

---

### Option 3: External Reporting Integration (BI Tool)

Expose an OData or simple JSON export endpoint for PowerBI/Tableau.

#### 1. Architecture

* **Backend**: Read-only endpoints optimized for data export.

#### 2. Trade-offs

* **Pros**: Infinite customization in BI tools.
* **Cons**: Bad UX for day-to-day users (leaves app), authentication complexity.
* **Complexity**: Low (for us), High (for user setup).

---

## Phase 4: Recommendation

**I recommend Option 1 (Embedded Analytics Tab)**.

### Rationale

1. **User Focus**: Keeps the analytics close to the action (the Change Order list).
2. **Consistency**: Matches the pattern used in "EVM Analyzer" (Tabs for different views).
3. **Feasibility**: Leverages existing `@ant-design/charts` and fits within the estimated 18 points.
4. **Extensibility**: Can be easily moved to a master dashboard later if needed.

### Plan Summary

1. **Backend**: Create `ReportingService` with methods:
    * `get_change_order_stats(project_id)`
    * `get_change_order_trend(project_id)`
    * `get_approval_bottlenecks(project_id)`
2. **Frontend**: Create `ChangeOrderAnalytics` component.
3. **UI**: Add Tab switching to `ChangeOrderList.tsx`.

### Questions for Decision

* Do we have strict requirements for "historical snapshot" reporting (e.g., "What was the stats on Jan 1st?"), or is "Current State" sufficient? *(Assumption: Current State + Trend of created date is sufficient for now).*
