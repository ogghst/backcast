# Change Order Management — Business User Guide

This guide explains how to create, review, approve, and implement Change Orders in Backcast. It is written for Project Managers, Controllers, Department Heads, Directors, and anyone who participates in the change control process.

---

## 1. What Are Change Orders?

Change Orders (COs) manage modifications to a project's budget, work breakdown elements (WBEs), and cost elements. Every change order operates in an **isolated branch** — a private copy of the project where you can experiment freely without affecting the live budget. Changes only reach the main project when the order is approved and merged.

**Key principle:** No one sees your changes until you submit for approval. The main project data is never at risk.

### When to Use a Change Order

- Adding or removing work packages from the project scope
- Revising budgets on existing cost elements
- Responding to client-requested scope changes
- Correcting estimation errors that affect financial baselines
- Any modification that requires formal sign-off before implementation

---

## 2. Getting There

Navigate to **Projects → select your project → Change Orders** in the sidebar.

The page opens with two tabs:

| Tab | Purpose |
|-----|---------|
| **List View** | All change orders for this project in a searchable, filterable table |
| **Analytics** | Dashboard with KPIs, charts, and approval workload breakdowns |

---

## 3. Roles and Permissions

Your role determines what you can do with change orders. The table below shows the capabilities for each role.

### What Each Role Can Do

| Action | Viewer | Editor / PM | Department Head | Director | Admin |
|--------|--------|-------------|-----------------|----------|-------|
| View change orders | Yes | Yes | Yes | Yes | Yes |
| View impact analysis | Yes | Yes | Yes | Yes | Yes |
| Create a change order | — | Yes | — | — | Yes |
| Edit a Draft/Rejected CO | — | Yes | — | — | Yes |
| Delete a Draft CO | — | Yes | — | — | Yes |
| Submit for approval | — | Yes | — | — | Yes |
| Approve/Reject (Low impact) | — | Yes | Yes | Yes | Yes |
| Approve/Reject (Medium impact) | — | — | Yes | Yes | Yes |
| Approve/Reject (High impact) | — | — | — | Yes | Yes |
| Approve/Reject (Critical impact) | — | — | — | — | Yes |
| Merge to main | — | Yes | — | — | Yes |
| Recover stuck workflows | — | — | — | — | Yes |

### Approval Authority by Impact Level

The system automatically calculates the financial impact of your changes and routes approval to the right authority level. The values below show the **default configuration** — your system administrator may have customized these for your organization or project.

| Impact Level | Financial Threshold | Required Approver | SLA Deadline |
|--------------|---------------------|-------------------|--------------|
| Low | Under €10,000 | Project Manager | 2 business days |
| Medium | €10,000 — €50,000 | Department Head | 5 business days |
| High | €50,000 — €100,000 | Director | 10 business days |
| Critical | Over €100,000 | Executive Committee | 15 business days |

The impact level is calculated using a weighted score that considers budget change percentage, schedule impact, revenue impact, and earned value degradation. The weights and score boundaries are also configurable by administrators.

---

## 4. Change Order Lifecycle

Every change order follows the same six-state workflow. Below is the complete lifecycle with what happens at each stage.

```
Draft → Submitted for Approval → Under Review → Approved → Implemented
                                   ↘ Rejected → (resubmit as Draft)
```

### State Overview

| State | What It Means | Can You Edit? | Branch Status |
|-------|---------------|---------------|---------------|
| **Draft** | You are preparing the change. Work in progress. | Yes | Unlocked |
| **Submitted for Approval** | Sent for review. Awaiting a decision. | No | Locked |
| **Under Review** | An approver is actively reviewing the change. | No | Locked |
| **Approved** | Change accepted. Ready for implementation. | No | Locked |
| **Rejected** | Change denied. You can revise and resubmit. | Yes | Unlocked |
| **Implemented** | Change merged into the main project. Final state. | No | Archived |

---

## 5. Step-by-Step Workflows

### 5.1 Creating a Change Order

1. Go to the Change Orders list and click **New Change Order**.
2. Fill in the form:
   - **Code** — Auto-generated in `CO-YYYY-NNN` format (you can override).
   - **Title** — Short, descriptive name (e.g., "Add emergency stop feature").
   - **Description** — What the change entails.
   - **Justification** — Why this change is needed.
   - **Effective Date** — When the change should take effect.
3. Click **Create**. The system creates the change order on the main branch and prepares a dedicated branch (named `BR-{code}`).

At this point, the change order is in **Draft** status. No changes to the project have been made yet.

### 5.2 Working on a Change Order (Draft)

