import { Steps } from "antd";
import { CheckCircleOutlined, LoadingOutlined } from "@ant-design/icons";
import { WORKFLOW_STEPS, getStepIndex } from "./WorkflowConstants";

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
export function WorkflowStepper({
  status,
  processingStatus,
}: WorkflowStepperProps) {
  const currentIndex = getStepIndex(status);

  const items = WORKFLOW_STEPS.map((step, index) => {
    const isCompleted = index < currentIndex;
    const isCurrent = index === currentIndex;
    const isProcessing =
      processingStatus && step.key === processingStatus.toLowerCase();

    let icon: React.ReactNode;
    if (isCompleted) {
      icon = <CheckCircleOutlined />;
    } else if (isProcessing) {
      icon = <LoadingOutlined />;
    }

    return {
      title: step.title,
      subTitle: step.description,
      status: (isCompleted ? "finish" : isCurrent ? "process" : "wait") as
        | "finish"
        | "process"
        | "wait",
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
