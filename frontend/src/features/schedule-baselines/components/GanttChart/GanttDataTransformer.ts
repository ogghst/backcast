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
  wbeId: string;
  /** True for WBE group headers */
  isWbe: boolean;
  /** Current collapse state */
  collapsed: boolean;
  /** Total descendants for display */
  childrenCount: number;
}

/** Internal tree node used during hierarchy construction. */
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
 * 1. Build a tree of WBE nodes from flat items using parent_wbe_id
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

  // Sort roots and children by WBE code for consistent ordering
  const sortByCode = (a: WbeNode, b: WbeNode) =>
    a.wbeCode.localeCompare(b.wbeCode, undefined, { numeric: true });

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
    const isCollapsed = collapsedWbeIds.has(node.wbeId);

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
      wbeId: node.wbeId,
      isWbe: true,
      collapsed: isCollapsed,
      childrenCount: node.children.length + node.items.length,
    });

    // If collapsed, skip children and cost elements
    if (isCollapsed) return;

    // Add child WBE nodes first (recursive)
    for (const child of node.children) {
      flattenNode(child, collapsedWbeIds);
    }

    // Then add cost element items under this WBE
    const sortedItems = [...node.items].sort((a, b) =>
      a.cost_element_code.localeCompare(b.cost_element_code, undefined, {
        numeric: true,
      }),
    );

    for (const item of sortedItems) {
      rows.push({
        name: item.cost_element_name,
        level: node.wbeLevel + 1,
        costElementId: item.cost_element_id,
        startDate: item.start_date ? new Date(item.start_date) : null,
        endDate: item.end_date ? new Date(item.end_date) : null,
        progressionType: item.progression_type,
        budgetAmount: item.budget_amount,
        wbeCode: item.wbe_code,
        wbeId: item.wbe_id,
        isWbe: false,
        collapsed: false,
        childrenCount: 0,
      });
    }
  }

  for (const root of roots) {
    flattenNode(root, collapsedWbeIds);
  }

  return rows;
}

/**
 * Build the Y-axis label with indentation.
 * Uses unicode triangle characters for WBE collapse state.
 */
export function formatRowLabel(row: GanttRow): string {
  const indent = "\u00A0\u00A0\u00A0\u00A0".repeat(row.level);
  if (row.isWbe) {
    const prefix = row.collapsed ? "\u25B6" : "\u25BC";
    return `${indent}${prefix} ${row.name}`;
  }
  return `${indent}${row.name}`;
}
