import { Card, Descriptions, Tag, Typography, Button, Space } from "antd";
import { ProjectRead } from "@/api/generated";
import { HistoryOutlined } from "@ant-design/icons";
import { Can } from "@/components/auth/Can";

interface ProjectSummaryCardProps {
  project: ProjectRead;
  loading?: boolean;
  onViewHistory?: () => void;
}

export const ProjectSummaryCard = ({
  project,
  loading,
  onViewHistory,
}: ProjectSummaryCardProps) => {
  return (
    <Card
      loading={loading}
      style={{ marginBottom: 16 }}
      extra={
        onViewHistory && (
          <Space>
            <Can permission="project-read">
              <Button icon={<HistoryOutlined />} onClick={onViewHistory}>
                History
              </Button>
            </Can>
          </Space>
        )
      }
    >
      <div style={{ marginBottom: 16 }}>
        <Typography.Title level={4} style={{ margin: 0 }}>
          {project.name}{" "}
          <Tag color="blue" style={{ marginLeft: 8 }}>
            {project.code}
          </Tag>
        </Typography.Title>
      </div>

      <Descriptions size="small" column={{ xs: 1, sm: 2, md: 3 }} bordered>
        <Descriptions.Item label="Status">
          <Tag color={project.status === "Active" ? "green" : "default"}>
            {project.status || "Unknown"}
          </Tag>
        </Descriptions.Item>
        <Descriptions.Item label="Budget">
          {project.budget
            ? new Intl.NumberFormat("en-US", {
                style: "currency",
                currency: "USD",
              }).format(Number(project.budget))
            : "-"}
        </Descriptions.Item>
        <Descriptions.Item label="Contract Value">
          {project.contract_value
            ? new Intl.NumberFormat("en-US", {
                style: "currency",
                currency: "USD",
              }).format(Number(project.contract_value))
            : "-"}
        </Descriptions.Item>
        <Descriptions.Item label="Start Date">
          {project.start_date
            ? new Date(project.start_date).toLocaleDateString()
            : "-"}
        </Descriptions.Item>
        <Descriptions.Item label="End Date">
          {project.end_date
            ? new Date(project.end_date).toLocaleDateString()
            : "-"}
        </Descriptions.Item>
        <Descriptions.Item label="Branch">
          <Tag color="orange">{project.branch || "main"}</Tag>
        </Descriptions.Item>
        <Descriptions.Item label="Description" span={3}>
          {project.description || "-"}
        </Descriptions.Item>
      </Descriptions>
    </Card>
  );
};
