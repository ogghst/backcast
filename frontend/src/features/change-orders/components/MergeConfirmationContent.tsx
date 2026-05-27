import { Alert, List, Space, Typography } from "antd";
import { CheckCircleOutlined, InfoCircleOutlined } from "@ant-design/icons";

const { Text } = Typography;

interface MergeImpact {
  field: string;
  source_value: string | null;
  target_value: string | null;
}

interface MergeConfirmationContentProps {
  /** Source branch name */
  sourceBranch: string;
  /** Target branch name */
  targetBranch: string;
  /** Number of entities that will be modified */
  entityCount: number;
  /** Optional list of specific field changes */
  impactSummary?: MergeImpact[];
  /** Target status after merge */
  targetStatus: string;
}

/**
 * MergeConfirmationContent - Confirmation view for merge operation.
 *
 * Shows the impact summary of merging source branch into target branch.
 * Displays what will change and confirms the target status after merge.
 */
export function MergeConfirmationContent({
  sourceBranch,
  targetBranch,
  entityCount,
  impactSummary,
  targetStatus,
}: MergeConfirmationContentProps) {
  return (
    <Space orientation="vertical" style={{ width: "100%" }}>
      {/* Primary confirmation message */}
      <Alert
        type="info"
        showIcon
        icon={<InfoCircleOutlined />}
        title={
          <Space orientation="vertical" size={0}>
            <Text strong>Merge {sourceBranch} → {targetBranch}</Text>
            <Text type="secondary">
              After merge, the Change Order status will be: <Text strong>{targetStatus}</Text>
            </Text>
          </Space>
        }
      />

      {/* Impact summary */}
      <div>
        <Text strong>Impact Summary:</Text>
        <List
          size="small"
          dataSource={[
            {
              key: "source-branch",
              label: "Branch to merge",
              value: sourceBranch,
            },
            {
              key: "target-branch",
              label: "Target branch",
              value: targetBranch,
            },
            {
              key: "entity-count",
              label: "Entities to update",
              value: String(entityCount),
            },
            {
              key: "new-status",
              label: "New status",
              value: targetStatus,
            },
          ]}
          renderItem={(item) => (
            <List.Item>
              <Space>
                <CheckCircleOutlined style={{ color: "#52c41a" }} />
                <Text>{item.label}: <Text code>{item.value}</Text></Text>
              </Space>
            </List.Item>
          )}
        />
      </div>

      {/* Detailed field changes (if provided) */}
      {impactSummary && impactSummary.length > 0 && (
        <div>
          <Text strong>Field Changes:</Text>
          <List
            size="small"
            dataSource={impactSummary}
            renderItem={(impact) => (
              <List.Item key={`${impact.field}-${impact.target_value}-${impact.source_value}`}>
                <Space orientation="vertical" size={0} style={{ width: "100%" }}>
                  <Text type="secondary">{impact.field}:</Text>
                  <div style={{ paddingLeft: 16, fontSize: "12px" }}>
                    <div>
                      <Text type="secondary">From (target): </Text>
                      <Text code style={{ color: "#ff4d4f" }}>{impact.target_value ?? "null"}</Text>
                    </div>
                    <div>
                      <Text type="secondary">To (source): </Text>
                      <Text code style={{ color: "#52c41a" }}>{impact.source_value ?? "null"}</Text>
                    </div>
                  </div>
                </Space>
              </List.Item>
            )}
          />
        </div>
      )}
    </Space>
  );
}
