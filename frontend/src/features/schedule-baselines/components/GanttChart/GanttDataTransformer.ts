/**
 * Gantt Data Transformer
 *
 * Pure functions that transform the flat API response into ECharts-friendly
 * structures for the Gantt chart. Builds WBE hierarchy, inserts group headers,
 * and flattens depth-first for display.
 *
 * @module features/schedule-baselines/components/GanttChart
 */

import type { GanttItem } from "../../api/useGanttData";

/** A single display row in the Gantt chart. */
export interface GanttRow {
  /** Display name for the Y-axis */
  name: string;
  /** Indentation level */
  level: number;
  /** Cost element ID (null for WBE group headers) */
  costElementId: string | null;
  /** Start date (aggregated for WBE headers, actual for cost elements) */
  startDate: Date | null;
  /** End date (aggregated for WBE headers, actual for cost elements) */
  endDate: Date | null;
  /** Progression type */
  progressionType: string | null;
  /** Budget amount */
  budgetAmount: number;
  /** WBE code */
  wbeCode: string;
  /** WBE ID */
  wbsElementId: string;
  /** True for WBE group headers */
  isWbe: boolean;
  /** Current collapse state */
  collapsed: boolean;
  /** Total descendants for display */
  childrenCount: number;
}

/** Internal tree node used during hierarchy construction. */
interface WbeNode {
  wbsElementId: string;
  wbeCode: string;
  wbeName: string;
  wbeLevel: number;
  parentWbsElementId: string | null;
  items: GanttItem[];
  children: WbeNode[];
  aggregatedStartDate: Date | null;
  aggregatedEndDate: Date | null;
}

/**
 * Compute aggregated start/end dates for a WBE node via post-order traversal.
 *
 * Takes the minimum start date and maximum end date from the node's own cost
 * elements and all child WBEs' already-computed aggregated dates.
 */