1. Open the change order from the list.
2. **Switch to the change branch** using the branch selector in the header (the header turns amber/orange to indicate you are on a change branch).
3. Modify WBEs, cost elements, or budgets as needed. All changes are isolated to this branch — the main project is unaffected.
4. You can freely edit, add, or remove items. Nothing is permanent until submission.

**Tip:** Use the **Impact Analysis** tab at any time during drafting to see a live preview of how your changes affect the project finances.

### 5.3 Reviewing Impact Analysis

Before submitting, review the impact dashboard. It provides:

- **KPI Cards** — Side-by-side comparison of current vs. proposed budget, gross margin, EAC, and performance indices (CPI, SPI).
- **Waterfall Chart** — Visual bridge from the current budget to the proposed budget, showing each contributing change.
- **S-Curve Comparison** — Dual-line chart comparing cumulative cost curves (main vs. proposed), with a time slider to inspect variance at any date.
- **Entity Impact Grid** — Detailed table of every modified, added, or removed WBE and cost element, color-coded by direction (red = increase, green = decrease).

You can view impact in two modes:

| Mode | What It Shows | When to Use |
|------|---------------|-------------|
| **Merged View** (default) | Final state after merging changes into main | Understanding the end result |
| **Changes Only** | Only the items you modified | Reviewing what specifically changed |

### 5.4 Submitting for Approval

1. Open the Draft change order.
2. Click **Submit for Approval**.
3. The system automatically:
   - Runs impact analysis (comparing isolation branch against main).
   - Calculates the financial impact level (Low/Medium/High/Critical).
   - Assigns the appropriate approver based on impact level.
   - Starts the SLA countdown timer.
   - Snapshots the current workflow configuration for audit purposes.
   - Forks all project entities to the isolation branch for complete data isolation.
   - **Locks the branch** — no further edits are possible while under review.
4. Add an optional comment for the reviewer.

**Important:** Once submitted, you cannot modify the change order. If changes are needed, the approver must reject it first, which unlocks the branch.

### 5.5 Approving or Rejecting a Change Order

If you are assigned as an approver:

1. Go to **Change Orders** and look for items with "Submitted for Approval" status, or check **Pending Approvals**.
2. Open the change order to review the details and impact analysis.
3. The approval section shows:
   - Your authority level and whether you can approve this change.
   - The SLA countdown (days remaining).
   - The assigned approver information.
4. Choose an action:
   - **Approve** — Accept the change. Add an optional comment for the audit trail.
   - **Reject** — Deny the change. A comment is required explaining the reason. The branch unlocks and the creator can revise and resubmit.

**Authority checks:** The system verifies that your role has sufficient authority for the change's impact level. If you lack authority, the approve/reject buttons are disabled with a tooltip explaining why.

### 5.6 Implementing an Approved Change Order

Once a change order is approved:

1. Open the approved change order.
2. Click **Merge to Main**.
3. The system:
   - Checks for merge conflicts (same entity modified on both the change branch and main).
   - Merges all modified, added, and removed entities into the main branch.
   - Updates the change order status to **Implemented**.
   - Archives the change branch.

**If merge conflicts are detected:** The merge is blocked. An admin can help resolve conflicts. Conflicts occur when the same entity was modified on both the change branch and the main branch independently.

### 5.7 Revising a Rejected Change Order

1. Open the rejected change order. The branch is now **unlocked**.
2. Switch to the change branch.
3. Make your revisions.
4. Click **Submit for Approval** again when ready.

### 5.8 Archiving

For change orders in **Implemented** or **Rejected** status that are no longer needed:

1. Open the change order.
2. Click **Archive**. This soft-deletes the associated branch for cleanup.

---

## 6. Status Visual Reference

The UI uses consistent color coding for change order states so you can identify status at a glance:

| Status | Color | Icon |
|--------|-------|------|
| Draft | Gray (default) | Clock |
| Submitted for Approval | Blue | Spinning sync |
| Under Review | Cyan | Spinning sync |
| Approved | Green | Checkmark circle |
| Rejected | Red | X circle |
| Implemented | Purple | Merge cells |

**Impact level badges:**

| Level | Color |
|-------|-------|
| Low | Green |
| Medium | Orange |
| High | Red |
| Critical | Purple |

---

## 7. Analytics Dashboard

Switch to the **Analytics** tab on the Change Orders page for project-wide insights:

- **KPI Cards** — Total change orders, total cost exposure, pending value, approved value.
- **Status Distribution** — Pie chart of change orders by status.
- **Impact Level Distribution** — Chart showing the breakdown by impact level.
- **Cost Trend** — Financial trend of changes over time.
- **Approval Workload Table** — Shows how many approvals are assigned to each approver.
- **Aging Items** — Change orders approaching or past their SLA deadline.
- **Average Approval Time** — Historical metric for how long approvals typically take.

