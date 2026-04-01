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
import { EntityCard } from "@/components/common/EntityCard";

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
    <EntityCard
      title={project.name}
      subtitle={project.code}
      badge={
        <Tag color={statusColorMap[project.status] || "default"}>
          {project.status}
        </Tag>
      }
      onClick={() => navigate(`/projects/${project.project_id}`)}
      metrics={
        <div
          style={{
            display: "flex",
            gap: token.marginMD,
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
      }
      meta={
        (project.start_date || project.end_date) ? (
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: token.marginXS,
              fontSize: token.fontSizeSM,
              color: token.colorTextTertiary,
            }}
          >
            <CalendarOutlined />
            <span>
              {formatDate(project.start_date)} — {formatDate(project.end_date)}
            </span>
          </div>
        ) : undefined
      }
      actions={
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
      }
    />
  );
};
