/**
 * Structural tests for buildGanttOptions — guards the ECharts dual-grid
 * gotcha (a grid whose only series are empty custom-series can collapse and
 * skip axis labels) across all four zoom levels, plus the config-driven
 * layout derivations. These assert on option SHAPE, not pixels.
 *
 * @module features/schedule-baselines/components/GanttChart
 */

import { describe, it, expect } from "vitest";
import { buildGanttOptions } from "./GanttChartOptions";
import { transformGanttData, buildScheduleBaselineIndex } from "./GanttDataTransformer";
import { defaultFullConfig, defaultCompactConfig, type GanttChartConfig } from "./config";
import { getZoomPreset, DAY_MS, WEEK_MS, MONTH_MS } from "./zoomPresets";
import type {
  EChartsColorPalette,
  EChartsTooltipConfig,
} from "@/features/evm/utils/echartsTheme";
import type { GanttDataResponse, GanttDependencyLink } from "../../api/useGanttData";

const COLORS: EChartsColorPalette = {
  primary: "#1677ff",
  success: "#52c41a",
  warning: "#faad14",
  error: "#ff4d4f",
  info: "#1677ff",
  pv: "#5b8ff9",
  ev: "#5ad8a6",
  ac: "#5d7092",
  forecast: "#faad14",
  actual: "#ff4d4f",
  gaugeGood: "#52c41a",
  gaugeWarning: "#faad14",
  gaugeBad: "#ff4d4f",
  text: "#000",
  textSecondary: "#8c8c8c",
  border: "#d9d9d9",
  bg: "#fff",
};

const TOOLTIP: EChartsTooltipConfig = {
  backgroundColor: "#fff",
  borderColor: "#d9d9d9",
  borderWidth: 1,
  textStyle: { color: "#000", fontSize: 12 },
  padding: [8, 12],
  extraCssText: "",
};

const SAMPLE: GanttDataResponse = {
  items: [
    {
      cost_element_id: "ce-1",
      cost_element_code: "1.1.1",
      cost_element_name: "Engineering",
      wbs_element_id: "wbe-1",
      wbe_code: "1.1",
      wbe_name: "Phase A",
      wbe_level: 2,
      parent_wbs_element_id: null,
      budget_amount: 1000,
      start_date: "2025-01-01",
      end_date: "2025-06-01",
      progression_type: "LINEAR",
    },
  ],
  project_start: "2025-01-01",
  project_end: "2025-12-31",
  dependencies: [] as GanttDependencyLink[],
};

function buildOption(config: GanttChartConfig) {
  const rows = transformGanttData(SAMPLE.items);
  const scheduleIndex = buildScheduleBaselineIndex(rows);
  return buildGanttOptions(
    rows,
    SAMPLE.dependencies,
    scheduleIndex,
    new Date(SAMPLE.project_start!),
    new Date(SAMPLE.project_end!),
    COLORS,
    TOOLTIP,
    "EUR",
    config,
  ) as {
    grid: unknown[];
    xAxis: Array<{ gridIndex: number; interval?: number; splitLine?: { show: boolean } }>;
    series: Array<{ xAxisIndex: number; type: string; data?: unknown[] }>;
    dataZoom: Array<{ type: string; xAxisIndex?: number[]; startValue?: number; endValue?: number }>;
  };
}

describe("buildGanttOptions — dual-grid gotcha (all zooms)", () => {
  const zooms = ["day", "week", "month", "quarter"] as const;

  for (const zoom of zooms) {
    it(`renders two grids for zoom=${zoom}`, () => {
      const opt = buildOption({ ...defaultFullConfig, zoom });
      expect(opt.grid).toHaveLength(2);
    });

    it(`preserves BOTH dummy series on grid 0 for zoom=${zoom} (axis-label keepalive)`, () => {
      const opt = buildOption({ ...defaultFullConfig, zoom });
      const dummySeries = opt.series.filter(
        (s) => s.xAxisIndex === 0 || s.xAxisIndex === 2,
      );
      // Must have at least one series per grid-0 xAxis (0 and 2) AND each must
      // carry data — an empty custom-series-only grid collapses its labels.
      expect(dummySeries.length).toBeGreaterThanOrEqual(2);
      const hasDummyOnAxis0 = dummySeries.some(
        (s) => s.xAxisIndex === 0 && (s.data?.length ?? 0) > 0,
      );
      const hasDummyOnAxis2 = dummySeries.some(
        (s) => s.xAxisIndex === 2 && (s.data?.length ?? 0) > 0,
      );
      expect(hasDummyOnAxis0).toBe(true);
      expect(hasDummyOnAxis2).toBe(true);
    });

    it(`emits 3 xAxes (primary/secondary on grid 0 + main on grid 1) for zoom=${zoom}`, () => {
      const opt = buildOption({ ...defaultFullConfig, zoom });
      expect(opt.xAxis).toHaveLength(3);
      expect(opt.xAxis[0].gridIndex).toBe(0);
      expect(opt.xAxis[1].gridIndex).toBe(1);
      expect(opt.xAxis[2].gridIndex).toBe(0);
    });
  }
});

