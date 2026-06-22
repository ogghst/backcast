/**
 * GanttToolbar
 *
 * One cohesive, fully-tokenised control cluster for the Gantt chart:
 *   - discrete zoom `Segmented` (Day/Week/Month/Quarter)
 *   - framing icon buttons (Today / Fit), each in a `Tooltip`
 *   - a Tree `Dropdown` (Expand All / Collapse All / Level N)
 *   - a density `Segmented` (Comfortable / Compact)
 *
 * Sub-groups are separated by subtle token dividers (`token.colorSplit`).
 * Presentation-agnostic: it consumes viewport state/actions from
 * {@link useScheduleViewport} plus an optional `tree` prop (computed by the
 * GanttChart wrapper) for collapse-to-level.
 *
 * @module features/schedule-baselines/components/GanttChart
 */

import React, { useMemo } from "react";
import { Segmented, Tooltip, Button, Dropdown, theme } from "antd";
import {
  AimOutlined,
  CompressOutlined,
  ApartmentOutlined,
} from "@ant-design/icons";
import type { MenuProps } from "antd";
import type { ZoomLevel } from "./config";
import {
  ZOOM_LEVELS,
  type ScheduleViewport,
  type GanttDensity,
} from "./useScheduleViewport";

/**
 * Tree-control handle. The GanttChart wrapper computes `allWbeIds` / `maxLevel`
 * from the raw items and wires the actions to the viewport.
 */
export interface GanttTreeControls {
  /** Every distinct WBE id in the project (for "Collapse All"). */
  allWbeIds: string[];
  /** Deepest WBE outline level present (drives the Level N menu depth). */
  maxLevel: number;
  /** Expand every WBE group. */
  expandAll: () => void;
  /** Collapse exactly the WBE ids in the set. */
  collapseAll: (ids: Iterable<string>) => void;
  /** Collapse so the outline shows levels 1..N-1 (N >= 1). */
  collapseToLevel: (level: number) => void;
}

export interface GanttToolbarProps {
  /** Viewport state + actions from useScheduleViewport. */
  viewport: ScheduleViewport;
  /** Optional tree controls (omit to hide the Tree dropdown). */
  tree?: GanttTreeControls;
}

/** Display label per zoom level. */
const ZOOM_LABELS: Record<ZoomLevel, string> = {
  day: "Day",
  week: "Week",
  month: "Month",
  quarter: "Quarter",
};

/** Display label per density. */
const DENSITY_LABELS: Record<GanttDensity, string> = {
  comfortable: "Comfortable",
  compact: "Compact",
};

/** Segmented option shape carrying the value as `value`. */
interface SegOption<T extends string> {
  label: string;
  value: T;
  title: string;
}

/**
 * Zoom + framing + tree + density toolbar. See module doc.
 */
export const GanttToolbar: React.FC<GanttToolbarProps> = ({ viewport, tree }) => {
  const { token } = theme.useToken();
  const { zoom, setZoom, density, setDensity, scrollToToday, fitProject } =
    viewport;

  const zoomOptions = useMemo<SegOption<ZoomLevel>[]>(
    () =>
      ZOOM_LEVELS.map((level) => ({
        label: ZOOM_LABELS[level],
        value: level,
        title: `${ZOOM_LABELS[level]} zoom`,
      })),
    [],
  );

  const densityOptions = useMemo<SegOption<GanttDensity>[]>(
    () =>
      (Object.keys(DENSITY_LABELS) as GanttDensity[]).map((d) => ({
        label: DENSITY_LABELS[d],
        value: d,
        title: `${DENSITY_LABELS[d]} density`,
      })),
    [],
  );

  // Tree dropdown menu: Expand All / Collapse All, divider, then Level 1..maxLevel
  const treeMenu = useMemo<MenuProps>(() => {
    if (!tree) return { items: [] };
    const levelItems: MenuProps["items"] = [];
    for (let lvl = 1; lvl <= tree.maxLevel; lvl++) {
      levelItems.push({
        key: `level-${lvl}`,
        label: `Level ${lvl}`,
        onClick: () => tree.collapseToLevel(lvl),
      });
    }
    return {
      items: [
        {
          key: "expand-all",
          label: "Expand All",
          onClick: tree.expandAll,
        },
        {
          key: "collapse-all",
          label: "Collapse All",
          onClick: () => tree.collapseAll(tree.allWbeIds),
        },
        { type: "divider" },
        ...(levelItems ?? []),
      ],
    };
  }, [tree]);

  const containerStyle = useMemo<React.CSSProperties>(
    () => ({
      display: "flex",
      alignItems: "center",
      gap: token.marginSM,
      flexWrap: "wrap",
    }),
    [token.marginSM],
  );

  const dividerStyle = useMemo<React.CSSProperties>(
    () => ({
      width: 1,
      alignSelf: "stretch",
      margin: `${token.marginXXS}px 0`,
      backgroundColor: token.colorSplit,
    }),
    [token.colorSplit, token.marginXXS],
  );

  return (
    <div style={containerStyle}>
      <Segmented
        size="small"
        value={zoom}
        onChange={(value) => setZoom(value as ZoomLevel)}
        options={zoomOptions}
      />
      <Tooltip title="Scroll to Today">
        <Button
          size="small"
          icon={<AimOutlined />}
          onClick={scrollToToday}
          aria-label="Scroll to Today"
        />
      </Tooltip>
      <Tooltip title="Fit project">
        <Button
          size="small"
          icon={<CompressOutlined />}
          onClick={fitProject}
          aria-label="Fit project"
        />
      </Tooltip>
      {tree && (
        <>
          <div style={dividerStyle} aria-hidden />
          <Dropdown menu={treeMenu} trigger={["click"]}>
            <Button size="small" icon={<ApartmentOutlined />} aria-label="Tree">
              Tree
            </Button>
          </Dropdown>
        </>
      )}
      <div style={dividerStyle} aria-hidden />
      <Segmented
        size="small"
        value={density}
        onChange={(value) => setDensity(value as GanttDensity)}
        options={densityOptions}
      />
    </div>
  );
};
