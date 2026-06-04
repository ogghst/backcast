/**
 * Project Schedule Page
 *
 * Displays the Gantt chart for a project's schedule baselines,
 * plus a collapsible dependency management panel below.
 *
 * @module pages/projects
 */

import { useMemo } from "react";
import { useParams } from "react-router-dom";
import { Card, theme } from "antd";
import { GanttChart } from "@/features/schedule-baselines/components/GanttChart/GanttChart";
import { ScheduleDependencyPanel } from "@/features/schedule-baselines/components/ScheduleDependencyPanel";
import { useGanttData } from "@/features/schedule-baselines/api/useGanttData";

export const ProjectSchedulePage: React.FC = () => {
  const { projectId } = useParams<{ projectId: string }>();
  const { token } = theme.useToken();

  // NOTE: useGanttData is also called inside GanttChart. TanStack Query deduplicates
  // by query key, so only one network request is made. This call is kept at the page
  // level because the dependency panel needs the schedule items for its dropdown.
  const { data } = useGanttData(projectId ?? "");

  // Derive schedule options from Gantt data items for the dependency panel
  const schedules = useMemo(
    () =>
      (data?.items ?? [])
        .filter((item) => item.cost_element_id && item.start_date && item.end_date)
        .map((item) => ({
          schedule_baseline_id: item.cost_element_id!,
          name: item.cost_element_name ?? item.wbe_name ?? "",
          code: item.cost_element_code ?? "",
          start_date: item.start_date,
          end_date: item.end_date,
        })),
    [data?.items],
  );

  if (!projectId) {
    return null;
  }

  return (
    <div style={{ padding: `${token.paddingXL}px 0` }}>
      <h1 style={{ margin: 0, marginBottom: token.marginLG }}>Project Schedule</h1>
      <Card
        styles={{ body: { padding: token.paddingMD } }}
        loading={false}
      >
        <GanttChart projectId={projectId} />
      </Card>
      <div style={{ marginTop: token.marginLG }}>
        <ScheduleDependencyPanel projectId={projectId} schedules={schedules} />
      </div>
    </div>
  );
};
