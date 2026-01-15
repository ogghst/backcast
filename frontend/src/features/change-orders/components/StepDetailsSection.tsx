import { Alert, Empty, Space, Tag, Typography } from "antd";
import { InfoCircleOutlined } from "@ant-design/icons";

const { Text, Paragraph } = Typography;

interface StepDetailsSectionProps {
  /** Current workflow status */
  status: string;
  /** Available transitions from backend */
  availableTransitions?: string[] | null;
  /** Whether the branch is locked */
  branchLocked?: boolean | null;
}

/**
 * StepDetailsSection - Dynamic content based on workflow status.
 *
 * Displays contextual information and guidance for the current
 * workflow step, including what actions are available.
 */
export function StepDetailsSection({
  status,
  availableTransitions,
  branchLocked,
}: StepDetailsSectionProps) {
  // Get content for current status
  const getStatusContent = () => {
    switch (status) {
      case "Draft":
        return {
          title: "Draft Phase",
          description: "Your change order is in draft mode. You can modify all details.",
          actionHint: "Submit for review when ready.",
          availableActions: availableTransitions || [],
        };

      case "Submitted for Approval":
        return {
          title: "Submitted for Review",
          description: "Change order has been submitted and is awaiting review.",
          actionHint: branchLocked
            ? "Branch is locked. Wait for a reviewer to process your request."
            : "Awaiting assignment to a reviewer.",
          availableActions: [],
          warning: branchLocked
            ? "Branch is locked - no modifications allowed while under review."
            : undefined,
        };

      case "Under Review":
        return {
          title: "Under Review",
          description: "A reviewer is evaluating your change order.",
          actionHint: branchLocked
            ? "Branch is locked. Wait for the review to complete."
            : "Review in progress.",
          availableActions: availableTransitions || [],
          warning: branchLocked
            ? "Branch is locked - no modifications allowed while under review."
            : undefined,
        };

      case "Approved":
        return {
          title: "Approved",
          description: "Change order has been approved and is ready to merge.",
          actionHint: "Merge to main branch to implement the changes.",
          availableActions: availableTransitions || [],
          info: "After merging, the status will automatically change to Implemented.",
        };

      case "Implemented":
        return {
          title: "Implemented",
          description: "Change order has been merged to main branch.",
          actionHint: "The changes are now live.",
          availableActions: [],
          success: "All changes have been successfully applied.",
        };

      case "Rejected":
        return {
          title: "Rejected",
          description: "Change order was rejected.",
          actionHint: "You can modify the change order and resubmit.",
          availableActions: availableTransitions || [],
          warning: "Branch has been unlocked. You may make changes and resubmit.",
        };

      default:
        return {
          title: status,
          description: "Unknown status",
          actionHint: "Contact support if you believe this is an error.",
          availableActions: [],
        };
    }
  };

  const content = getStatusContent();

  return (
    <Space direction="vertical" size="middle" style={{ width: "100%" }}>
      {/* Status banner */}
      {content.success && (
        <Alert
          type="success"
          showIcon
          message={content.success}
        />
      )}

      {content.warning && (
        <Alert
          type="warning"
          showIcon
          message={content.warning}
        />
      )}

      {/* Title and description */}
      <div>
        <Text strong style={{ fontSize: 16 }}>
          {content.title}
        </Text>
        <Paragraph style={{ marginBottom: 8, marginTop: 8 }}>
          {content.description}
        </Paragraph>
        <Paragraph type="secondary" style={{ marginBottom: 0 }}>
          <InfoCircleOutlined style={{ marginRight: 4 }} />
          {content.actionHint}
        </Paragraph>
      </div>

      {/* Info message (if any) */}
      {content.info && (
        <Alert
          type="info"
          showIcon
          message={content.info}
          style={{ fontSize: "12px" }}
        />
      )}

      {/* Available actions */}
      {content.availableActions.length > 0 && (
        <div>
          <Text strong style={{ fontSize: 12 }}>
            Available Actions:
          </Text>
          <Space wrap style={{ marginTop: 8 }}>
            {content.availableActions.map((action) => (
              <Tag key={action}>{action}</Tag>
            ))}
          </Space>
        </div>
      )}

      {/* Empty state for no actions */}
      {content.availableActions.length === 0 && status !== "Implemented" && (
        <Empty
          image={Empty.PRESENTED_IMAGE_SIMPLE}
          description="No actions available at this time"
          style={{ margin: "8px 0" }}
        />
      )}
    </Space>
  );
}
