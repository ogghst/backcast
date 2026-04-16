import { ProjectOutlined } from "@ant-design/icons";
import { Space, Tag, Typography, theme } from "antd";
import type { FC } from "react";
import { useProject } from "@/features/projects/api/useProjects";
import { getProjectStatusColor } from "@/lib/status";
import { useDashboardContext } from "../context/useDashboardContext";
import { WidgetShell } from "../components/WidgetShell";
import { registerWidget, widgetTypeId } from "..";
import type { WidgetComponentProps } from "../types";
import { formatDate } from "@/utils/formatters";

const { Text } = Typography;

interface ProjectHeaderConfig {
  showDates: boolean;
  showStatus: boolean;
}

/** Format an ISO date string as "MMM YYYY" (e.g. "Jan 2024"). */
const formatMonthYear = (date: string | null | undefined): string => {
  if (!date) return "";
  return formatDate(date, { style: "medium", fallback: "" });
};

const ProjectHeaderComponent: FC<WidgetComponentProps<ProjectHeaderConfig>> = ({
  config,
  instanceId,
  isEditing,
  onRemove,
  onConfigure,
  onFullscreen,
  widgetType,
  dashboardName,
}) => {
  const { token } = theme.useToken();
  const { projectId } = useDashboardContext();
  const { data: project, isLoading, error, refetch } = useProject(projectId);

  return (
    <WidgetShell
      instanceId={instanceId}
      title="Project Header"
      icon={<ProjectOutlined />}
      isEditing={isEditing}
      isLoading={isLoading}
      error={error}
      onRemove={onRemove}
      onRefresh={refetch}
      onConfigure={onConfigure}
      onFullscreen={onFullscreen}
      widgetType={widgetType}
      dashboardName={dashboardName}
    >
      {project ? (
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: token.paddingSM,
            flexWrap: "wrap",
            minHeight: 0,
          }}
        >
          <Text
            strong
            style={{
              fontSize: token.fontSizeLG,
              lineHeight: token.lineHeightLG,
            }}
          >
            {project.name}
          </Text>

          <Text
            type="secondary"
            style={{
              fontSize: token.fontSizeSM,
            }}
          >
            {project.code}
          </Text>

          {config.showStatus && project.status && (
            <Tag
              color={getProjectStatusColor(project.status)}
              style={{ margin: 0 }}
            >
              {project.status}
            </Tag>
          )}

          {config.showDates &&
            (project.start_date || project.end_date) && (
              <Space size={4} style={{ marginLeft: "auto" }}>
                {project.start_date && (
                  <Text
                    type="secondary"
                    style={{ fontSize: token.fontSizeSM }}
                  >
                    {formatMonthYear(project.start_date)}
                  </Text>
                )}
                {project.start_date && project.end_date && (
                  <Text
                    type="secondary"
                    style={{ fontSize: token.fontSizeXS }}
                  >
                    –
                  </Text>
                )}
                {project.end_date && (
                  <Text
                    type="secondary"
                    style={{ fontSize: token.fontSizeSM }}
                  >
                    {formatMonthYear(project.end_date)}
                  </Text>
                )}
              </Space>
            )}
        </div>
      ) : (
        !isLoading &&
        !error && (
          <div
            style={{
              textAlign: "center",
              padding: token.paddingMD,
            }}
          >
            <Text type="secondary">No project data available</Text>
          </div>
        )
      )}
    </WidgetShell>
  );
};

registerWidget<ProjectHeaderConfig>({
  typeId: widgetTypeId("project-header"),
  displayName: "Project Header",
  description: "Project name, code, status, and date range at a glance",
  category: "summary",
  icon: <ProjectOutlined />,
  sizeConstraints: {
    minW: 4,
    minH: 1,
    defaultW: 4,
    defaultH: 1,
  },
  component: ProjectHeaderComponent,
  defaultConfig: {
    showDates: true,
    showStatus: true,
  },
});
