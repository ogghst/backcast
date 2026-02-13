import { Descriptions, Space, Tag, Typography } from "antd";
import dayjs from "dayjs";
import type { ChangeOrderPublic } from "@/api/generated";

const { Text, Paragraph } = Typography;

interface ChangeOrderDetailsSectionProps {
  /** Change Order data */
  changeOrder: ChangeOrderPublic;
}

/**
 * ChangeOrderDetailsSection - Display Change Order metadata.
 *
 * Shows key information about the Change Order including code, title,
 * status, branch, dates, and other metadata in a compact format.
 */
export function ChangeOrderDetailsSection({
  changeOrder,
}: ChangeOrderDetailsSectionProps) {
  // Status color mapping
  const getStatusColor = (status: string) => {
    const colors: Record<string, string> = {
      Draft: "default",
      "Submitted for Approval": "processing",
      "Under Review": "processing",
      Approved: "success",
      Implemented: "success",
      Rejected: "error",
    };
    return colors[status] || "default";
  };

  return (
    <Descriptions
      column={2}
      size="small"
      bordered
      items={[
        {
          label: "Code",
          children: <Text code>{changeOrder.code}</Text>,
        },
        {
          label: "Status",
          children: <Tag color={getStatusColor(changeOrder.status || "")}>{changeOrder.status || "Unknown"}</Tag>,
        },
        {
          label: "Title",
          children: <Text strong>{changeOrder.title || "No title"}</Text>,
          span: 2,
        },
        {
          label: "Branch",
          children: (
            <Space>
              <Text code>{changeOrder.branch}</Text>
              {changeOrder.branch_locked && (
                <Tag color="red">
                  Locked
                </Tag>
              )}
            </Space>
          ),
        },
        {
          label: "Effective Date",
          children: changeOrder.effective_date
            ? dayjs(changeOrder.effective_date).format("YYYY-MM-DD")
            : "Not set",
        },
        {
          label: "Description",
          children: (
            <Paragraph
              ellipsis={{ rows: 2, expandable: true }}
              style={{ marginBottom: 0 }}
            >
              {changeOrder.description || "No description"}
            </Paragraph>
          ),
          span: 2,
        },
        ...(changeOrder.justification
          ? [
              {
                label: "Justification",
                children: (
                  <Paragraph
                    ellipsis={{ rows: 2, expandable: true }}
                    style={{ marginBottom: 0 }}
                  >
                    {changeOrder.justification}
                  </Paragraph>
                ),
                span: 2,
              },
            ]
          : []),
      ]}
    />
  );
}
