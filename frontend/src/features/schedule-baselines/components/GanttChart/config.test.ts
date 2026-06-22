/**
 * Unit tests for Gantt chart config defaults (pure logic).
 *
 * @module features/schedule-baselines/components/GanttChart
 */

import { describe, it, expect } from "vitest";
import {
  defaultFullConfig,
  defaultCompactConfig,
} from "./config";

describe("defaultFullConfig", () => {
  it("is full mode with month zoom", () => {
    expect(defaultFullConfig.mode).toBe("full");
    expect(defaultFullConfig.zoom).toBe("month");
  });

  it("has the expected full density (no-op refactor contract)", () => {
    expect(defaultFullConfig.density).toEqual({
      rowHeight: 32,
      headerHeight: 56,
      bottomPadding: 80,
    });
    expect(defaultFullConfig.gridLeft).toBe(300);
  });

  it("enables all optional features", () => {
    expect(defaultFullConfig.showDependencies).toBe(true);
    expect(defaultFullConfig.showDataZoom).toBe(true);
    expect(defaultFullConfig.showTimeHeader).toBe(true);
  });
});

describe("defaultCompactConfig", () => {
  it("is compact mode with month zoom", () => {
    expect(defaultCompactConfig.mode).toBe("compact");
    expect(defaultCompactConfig.zoom).toBe("month");
  });

  it("has the expected compact density for the future widget", () => {
    expect(defaultCompactConfig.density).toEqual({
      rowHeight: 22,
      headerHeight: 28,
      bottomPadding: 24,
    });
    expect(defaultCompactConfig.gridLeft).toBe(120);
  });

  it("disables dependencies + dataZoom (widget drives its own framing)", () => {
    expect(defaultCompactConfig.showDependencies).toBe(false);
    expect(defaultCompactConfig.showDataZoom).toBe(false);
    expect(defaultCompactConfig.showTimeHeader).toBe(true);
  });
});
