import { Alert, List, Space, Tag, Typography } from "antd";
import { CloseCircleOutlined } from "@ant-design/icons";
import type { MergeConflict } from "../api/useChangeOrders";

interface MergeConflictsListProps {
  /** List of merge conflicts */
  conflicts: MergeConflict[];
  /** Optional custom message */
  message?: string;
}

/**
 * MergeConflictsList - Display merge conflicts in error modal.
 *
 * Shows a list of conflicts that prevent merging, with details about
 * what fields conflict between source and target branches.
 */
export function MergeConflictsList({
  conflicts,
  message,
}: MergeConflictsListProps) {
  const conflictCount = conflicts.length;

  return (
    <Space direction="vertical" size="middle" style={{ width: "100%" }}>
      {/* Error banner */}
      <Alert
        type="error"
        showIcon
        icon={<CloseCircleOutlined />}
        message={
          message ||
          `Merge blocked: ${conflictCount} conflict${conflictCount > 1 ? "s" : ""} detected`
        }
        description="Please resolve the conflicts before merging."
      />

      {/* Conflicts list */}
      <List
        size="small"
        dataSource={conflicts}
        renderItem={(conflict) => (
          <List.Item>
            <Space direction="vertical" size={4} style={{ width: "100%" }}>
              {/* Entity and field header */}
              <Space>
                <Tag color="orange">{conflict.entity_type}</Tag>
                <Typography.Text strong>{conflict.field}</Typography.Text>
                <Typography.Text type="secondary">ID: {conflict.entity_id.slice(0, 8)}...</Typography.Text>
              </Space>

              {/* Branch labels */}
              <div style={{ paddingLeft: 12, fontSize: "12px" }}>
                <Space split="→">
                  <span>
                    <Tag color="red">{conflict.target_branch}</Tag>
                    <Typography.Text type="secondary">current: </Typography.Text>
                    <Typography.Text code>{conflict.target_value ?? "null"}</Typography.Text>
                  </span>
                  <span>
                    <Tag color="green">{conflict.source_branch}</Tag>
                    <Typography.Text type="secondary">incoming: </Typography.Text>
                    <Typography.Text code>{conflict.source_value ?? "null"}</Typography.Text>
                  </span>
                </Space>
              </div>
            </Space>
          </List.Item>
        )}
      />

      {/* Resolution hint */}
      <Typography.Text type="secondary" style={{ fontSize: "12px" }}>
        To resolve: Re-apply your changes on the target branch, or reset the source
        branch to match the target branch.
      </Typography.Text>
    </Space>
  );
}
