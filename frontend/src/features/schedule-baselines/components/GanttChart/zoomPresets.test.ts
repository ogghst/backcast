/**
 * Unit tests for Gantt zoom presets (pure logic).
 *
 * @module features/schedule-baselines/components/GanttChart
 */

import { describe, it, expect } from "vitest";
import {
  getZoomPreset,
  DAY_MS,
  WEEK_MS,
  MONTH_MS,
} from "./zoomPresets";
import type { ZoomLevel } from "./config";

// Fixed reference timestamps used across formatter assertions.
const TS_JAN_01_2025 = Date.UTC(2025, 0, 1); // Wed, 1 Jan 2025
const TS_JAN_15_2025 = Date.UTC(2025, 0, 15); // mid-month
const TS_MAR_20_2025 = Date.UTC(2025, 2, 20); // Q1
const TS_JUL_04_2025 = Date.UTC(2025, 6, 4); // Q3
const TS_OCT_31_2025 = Date.UTC(2025, 9, 31); // Q4, day 31

describe("getZoomPreset", () => {
  it("returns a preset for every zoom level", () => {
    const levels: ZoomLevel[] = ["day", "week", "month", "quarter"];
    for (const level of levels) {
      const preset = getZoomPreset(level);
      expect(preset).toBeDefined();
      expect(typeof preset.tickIntervalMs).toBe("number");
      expect(typeof preset.splitlineIntervalMs).toBe("number");
      expect(typeof preset.defaultWindowMs).toBe("number");
      expect(typeof preset.primaryAxis.formatter).toBe("function");
      expect(preset.headerRows).toBeGreaterThanOrEqual(1);
    }
  });
});

describe("day preset", () => {
  const preset = getZoomPreset("day");

  it("uses daily ticks + daily splitlines", () => {
    expect(preset.tickIntervalMs).toBe(DAY_MS);
    expect(preset.splitlineIntervalMs).toBe(DAY_MS);
  });

  it("frames a ~14 day window", () => {
    expect(preset.defaultWindowMs).toBe(14 * DAY_MS);
  });

  it("renders two header rows", () => {
    expect(preset.headerRows).toBe(2);
  });

  it("primary axis formats as 'MMM ''YY' (month) regardless of day", () => {
    expect(preset.primaryAxis.formatter(TS_JAN_01_2025)).toBe("Jan '25");
    expect(preset.primaryAxis.formatter(TS_JAN_15_2025)).toBe("Jan '25");
  });

  it("secondary axis formats the day-of-month WITHOUT leading zero", () => {
    expect(preset.secondaryAxis?.formatter(TS_JAN_01_2025)).toBe("1");
    expect(preset.secondaryAxis?.formatter(TS_OCT_31_2025)).toBe("31");
  });
});

describe("week preset", () => {
  const preset = getZoomPreset("week");

  it("uses weekly ticks + weekly splitlines", () => {
    expect(preset.tickIntervalMs).toBe(WEEK_MS);
    expect(preset.splitlineIntervalMs).toBe(WEEK_MS);
  });

  it("frames a ~9 week window", () => {
    expect(preset.defaultWindowMs).toBe(9 * WEEK_MS);
  });

  it("primary axis formats as month", () => {
    expect(preset.primaryAxis.formatter(TS_JAN_01_2025)).toBe("Jan '25");
  });

  it("secondary axis formats as dd/mm weekly", () => {
    expect(preset.secondaryAxis?.formatter(TS_JAN_01_2025)).toBe("01/01");
    expect(preset.secondaryAxis?.formatter(TS_OCT_31_2025)).toBe("31/10");
  });
});

describe("month preset (default — must match pre-refactor behaviour)", () => {
  const preset = getZoomPreset("month");

  it("uses weekly ticks + weekly splitlines", () => {
    expect(preset.tickIntervalMs).toBe(WEEK_MS);
    expect(preset.splitlineIntervalMs).toBe(WEEK_MS);
  });

  it("frames a ~6 month window (30-day approximation)", () => {
    expect(preset.defaultWindowMs).toBe(6 * MONTH_MS);
  });

  it("primary cascading formatter emits month label only within first 7 days", () => {
    // Day 1 of month → label
    expect(preset.primaryAxis.formatter(TS_JAN_01_2025)).toBe("Jan '25");
    // Day 15 of month → blank (cascading suppression)
    expect(preset.primaryAxis.formatter(TS_JAN_15_2025)).toBe("");
  });

  it("primary cascading formatter emits at day 7 (boundary inclusive) and blanks at day 8", () => {
    const day7 = Date.UTC(2025, 0, 7);
    const day8 = Date.UTC(2025, 0, 8);
    expect(preset.primaryAxis.formatter(day7)).toBe("Jan '25");
    expect(preset.primaryAxis.formatter(day8)).toBe("");
  });

  it("secondary axis formats as dd/mm weekly (unchanged)", () => {
    expect(preset.secondaryAxis?.formatter(TS_JAN_01_2025)).toBe("01/01");
  });
});

describe("quarter preset", () => {
  const preset = getZoomPreset("quarter");

  it("uses monthly ticks + monthly splitlines", () => {
    expect(preset.tickIntervalMs).toBe(MONTH_MS);
    expect(preset.splitlineIntervalMs).toBe(MONTH_MS);
  });

  it("frames a ~15 month window", () => {
    expect(preset.defaultWindowMs).toBe(15 * MONTH_MS);
  });

  it("primary axis formats as 'Qn ''YY' quarterly", () => {
    expect(preset.primaryAxis.formatter(TS_JAN_01_2025)).toBe("Q1 '25");
    expect(preset.primaryAxis.formatter(TS_MAR_20_2025)).toBe("Q1 '25");
    expect(preset.primaryAxis.formatter(TS_JUL_04_2025)).toBe("Q3 '25");
    expect(preset.primaryAxis.formatter(TS_OCT_31_2025)).toBe("Q4 '25");
  });

  it("primary interval is a quarter (3 months)", () => {
    expect(preset.primaryAxis.interval).toBe(3 * MONTH_MS);
  });

  it("secondary axis formats as short month name only", () => {
    expect(preset.secondaryAxis?.formatter(TS_JAN_01_2025)).toBe("Jan");
    expect(preset.secondaryAxis?.formatter(TS_OCT_31_2025)).toBe("Oct");
  });
});

describe("formatters — timezone robustness", () => {
  it("all formatters are pure (same input → same output)", () => {
    const presets = (["day", "week", "month", "quarter"] as ZoomLevel[]).map(
      getZoomPreset,
    );
    for (const p of presets) {
      const primaryA = p.primaryAxis.formatter(TS_JUL_04_2025);
      const primaryB = p.primaryAxis.formatter(TS_JUL_04_2025);
      expect(primaryA).toBe(primaryB);
      if (p.secondaryAxis) {
        const secA = p.secondaryAxis.formatter(TS_JUL_04_2025);
        const secB = p.secondaryAxis.formatter(TS_JUL_04_2025);
        expect(secA).toBe(secB);
      }
    }
  });
});