function computeAggregatedDates(node: WbeNode): void {
  // Recurse into children first (post-order)
  for (const child of node.children) {
    computeAggregatedDates(child);
  }

  const dates: Date[] = [];

  // Collect dates from direct cost elements
  for (const item of node.items) {
    if (item.start_date) dates.push(new Date(item.start_date));
    if (item.end_date) dates.push(new Date(item.end_date));
  }

  // Collect aggregated dates from child WBEs
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
 * Transform flat GanttItem array into an ordered list of GanttRow objects.
 *
 * Steps:
 * 1. Build a tree of WBE nodes from flat items using parent_wbs_element_id
 * 2. Compute aggregated dates via post-order traversal
 * 3. Insert WBE group headers at each level
 * 4. Depth-first flatten to produce display order, respecting collapsed state
 * 5. Indent labels based on wbe_level
 */
export function transformGanttData(
  items: GanttItem[],
  collapsedWbeIds: Set<string> = new Set(),
): GanttRow[] {
  if (items.length === 0) return [];

  // Build a map of WBE nodes
  const nodeMap = new Map<string, WbeNode>();
  const roots: WbeNode[] = [];

  // First pass: create nodes for each unique WBE
  for (const item of items) {
    if (!nodeMap.has(item.wbs_element_id)) {
      const node: WbeNode = {
        wbsElementId: item.wbs_element_id,
        wbeCode: item.wbe_code,
        wbeName: item.wbe_name,
        wbeLevel: item.wbe_level,
        parentWbsElementId: item.parent_wbs_element_id,
        items: [],
        children: [],
        aggregatedStartDate: null,
        aggregatedEndDate: null,
      };
      nodeMap.set(item.wbs_element_id, node);
    }
    nodeMap.get(item.wbs_element_id)!.items.push(item);
  }

  // Second pass: build parent-child relationships
  for (const node of nodeMap.values()) {
    if (node.parentWbsElementId && nodeMap.has(node.parentWbsElementId)) {
      nodeMap.get(node.parentWbsElementId)!.children.push(node);
    } else {
      roots.push(node);
    }
  }

  // Sort roots and children by WBE code for consistent ordering
  const sortByCode = (a: WbeNode, b: WbeNode) =>
    (a.wbeCode ?? "").localeCompare(b.wbeCode ?? "", undefined, { numeric: true });

  roots.sort(sortByCode);
  for (const node of nodeMap.values()) {
    node.children.sort(sortByCode);
  }

  // Compute aggregated dates for each root (post-order traversal)
  for (const root of roots) {
    computeAggregatedDates(root);
  }

  // Depth-first flatten
  const rows: GanttRow[] = [];

  function flattenNode(node: WbeNode, collapsedWbeIds: Set<string>): void {
    const isCollapsed = collapsedWbeIds.has(node.wbsElementId);

    // Add WBE group header with aggregated dates
    rows.push({
      name: node.wbeName,
      level: node.wbeLevel,
      costElementId: null,
      startDate: node.aggregatedStartDate,
      endDate: node.aggregatedEndDate,
      progressionType: null,
      budgetAmount: 0,
      wbeCode: node.wbeCode,
      wbsElementId: node.wbsElementId,
      isWbe: true,
      collapsed: isCollapsed,
      childrenCount: node.children.length + node.items.length,
    });

    // If collapsed, skip cost elements and child WBEs
    if (isCollapsed) return;

    // Add cost element items directly under this WBE first
    // so they appear right after the WBE header, before any child WBEs
    const sortedItems = [...node.items].sort((a, b) =>
      (a.cost_element_code ?? "").localeCompare(b.cost_element_code ?? "", undefined, {
        numeric: true,
      }),
    );

    for (const item of sortedItems) {
      rows.push({
        name: item.cost_element_name ?? item.wbe_name ?? "",
        level: node.wbeLevel + 1,
        costElementId: item.cost_element_id,
        startDate: item.start_date ? new Date(item.start_date) : null,
        endDate: item.end_date ? new Date(item.end_date) : null,
        progressionType: item.progression_type,
        budgetAmount: item.budget_amount ?? 0,
        wbeCode: item.wbe_code ?? "",
        wbsElementId: item.wbs_element_id,
        isWbe: false,
        collapsed: false,
        childrenCount: 0,
      });
    }

    // Then add child WBE nodes (recursive)
    for (const child of node.children) {
      flattenNode(child, collapsedWbeIds);
    }
  }

  for (const root of roots) {
    flattenNode(root, collapsedWbeIds);
  }

  return rows;
}

/**
 * Build the Y-axis label (raw name only).
 * Visual indentation and icons are handled by ECharts rich text formatter.
 */
export function formatRowLabel(row: GanttRow): string {
  return row.name;
}

/**
 * Compute the set of WBE ids to collapse so the tree shows only outline
 * levels `1..level-1` expanded and hides everything deeper.
 *
 * Semantics: "collapse to level N" collapses every WBE whose own outline
 * level is `>= N`, so the outline displays levels `1..N-1` expanded.
 *   - `level = 1` → only root WBE headers are visible (every WBE collapsed).
 *   - `level = 2` → roots expanded, their direct-child WBE headers visible.
 *   - `level = maxLevel + 1` (or beyond) → nothing collapsed → equivalent to
 *     "Expand All".
 *
 * @param items - Raw Gantt items (flat API response)
 * @param level - Outline level to collapse from (1 = collapse all)
 * @returns Set of distinct `wbs_element_id` values to collapse
 */
export function computeCollapseToLevel(
  items: GanttItem[],
  level: number,
): Set<string> {
  const ids = new Set<string>();
  for (const item of items) {
    if (item.wbe_level >= level) {
      ids.add(item.wbs_element_id);
    }
  }
  return ids;
}

/**
 * Build a map from costElementId (which represents work_package_id / schedule_baseline_id)
 * to the y-axis index in the rows array. Used for dependency arrow coordinate resolution.
 *
 * Only includes rows that have a costElementId (non-WBE rows with schedule data).
 */
export function buildScheduleBaselineIndex(rows: GanttRow[]): Map<string, number> {
  const index = new Map<string, number>();
  rows.forEach((row, i) => {
    if (row.costElementId && row.startDate && row.endDate) {
      index.set(row.costElementId, i);
    }
  });
  return index;
}