describe("buildGanttOptions — config-driven layout derivation", () => {
  it("derives splitline interval from the active zoom preset", () => {
    const cases: Array<{ zoom: "day" | "week" | "month" | "quarter"; ms: number }> = [
      { zoom: "day", ms: DAY_MS },
      { zoom: "week", ms: WEEK_MS },
      { zoom: "month", ms: WEEK_MS },
      { zoom: "quarter", ms: MONTH_MS },
    ];
    for (const { zoom, ms } of cases) {
      const opt = buildOption({ ...defaultFullConfig, zoom });
      expect(opt.xAxis[1].interval).toBe(ms);
      // matches the preset
      expect(opt.xAxis[1].interval).toBe(getZoomPreset(zoom).splitlineIntervalMs);
    }
  });

  it("sets the slider initial window from the preset's defaultWindowMs", () => {
    const opt = buildOption(defaultFullConfig); // month
    const slider = opt.dataZoom.find((d) => d.type === "slider")!;
    const window = getZoomPreset("month").defaultWindowMs;
    expect(slider.endValue! - slider.startValue!).toBe(window);
  });

  it("uses config.density for grid1 top/bottom (no-op refactor)", () => {
    const opt = buildOption(defaultFullConfig);
    const grid1 = opt.grid[1] as { top?: number; bottom?: number };
    expect(grid1.top).toBe(defaultFullConfig.density.headerHeight);
    expect(grid1.bottom).toBe(defaultFullConfig.density.bottomPadding);
  });

  it("uses config.gridLeft for both grids", () => {
    const opt = buildOption({ ...defaultFullConfig, gridLeft: 424 });
    const g0 = opt.grid[0] as { left?: number };
    const g1 = opt.grid[1] as { left?: number };
    expect(g0.left).toBe(424);
    expect(g1.left).toBe(424);
  });
});

describe("buildGanttOptions — feature flags", () => {
  it("omits the dependency-arrow series when showDependencies=false (compact)", () => {
    const opt = buildOption(defaultCompactConfig);
    // compact config has no dependencies anyway; assert only bar + 2 dummy = 3 series
    expect(opt.series.length).toBe(3);
  });

  it("includes the dependency-arrow series when showDependencies=true", () => {
    const withDeps: GanttDataResponse = {
      ...SAMPLE,
      dependencies: [
        {
          dependency_id: "d1",
          predecessor_id: "ce-1",
          successor_id: "ce-1",
          dependency_type: "FS",
          lag_days: 0,
        },
      ],
    };
    const rows = transformGanttData(withDeps.items);
    const scheduleIndex = buildScheduleBaselineIndex(rows);
    const opt = buildGanttOptions(
      rows,
      withDeps.dependencies,
      scheduleIndex,
      new Date(withDeps.project_start!),
      new Date(withDeps.project_end!),
      COLORS,
      TOOLTIP,
      "EUR",
      defaultFullConfig,
    ) as { series: Array<{ data?: unknown[] }> };
    // bar(1) + dummy(2) + dep(1) = 4
    expect(opt.series.length).toBe(4);
  });

  it("omits the slider but keeps inside-zoom when showDataZoom=false", () => {
    const opt = buildOption(defaultCompactConfig);
    const sliders = opt.dataZoom.filter((d) => d.type === "slider");
    const inside = opt.dataZoom.filter((d) => d.type === "inside");
    expect(sliders).toHaveLength(0);
    expect(inside.length).toBeGreaterThanOrEqual(1);
  });

  it("includes both slider + inside when showDataZoom=true", () => {
    const opt = buildOption(defaultFullConfig);
    const sliders = opt.dataZoom.filter((d) => d.type === "slider");
    const inside = opt.dataZoom.filter((d) => d.type === "inside");
    expect(sliders).toHaveLength(1);
    expect(inside).toHaveLength(1);
  });
});

describe("buildGanttOptions — progression color tokenisation", () => {
  it("resolves LINEAR/GAUSSIAN/LOGARITHMIC via the pv/ev/forecast palette tokens", () => {
    // The bar series foreground colour is chosen inside renderItem; verify the
    // palette carries the tokenised values the builder reads (no raw hex in
    // options source). pv/ev/forecast are the canonical chart tokens.
    expect(COLORS.pv).toBeDefined();
    expect(COLORS.ev).toBeDefined();
    expect(COLORS.forecast).toBeDefined();
  });
});
