/**
 * Gantt chart data hook
 *
 * Fetches aggregated Gantt data for a project's schedule baselines.
 * Uses TimeMachine params for as_of, branch, and mode support.
 */

import { useQuery } from "@tanstack/react-query";
import { useTimeMachineParams } from "@/contexts/TimeMachineContext";
import { request as __request } from "@/api/generated/core/request";
import { OpenAPI } from "@/api/generated/core/OpenAPI";
import { queryKeys } from "@/api/queryKeys";

/** Single item returned by the Gantt data API. */
export interface GanttItem {
  cost_element_id: string;
  cost_element_code: string;
  cost_element_name: string;
  wbe_id: string;
  wbe_code: string;
  wbe_name: string;
  wbe_level: number;
  parent_wbe_id: string | null;
  budget_amount: number;
  start_date: string | null;
  end_date: string | null;
  progression_type: string | null;
}

/** Top-level response from the Gantt data API. */
export interface GanttDataResponse {
  items: GanttItem[];
  project_start: string | null;
  project_end: string | null;
}

/**
 * Fetch Gantt chart data for a project.
 *
 * @param projectId - The project ID to fetch Gantt data for
 */
export const useGanttData = (projectId: string) => {
  const { asOf, mode, branch } = useTimeMachineParams();

  return useQuery<GanttDataResponse>({
    queryKey: queryKeys.gantt.project(projectId, { asOf, mode, branch }),
    queryFn: async () => {
      const res = await __request(OpenAPI, {
        method: "GET",
        url: "/api/v1/projects/{project_id}/gantt-data",
        path: {
          project_id: projectId,
        },
        query: {
          branch,
          mode,
          as_of: asOf || undefined,
        },
      });
      return res as GanttDataResponse;
    },
    enabled: !!projectId,
  });
};