---

## 8. SLA Tracking

When a change order is submitted for approval, an SLA timer starts based on the impact level:

| SLA Status | Meaning |
|------------|---------|
| **Pending** | More than half the SLA time remains |
| **Approaching** | Less than half the SLA time remains |
| **Escalated** | Manually escalated for urgent attention |
| **Overdue** | The SLA deadline has passed |

The SLA countdown is visible on the change order detail page in the approval section. Overdue items are highlighted in the analytics dashboard.

---

## 9. AI-Assisted Features

Backcast includes AI tools to speed up change order creation:

- **Draft Generation** — Describe the change in natural language and the AI generates a complete change order draft with suggested title, description, justification, and impact assessment.
- **Impact Summaries** — Plain-language descriptions of what the change means for the project.
- **Justification Assistance** — AI-generated justification text based on the impact analysis.

These features are available from the change order creation page and within the AI chat interface.

---

## 10. Common Scenarios

### "I need to increase the budget on three cost elements"

1. Create a new change order with a descriptive title.
2. Switch to the change branch.
3. Navigate to the relevant WBEs and update the three cost elements.
4. Check the Impact Analysis tab to see the total budget increase.
5. Submit for approval when ready.

### "My change order was rejected — now what?"

The branch is unlocked and you can edit again. Review the rejection comment from the approver, make adjustments, and resubmit. All previous versions are preserved in the history.

### "I need to see what changed without affecting the project"

Create a change order and work on the branch. The Impact Analysis dashboard updates in real time as you make changes. You can delete the draft at any time without any effect on the main project.

### "I'm an approver — how do I find change orders that need my attention?"

Check the **Pending Approvals** section or filter the change order list by "Submitted for Approval" status. The analytics dashboard also shows aging items that need urgent attention.

### "A change order is stuck and won't progress"

Contact your system administrator. They have access to the **Recover Workflow** tool that can reset stuck change orders.

---

## 11. Tips and Best Practices

- **Check impact early and often** — Use the Impact Analysis tab while drafting, not just before submission. This avoids surprises during review.
- **Write clear justifications** — Approvers rely on the description and justification to make decisions. Include the business reason, not just what changed.
- **Use the Merged View for stakeholder communication** — It shows the final result, which is what stakeholders care about.
- **Monitor SLA deadlines** — Overdue approvals are visible to administrators and tracked in the analytics dashboard.
- **Keep change orders focused** — One change order per logical change. Combining unrelated changes makes review harder and increases the chance of rejection.
- **Review rejection comments carefully** — They contain the approver's reasoning. Address the specific concerns before resubmitting.

---

## 12. Configurable Workflow Settings

Administrators can customize the change order workflow parameters to match organizational policies. This replaces the previous system-wide hardcoded defaults.

### What Can Be Configured

| Setting | Description | Default |
|---------|-------------|---------|
| **Impact Level Thresholds** | Financial amount boundaries (LOW/MEDIUM/HIGH/CRITICAL) | €10K / €50K / €100K / unlimited |
| **Score Boundaries** | Impact score ranges for each level | 0-10 / 10-30 / 30-50 / 50+ |
| **Impact Weights** | Relative weight of budget, schedule, revenue, EVM factors | 0.4 / 0.3 / 0.2 / 0.1 |
| **Approval Rules** | Which roles can approve at each impact level | PM → LOW, Dept Head → HIGH, Director → HIGH, Admin → CRITICAL |
| **SLA Deadlines** | Business day limits per impact level | 2 / 5 / 10 / 15 days |

### Global vs. Project-Level Configuration

- **Global defaults** apply to all projects without a project-specific override
- **Project overrides** allow per-project customization (e.g., stricter thresholds for high-risk projects)
- When a project override is removed, it reverts to the global defaults

### Accessing Configuration

| Page | URL | Permission Required |
|------|-----|---------------------|
| **Global Config** | `/admin/change-order-config` | `change-order-workflow-config-manage` |
| **Project Override** | Project → Admin → Change Order Workflow | `change-order-workflow-config-override` |

### How It Works

1. Admin navigates to the **Global Config** page under Admin settings
2. Edits parameters in the tabbed form (Impact Levels, Approval Rules, SLA Rules, Weights & Scores)
3. Saves with a confirmation dialog — changes take effect immediately on new change orders
4. For project-specific needs, project managers can override settings from the project admin page
5. Configuration is **snapshotted** at submission time, so historical change orders retain the values that were active when they were submitted

> **Note:** Changes to configuration do not affect change orders that are already in progress. Only new submissions use the updated values.
