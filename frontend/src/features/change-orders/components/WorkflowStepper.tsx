import { Steps } from "antd";
import { CheckCircleOutlined, LoadingOutlined } from "@ant-design/icons";

/**
 * The 5-step workflow for Change Orders.
 */
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

interface WorkflowStepperProps {
  status: string;
  /** Current status that is being processed (e.g., during a transition) */
  processingStatus?: string | null;
}

/**
 * WorkflowStepper - Visual progress indicator for the 5-step Change Order workflow.
 *
 * Shows the current state in the workflow with visual progress indication.
 * - Gray: Future steps
 * - Blue: Current step
 * - Green: Completed steps
 */
export function WorkflowStepper({ status, processingStatus }: WorkflowStepperProps) {
  const currentIndex = getStepIndex(status);

  const items = WORKFLOW_STEPS.map((step, index) => {
    const isCompleted = index < currentIndex;
    const isCurrent = index === currentIndex;
    const isProcessing = processingStatus && step.key === processingStatus.toLowerCase();

    let icon: React.ReactNode;
    if (isCompleted) {
      icon = <CheckCircleOutlined />;
    } else if (isProcessing) {
      icon = <LoadingOutlined />;
    }

    return {
      title: step.title,
      description: step.description,
      status: (isCompleted ? "finish" : isCurrent ? "process" : "wait") as "finish" | "process" | "wait",
      icon,
    };
  });

  return (
    <Steps
      current={currentIndex}
      items={items}
      size="small"
      style={{ marginBottom: 24 }}
    />
  );
}
