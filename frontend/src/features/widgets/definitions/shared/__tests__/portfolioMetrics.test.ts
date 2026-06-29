/**
 * Unit tests for the shared portfolio-widget metrics module.
 *
 * Merged from the legacy rag + roleLayout suites (Phase 3 of the
 * global-dashboard-widgets initiative): all 17 rag helper tests + the 5
 * cpiCostDistress tests, with imports repointed to this shared module.
 *
 * Source files deleted alongside this consolidation:
 *   - features/portfolio/utils/__tests__/rag.test.ts
 *   - the cpiCostDistress block from features/portfolio/__tests__/roleLayout.test.ts
 */

import { describe, it, expect } from "vitest";
import {
  ragBand,
  ragToStatus,
  indexBand,
  RED_BAND_THRESHOLD,
  cpiCostDistress,
} from "../portfolioMetrics";
import type { PortfolioProjectMetrics } from "@/api/generated/models/PortfolioProjectMetrics";

function makeProject(
  overrides: Partial<PortfolioProjectMetrics>,
): PortfolioProjectMetrics {
  return {
    project_id: "p-1",
    name: "P1",
    status: "active",
    bac: 1000,
    currency: "EUR",
    at_risk: false,
    ...overrides,
  };
}

describe("rag utils", () => {
  describe("indexBand (single index)", () => {
    it("returns Green for index >= 1.0", () => {
      expect(indexBand(1.0)).toBe("Green");
      expect(indexBand(1.05)).toBe("Green");
      expect(indexBand(2.0)).toBe("Green");
    });

    it("returns Amber for index in [0.9, 1.0)", () => {
      expect(indexBand(0.9)).toBe("Amber");
      expect(indexBand(0.95)).toBe("Amber");
      expect(indexBand(0.999)).toBe("Amber");
    });

    it("returns Red for index < 0.9", () => {
      expect(indexBand(0.89)).toBe("Red");
      expect(indexBand(0.5)).toBe("Red");
      expect(indexBand(0)).toBe("Red");
    });

    it("returns Unknown for null/undefined/NaN", () => {
      expect(indexBand(null)).toBe("Unknown");
      expect(indexBand(undefined)).toBe("Unknown");
      // NaN is a realistic input (CPI/SPI are EV/AC divisions); pin the
      // defensive Number.isNaN branch so it can't silently regress to Red.
      expect(indexBand(NaN)).toBe("Unknown");
    });

    it("treats the exact boundary 1.0 as Green", () => {
      expect(indexBand(1.0)).toBe("Green");
    });

    it("treats the exact boundary 0.9 as Amber", () => {
      expect(indexBand(0.9)).toBe("Amber");
    });
  });

  describe("ragBand (worse of CPI & SPI)", () => {
    it("returns Green when both indices are >= 1.0", () => {
      expect(ragBand(1.0, 1.0)).toBe("Green");
      expect(ragBand(1.2, 1.5)).toBe("Green");
    });

    it("returns Amber when one index is in [0.9, 1.0) and the other is Green", () => {
      expect(ragBand(0.9, 1.1)).toBe("Amber");
      expect(ragBand(1.1, 0.95)).toBe("Amber");
    });

    it("returns Red when one index is < 0.9 regardless of the other", () => {
      expect(ragBand(0.8, 1.2)).toBe("Red");
      expect(ragBand(1.2, 0.8)).toBe("Red");
      expect(ragBand(0.5, 0.6)).toBe("Red");
    });

    it("returns Amber when both indices are Amber (worse-of-two tie at Amber)", () => {
      expect(ragBand(0.91, 0.95)).toBe("Amber");
    });

    it("returns the present band when only one index is present", () => {
      expect(ragBand(null, 1.1)).toBe("Green");
      expect(ragBand(0.85, null)).toBe("Red");
      expect(ragBand(null, 0.95)).toBe("Amber");
    });

    it("returns Unknown when both indices are null", () => {
      expect(ragBand(null, null)).toBe("Unknown");
    });

    it("respects exact boundaries in the worse-of-two combination", () => {
      // CPI = 1.0 (Green), SPI = 0.9 (Amber) → worse is Amber
      expect(ragBand(1.0, 0.9)).toBe("Amber");
      // CPI = 0.9 (Amber), SPI = 0.89 (Red) → worse is Red
      expect(ragBand(0.9, 0.89)).toBe("Red");
    });
  });

  describe("ragToStatus (MetricCard status mapping)", () => {
    it("maps Green → good", () => {
      expect(ragToStatus("Green")).toBe("good");
    });

    it("maps Amber → warning", () => {
      expect(ragToStatus("Amber")).toBe("warning");
    });

    it("maps Red → bad", () => {
      expect(ragToStatus("Red")).toBe("bad");
    });

    it("maps Unknown → warning", () => {
      expect(ragToStatus("Unknown")).toBe("warning");
    });
  });
});

describe("cpiCostDistress", () => {
  it("keeps only projects with cpi present and strictly below the Red-band threshold", () => {
    const projects = [
      makeProject({ project_id: "a", name: "A", cpi: 0.8 }),
      makeProject({ project_id: "b", name: "B", cpi: RED_BAND_THRESHOLD }), // exactly 0.9 → NOT distressed
      makeProject({ project_id: "c", name: "C", cpi: 0.95 }),
      makeProject({ project_id: "d", name: "D", cpi: 1.1 }),
      makeProject({ project_id: "e", name: "E", cpi: null }),
    ];

    const out = cpiCostDistress(projects);

    expect(out.map((p) => p.project_id)).toEqual(["a"]);
  });

  it("excludes projects whose cpi is null or undefined", () => {
    const projects = [
      makeProject({ project_id: "a", name: "A", cpi: null }),
      makeProject({ project_id: "b", name: "B" }), // cpi undefined
      makeProject({ project_id: "c", name: "C", cpi: 0.5 }),
    ];

    const out = cpiCostDistress(projects);

    expect(out.map((p) => p.project_id)).toEqual(["c"]);
  });

  it("ranks results CPI ascending (worst first)", () => {
    const projects = [
      makeProject({ project_id: "a", name: "A", cpi: 0.85 }),
      makeProject({ project_id: "b", name: "B", cpi: 0.7 }),
      makeProject({ project_id: "c", name: "C", cpi: 0.6 }),
    ];

    const out = cpiCostDistress(projects);

    expect(out.map((p) => p.cpi)).toEqual([0.6, 0.7, 0.85]);
  });

  it("returns an empty array when no project is in distress", () => {
    const projects = [
      makeProject({ project_id: "a", name: "A", cpi: 1.0 }),
      makeProject({ project_id: "b", name: "B", cpi: RED_BAND_THRESHOLD }),
      makeProject({ project_id: "c", name: "C", cpi: null }),
    ];

    expect(cpiCostDistress(projects)).toEqual([]);
  });

  it("does not mutate the input array", () => {
    const projects = [
      makeProject({ project_id: "a", name: "A", cpi: 0.8 }),
      makeProject({ project_id: "b", name: "B", cpi: 0.6 }),
    ];
    const snapshot = projects.map((p) => ({ ...p }));

    cpiCostDistress(projects);

    expect(projects).toEqual(snapshot);
  });
});
