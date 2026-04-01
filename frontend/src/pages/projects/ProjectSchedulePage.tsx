/**
 * Project Schedule Page
 *
 * Displays the Gantt chart for a project's schedule baselines.
 * Follows the same pattern as ProjectEVMAnalysis.
 *
 * @module pages/projects
 */

import { useParams } from "react-router-dom";
import { Card, theme } from "antd";
import { GanttChart } from "@/features/schedule-baselines/components/GanttChart/GanttChart";

export const ProjectSchedulePage: React.FC = () => {
  const { projectId } = useParams<{ projectId: string }>();
  const { token } = theme.useToken();

  if (!projectId) {
    return null;
  }

  return (
    <div style={{ padding: token.paddingXL }}>
      <h1 style={{ margin: 0, marginBottom: token.marginLG }}>Project Schedule</h1>
      <Card
        styles={{ body: { padding: token.paddingMD } }}
        loading={false}
      >
        <GanttChart projectId={projectId} />
      </Card>
    </div>
  );
};
