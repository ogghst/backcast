/**
 * Gantt Task Adapter
 *
 * Transforms flat GanttItem[] from the API into the Task[] format
 * expected by @wamra/gantt-task-react. Builds WBE hierarchy as
 * project-type group tasks with cost elements as child tasks.
 *
 * @module features/schedule-baselines/components/GanttChart
 */

import type { Task } from "@wamra/gantt-task-react";
import type { GanttItem } from "../../api/useGanttData";

/** Progression type to color mapping (matches existing ECharts Gantt). */
const PROGRESSION_COLORS: Record<string, string> = {
  LINEAR: "#5b8ff9",
  GAUSSIAN: "#5ad8a6",
  LOGARITHMIC: "#faad14",
};

/** Default color for items without a progression type. */
const DEFAULT_COLOR = "#4a7c91";

/** Internal WBE tree node used during hierarchy construction. */
interface WbeNode {
  wbeId: string;
  wbeCode: string;
  wbeName: string;
  wbeLevel: number;
  parentWbeId: string | null;
  items: GanttItem[];
  children: WbeNode[];
  aggregatedStartDate: Date | null;
  aggregatedEndDate: Date | null;
}

/**
 * Compute aggregated start/end dates for a WBE node via post-order traversal.
 */
function computeAggregatedDates(node: WbeNode): void {
  for (const child of node.children) {
    computeAggregatedDates(child);
  }

  const dates: Date[] = [];

  for (const item of node.items) {
    if (item.start_date) dates.push(new Date(item.start_date));
    if (item.end_date) dates.push(new Date(item.end_date));
  }

  for (const child of node.children) {
    if (child.aggregatedStartDate) dates.push(child.aggregatedStartDate);
    if (child.aggregatedEndDate) dates.push(child.aggregatedEndDate);
  }

  node.aggregatedStartDate =
    dates.length > 0
      ? dates.reduce((min, d) => (d < min ? d : min))
      : null;
  node.aggregatedEndDate =
    dates.length > 0
      ? dates.reduce((max, d) => (d > max ? d : max))
      : null;
}

/**
 * Get the bar color for a cost element based on its progression type.
 */
function getBarColor(progressionType: string | null): string {
  if (progressionType && PROGRESSION_COLORS[progressionType]) {
    return PROGRESSION_COLORS[progressionType];
  }
  return DEFAULT_COLOR;
}

/**
 * Adapt flat GanttItem[] into library-compatible Task[].
 *
 * Builds WBE hierarchy, creates project-type group tasks for WBE nodes,
 * and task-type items for cost elements with valid dates.
 */
export function adaptGanttItems(items: GanttItem[]): Task[] {
  if (items.length === 0) return [];

  const nodeMap = new Map<string, WbeNode>();
  const roots: WbeNode[] = [];

  // First pass: create WBE nodes
  for (const item of items) {
    if (!nodeMap.has(item.wbe_id)) {
      const node: WbeNode = {
        wbeId: item.wbe_id,
        wbeCode: item.wbe_code,
        wbeName: item.wbe_name,
        wbeLevel: item.wbe_level,
        parentWbeId: item.parent_wbe_id,
        items: [],
        children: [],
        aggregatedStartDate: null,
        aggregatedEndDate: null,
      };
      nodeMap.set(item.wbe_id, node);
    }
    nodeMap.get(item.wbe_id)!.items.push(item);
  }

  // Second pass: build parent-child relationships
  for (const node of nodeMap.values()) {
    if (node.parentWbeId && nodeMap.has(node.parentWbeId)) {
      nodeMap.get(node.parentWbeId)!.children.push(node);
    } else {
      roots.push(node);
    }
  }

  // Sort by WBE code for consistent ordering
  const sortByCode = (a: WbeNode, b: WbeNode) =>
    a.wbeCode.localeCompare(b.wbeCode, undefined, { numeric: true });

  roots.sort(sortByCode);
  for (const node of nodeMap.values()) {
    node.children.sort(sortByCode);
  }

  // Compute aggregated dates
  for (const root of roots) {
    computeAggregatedDates(root);
  }

  // Flatten into Task[] with depth-first traversal
  const tasks: Task[] = [];

  function flattenNode(
    node: WbeNode,
    parentProjectId: string | null,
  ): void {
    // All WBE nodes become project-type tasks (group bars)
    // If no aggregated dates, use the project date range or a minimal span
    const startDate =
      node.aggregatedStartDate ?? new Date("2025-01-01");
    const endDate =
      node.aggregatedEndDate ?? new Date("2025-12-31");

    const projectTask: Task = {
      id: `wbe-${node.wbeId}`,
      name: node.wbeName,
      type: "project",
      start: startDate,
      end: endDate,
      progress: 0,
      hideChildren: false,
      isDisabled: true,
      parent: parentProjectId ?? undefined,
      styles: {
        projectBackgroundColor: "#4a7c91",
        projectProgressColor: "#5b8ff9",
      },
    };

    tasks.push(projectTask);

    // Recurse into child WBE nodes
    for (const child of node.children) {
      flattenNode(child, projectTask.id);
    }

    // Add cost element items with valid dates
    const sortedItems = [...node.items].sort((a, b) =>
      a.cost_element_code.localeCompare(b.cost_element_code, undefined, {
        numeric: true,
      }),
    );

    for (const item of sortedItems) {
      if (!item.start_date || !item.end_date) continue;

      const barColor = getBarColor(item.progression_type);

      tasks.push({
        id: item.cost_element_id,
        name: item.cost_element_name,
        type: "task",
        start: new Date(item.start_date),
        end: new Date(item.end_date),
        progress: 0,
        isDisabled: true,
        parent: projectTask.id,
        styles: {
          barBackgroundColor: barColor,
          barBackgroundSelectedColor: barColor,
          barProgressColor: barColor,
        },
      });
    }
  }

  for (const root of roots) {
    flattenNode(root, null);
  }

  return tasks;
}
