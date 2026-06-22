/**
 * Tests for the pure Gantt data transformer helpers — specifically
 * {@link computeCollapseToLevel}, the tree-compaction primitive that backs the
 * toolbar's "Level N" menu.
 *
 * @module features/schedule-baselines/components/GanttChart
 */

import { describe, it, expect } from "vitest";
import { computeCollapseToLevel } from "./GanttDataTransformer";
import type { GanttItem } from "../../api/useGanttData";

/** Build a minimal GanttItem for the level math. */
function item(
  wbsId: string,
  level: number,
  parent: string | null,
): GanttItem {
  return {
    cost_element_id: null,
    cost_element_code: null,
    cost_element_name: null,
    wbs_element_id: wbsId,
    wbe_code: wbsId,
    wbe_name: wbsId,
    wbe_level: level,
    parent_wbs_element_id: parent,
    budget_amount: null,
    start_date: null,
    end_date: null,
    progression_type: null,
  };
}

// Sample tree: root (L1) → child (L2) → grandchild (L3)
const SAMPLE: GanttItem[] = [
  item("root", 1, null),
  item("child-a", 2, "root"),
  item("child-b", 2, "root"),
  item("gc-1", 3, "child-a"),
  item("gc-2", 3, "child-b"),
];

describe("computeCollapseToLevel", () => {
  it("level 1 collapses every WBE (only root headers visible)", () => {
    const ids = computeCollapseToLevel(SAMPLE, 1);
    expect(ids).toEqual(
      new Set(["root", "child-a", "child-b", "gc-1", "gc-2"]),
    );
  });

  it("level 2 keeps roots expanded, collapses L2+ (their children hidden)", () => {
    const ids = computeCollapseToLevel(SAMPLE, 2);
    // roots (L1) NOT in set; L2 and L3 are.
    expect(ids.has("root")).toBe(false);
    expect(ids).toEqual(new Set(["child-a", "child-b", "gc-1", "gc-2"]));
  });

  it("level 3 shows L1..L2 expanded, collapses only L3", () => {
    const ids = computeCollapseToLevel(SAMPLE, 3);
    expect(ids).toEqual(new Set(["gc-1", "gc-2"]));
  });

  it("level beyond maxLevel collapses nothing (≈ Expand All)", () => {
    const ids = computeCollapseToLevel(SAMPLE, 4);
    expect(ids.size).toBe(0);
  });

  it("returns distinct WBE ids even when a WBE has many cost elements", () => {
    const many: GanttItem[] = [
      item("root", 1, null),
      item("root", 1, null), // duplicate WBE (multiple cost elements)
      item("child", 2, "root"),
    ];
    const ids = computeCollapseToLevel(many, 2);
    // "root" (L1) excluded; only "child" (L2) collapsed.
    expect(ids).toEqual(new Set(["child"]));
    expect(ids.size).toBe(1);
  });

  it("empty input yields an empty set", () => {
    expect(computeCollapseToLevel([], 1).size).toBe(0);
  });
});
