/**
 * Project Gantt Compare Page
 *
 * Displays the @wamra/gantt-task-react Gantt chart for side-by-side
 * comparison with the existing ECharts implementation.
 *
 * @module pages/projects
 */

import { useParams } from "react-router-dom";
import { Card, theme } from "antd";
import { GanttChartWamra } from "@/features/schedule-baselines/components/GanttChart/GanttChartWamra";

export const ProjectGanttComparePage: React.FC = () => {
  const { projectId } = useParams<{ projectId: string }>();
  const { token } = theme.useToken();

  if (!projectId) {
    return null;
  }

  return (
    <div style={{ padding: token.paddingXL }}>
      <h1 style={{ margin: 0, marginBottom: token.marginLG }}>
        Gantt (Library)
      </h1>
      <Card styles={{ body: { padding: token.paddingMD } }} loading={false}>
        <GanttChartWamra projectId={projectId} height={500} />
      </Card>
    </div>
  );
};
