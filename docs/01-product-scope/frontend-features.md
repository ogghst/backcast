# Frontend Features

**Last Updated:** 2026-03-02
**Status:** Active

This document describes the user-facing features implemented in the Backcast EVS frontend.

---

## 1. Project Management

### 1.1 Project List
- **Location:** `/projects`
- **Features:**
  - Card-based project overview with key metrics
  - Filter by status (active, completed, on-hold)
  - Search by name or code
  - Create new project modal
- **Related:** [Project Requirements](./functional-requirements.md#5-project-management)

### 1.2 Project Detail
- **Location:** `/projects/{id}`
- **Features:**
  - Project information summary
  - WBE hierarchy visualization
  - EVM metrics dashboard
  - Change order list
  - Quality events

---

## 2. WBE Management

### 2.1 WBE Hierarchy Table
- **Location:** `WBETable.tsx`
- **Features:**
  - Hierarchical tree view with indentation
  - Expandable/collapsible rows
  - Inline metrics (budget, revenue, EVM indices)
  - Branch comparison indicators
  - Click to navigate to detail

### 2.2 WBE Modal
- **Location:** `WBEModal.tsx`
- **Features:**
  - Create/Edit WBE
  - **Note:** Budget allocation is computed from cost elements (read-only)
  - Revenue allocation (visible in change order branches)
  - Parent WBE selection
  - Level auto-inference from parent
- **See Also:** [WBE User Guide](../05-user-guide/evcs-wbe-user-guide.md)

### 2.3 WBE Summary Card
- **Location:** `WBESummaryCard.tsx`
- **Features:**
  - Key WBE information at a glance
  - Computed budget display
  - Revenue allocation
  - Cost element count

---

## 3. Cost Element Management

### 3.1 Cost Element List
- **Location:** Within WBE detail view
- **Features:**
  - Table with budget, actuals, progress
  - Filter by type, status
  - Sort by budget amount, variance

### 3.2 Cost Element Modal
- **Location:** `CostElementModal.tsx`
- **Features:**
  - Create/Edit cost element
  - Budget amount entry (THIS is where budget lives)
  - Cost element type selection
  - Department assignment
  - Schedule baseline configuration

---

## 4. EVM Analysis

### 4.1 EVM Summary View
- **Location:** `EVMSummaryView.tsx`
- **Features:**
  - Cost metrics (CPI, CV, EAC, VAC)
  - Schedule metrics (SPI, SV)
  - Performance metrics (CPI/SPI trends)
  - Forecast metrics (EAC, ETC, TCPI)
- **See Also:** [EVM Requirements](./evm-requirements.md)

### 4.2 EVM Analyzer Modal
- **Location:** `EVMAnalyzerModal.tsx`
- **Features:**
  - Detailed metric breakdown
  - Time-series visualization
  - Branch comparison
  - Export capabilities

### 4.3 EVM Time Series Chart
- **Location:** `EVMTimeSeriesChart.tsx`
- **Features:**
  - PV/EV/AC progression over time
  - Granularity selector (daily/weekly/monthly)
  - Time-travel slider
  - Zoom and pan

---

## 5. Time Machine

### 5.1 Time Machine Context
- **Location:** `TimeMachineContext.tsx`
- **Features:**
  - Global `as_of` date selection
  - Branch switching
  - Context preservation across navigation
- **See Also:** [Temporal Query Reference](../02-architecture/cross-cutting/temporal-query-reference.md)

### 5.2 Time Machine UI
- **Features:**
  - Date picker for historical queries
  - Quick navigation (today, yesterday, last week)
  - Branch selector dropdown
  - Visual indicator of current context

---

## 6. Change Order Management

### 6.1 Change Order List
- **Location:** `/projects/{id}/change-orders`
- **Features:**
  - Status indicators (Draft, Submitted, Approved, etc.)
  - Impact level badges
  - Quick actions (Submit, Approve, Reject)
- **See Also:** [Change Management User Stories](./change-management-user-stories.md)

### 6.2 Change Order Modal
- **Location:** `ChangeOrderModal.tsx`
- **Features:**
  - Create new change order
  - Automatic branch creation
  - Initial impact assessment

### 6.3 Impact Analysis View
- **Features:**
  - Side-by-side comparison (main vs branch)
  - Hierarchical diff visualization
  - KPI comparison cards
  - Timeline visualization

### 6.4 Workflow Buttons
- **Location:** `WorkflowButtons.tsx`
- **Features:**
  - Context-aware action buttons
  - Submit/Approve/Reject/Merge/Archive
  - Confirmation modals
  - Comment support

---

## 7. Quality Events

### 7.1 Quality Event List
- **Features:**
  - Filter by type, severity, status
  - Cost impact summary
  - Root cause tracking

### 7.2 Quality Event Modal
- **Features:**
  - Create/Edit quality events
  - Cost impact entry
  - Root cause classification
  - Resolution tracking

---

## 8. User & Admin

### 8.1 User Management
- **Location:** `/admin/users`
- **Features:**
  - User list with roles
  - Create/Edit users
  - Role assignment
  - History drawer

### 8.2 Department Management
- **Location:** `/admin/departments`
- **Features:**
  - Department hierarchy
  - Manager assignment
  - Cost element type mapping

---

## 9. Common Components

### 9.1 Hierarchical Diff View
- **Location:** `HierarchicalDiffView.tsx`
- **Features:**
  - Tree structure with change indicators
  - Created/Updated/Deleted markers
  - Expandable nodes
  - Summary statistics

### 9.2 KPICards
- **Location:** `KPICards.tsx`
- **Features:**
  - Financial metrics display
  - EAC/VAC cards
  - Schedule/performance metrics
  - Target indicators

### 9.3 Approval Info
- **Location:** `ApprovalInfo.tsx`
- **Features:**
  - Impact level badge
  - Approver information
  - SLA status
  - Authority level indicator

---

## Related Documentation

- [EVM Requirements](./evm-requirements.md) - Formulas and metrics
- [Change Management User Stories](./change-management-user-stories.md) - Change order workflows
- [WBE User Guide](../05-user-guide/evcs-wbe-user-guide.md) - WBE operations
- [Frontend Architecture](../02-architecture/frontend/README.md) - Technical implementation
