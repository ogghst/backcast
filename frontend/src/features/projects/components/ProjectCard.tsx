import { Button, Space, Tag, theme } from "antd";
import {
  EditOutlined,
  DeleteOutlined,
  HistoryOutlined,
  CalendarOutlined,
  DollarOutlined,
} from "@ant-design/icons";
import { useNavigate } from "react-router-dom";
import type { ProjectRead } from "@/api/generated";
import { Can } from "@/components/auth/Can";

interface ProjectCardProps {
  project: ProjectRead;
  onEdit: (project: ProjectRead) => void;
  onDelete: (projectId: string) => void;
  onViewHistory: (project: ProjectRead) => void;
}

const statusColorMap: Record<string, string> = {
  Draft: "default",
  Active: "processing",
  Completed: "success",
  "On Hold": "warning",
};

const formatCurrency = (value: number | null | undefined) =>
  value
    ? new Intl.NumberFormat("en-US", {
        style: "currency",
        currency: "EUR",
        currencyDisplay: "narrowSymbol",
      }).format(value)
    : "-";

const formatDate = (date: string | null | undefined) =>
  date ? new Date(date).toLocaleDateString() : "-";

export const ProjectCard = ({
  project,
  onEdit,
  onDelete,
  onViewHistory,
}: ProjectCardProps) => {
  const { token } = theme.useToken();
  const navigate = useNavigate();

  return (
    <div
      onClick={() => navigate(`/projects/${project.project_id}`)}
      style={{
        background: token.colorBgContainer,
        border: `1px solid ${token.colorBorderSecondary}`,
        borderRadius: token.borderRadiusLG,
        padding: token.paddingMD,
        cursor: "pointer",
        transition: "all 150ms ease",
      }}
      onMouseEnter={(e) => {
        e.currentTarget.style.borderColor = token.colorPrimary;
        e.currentTarget.style.boxShadow = `0 2px 8px ${token.colorPrimary}20`;
      }}
      onMouseLeave={(e) => {
        e.currentTarget.style.borderColor = token.colorBorderSecondary;
        e.currentTarget.style.boxShadow = "none";
      }}
    >
      {/* Header: Name + Status */}
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "flex-start",
          marginBottom: token.marginSM,
          gap: token.marginSM,
        }}
      >
        <div style={{ flex: 1, minWidth: 0 }}>
          <div
            style={{
              fontSize: token.fontSizeLG,
              fontWeight: 600,
              color: token.colorText,
              overflow: "hidden",
              textOverflow: "ellipsis",
              whiteSpace: "nowrap",
            }}
          >
            {project.name}
          </div>
          <div
            style={{
              fontSize: token.fontSizeSM,
              color: token.colorTextSecondary,
            }}
          >
            {project.code}
          </div>
        </div>
        <Tag color={statusColorMap[project.status] || "default"}>
          {project.status}
        </Tag>
      </div>

      {/* Metrics row */}
      <div
        style={{
          display: "flex",
          gap: token.marginMD,
          marginBottom: token.marginSM,
          flexWrap: "wrap",
        }}
      >
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: token.marginXS,
            fontSize: token.fontSizeSM,
            color: token.colorTextSecondary,
          }}
        >
          <DollarOutlined />
          <span>Budget: {formatCurrency(project.budget)}</span>
        </div>
        {project.contract_value && (
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: token.marginXS,
              fontSize: token.fontSizeSM,
              color: token.colorTextSecondary,
            }}
          >
            <DollarOutlined />
            <span>Contract: {formatCurrency(project.contract_value)}</span>
          </div>
        )}
      </div>

      {/* Dates row */}
      {(project.start_date || project.end_date) && (
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: token.marginXS,
            fontSize: token.fontSizeSM,
            color: token.colorTextTertiary,
            marginBottom: token.marginSM,
          }}
        >
          <CalendarOutlined />
          <span>
            {formatDate(project.start_date)} — {formatDate(project.end_date)}
          </span>
        </div>
      )}

      {/* Actions */}
      <div
        style={{
          display: "flex",
          justifyContent: "flex-end",
          borderTop: `1px solid ${token.colorBorderSecondary}`,
          paddingTop: token.marginSM,
          marginTop: token.marginXS,
        }}
      >
        <Space size="small">
          <Can permission="project-read">
            <Button
              size="small"
              icon={<HistoryOutlined />}
              onClick={(e) => {
                e.stopPropagation();
                onViewHistory(project);
              }}
              title="View History"
            />
          </Can>
          <Can permission="project-update">
            <Button
              size="small"
              icon={<EditOutlined />}
              onClick={(e) => {
                e.stopPropagation();
                onEdit(project);
              }}
              title="Edit Project"
            />
          </Can>
          <Can permission="project-delete">
            <Button
              size="small"
              danger
              icon={<DeleteOutlined />}
              onClick={(e) => {
                e.stopPropagation();
                onDelete(project.project_id);
              }}
              title="Delete Project"
            />
          </Can>
        </Space>
      </div>
    </div>
  );
};
