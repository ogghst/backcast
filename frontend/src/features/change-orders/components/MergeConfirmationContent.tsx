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
  impactSummary,
  targetStatus,
}: Omit<MergeConfirmationContentProps, "entityCount">) {
  return (
    <Space direction="vertical" size="middle" style={{ width: "100%" }}>
      {/* Primary confirmation message */}
      <Alert
        type="info"
        showIcon
        icon={<InfoCircleOutlined />}
        message={
          <Space direction="vertical" size={0}>
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
            `Branch to merge: <Text code>{sourceBranch}</Text>`,
            `Target branch: <Text code>{targetBranch}</Text>`,
            `Entities to update: <Text strong>{entityCount}</Text>`,
            `New status: <Text strong>{targetStatus}</Text>`,
          ]}
          renderItem={(item) => (
            <List.Item>
              <CheckCircleOutlined style={{ color: "#52c41a", marginRight: 8 }} />
              <span dangerouslySetInnerHTML={{ __html: item }} />
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
              <List.Item>
                <Space direction="vertical" size={0} style={{ width: "100%" }}>
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
