export const WORKFLOW_STEPS = [
  { key: "draft", title: "Draft", description: "Initial state" },
  { key: "submitted", title: "Submitted", description: "Under Review" },
  { key: "under_review", title: "In Review", description: "Being evaluated" },
  { key: "approved", title: "Approved", description: "Ready to merge" },
  { key: "implemented", title: "Implemented", description: "Merged to main" },
] as const;

export type WorkflowStepKey = (typeof WORKFLOW_STEPS)[number]["key"];

/**
 * Get the current step index based on status.
 */
export function getStepIndex(status: string): number {
  const statusToKey: Record<string, WorkflowStepKey> = {
    Draft: "draft",
    "Submitted for Approval": "submitted",
    "Under Review": "under_review",
    Approved: "approved",
    Implemented: "implemented",
    Rejected: "draft", // Rejected returns to Draft
  };
  const key = statusToKey[status] || "draft";
  return WORKFLOW_STEPS.findIndex((step) => step.key === key);
}
