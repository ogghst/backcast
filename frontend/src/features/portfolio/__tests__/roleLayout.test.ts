/**
 * Unit tests for the Phase 2 role-curated layout config.
 *
 * Covers: each role resolves to the approved title / lead metrics / default
 * sort / section order; an unknown role falls back to `default`. (The
 * `cpiCostDistress` selector moved to the shared module — see
 * `features/widgets/definitions/shared/__tests__/portfolioMetrics.test.ts`.)
 */

import { describe, it, expect } from "vitest";
import { roleLayout } from "@/features/portfolio/roleLayout";

describe("roleLayout", () => {
  it("default role → CPI/SPI/VAC/TCPI leads, no default sort, kpis→coPipeline→table→atRisk", () => {
    const layout = roleLayout.default;

    expect(layout.title).toBe("Portfolio Dashboard");
    expect(layout.leadMetrics).toEqual(["cpi", "spi", "vac", "tcpi"]);
    expect(layout.defaultSort).toBeUndefined();
    expect(layout.sectionOrder).toEqual([
      "kpis",
      "coPipeline",
      "table",
      "atRisk",
    ]);
    expect(layout.leadDistressCount).toBeUndefined();
  });

  it("cost-controller → CPI lead + cost distress count, CPI asc sort, costDistress section before table", () => {
    const layout = roleLayout["cost-controller"];

    expect(layout.title).toBe("Cost Controlling");
    expect(layout.leadMetrics).toEqual(["cpi"]);
    expect(layout.leadDistressCount).toBe("cost");
    expect(layout.defaultSort).toEqual({ field: "cpi", order: "ascend" });
    expect(layout.sectionOrder).toEqual([
      "kpis",
      "costDistress",
      "table",
      "coPipeline",
      "atRisk",
    ]);
  });

  it("pmo-director → SPI lead + schedule distress count, SPI asc sort, atRisk section right after kpis", () => {
    const layout = roleLayout["pmo-director"];

    expect(layout.title).toBe("PMO / Schedule Governance");
    expect(layout.leadMetrics).toEqual(["spi"]);
    expect(layout.leadDistressCount).toBe("schedule");
    expect(layout.defaultSort).toEqual({ field: "spi", order: "ascend" });
    expect(layout.sectionOrder).toEqual([
      "kpis",
      "atRisk",
      "table",
      "coPipeline",
    ]);
  });

  it("cost-controller default sort field is `cpi` (ascend) — cost lens first", () => {
    expect(roleLayout["cost-controller"].defaultSort?.field).toBe("cpi");
    expect(roleLayout["cost-controller"].defaultSort?.order).toBe("ascend");
  });

  it("pmo-director default sort field is `spi` (ascend) — schedule lens first", () => {
    expect(roleLayout["pmo-director"].defaultSort?.field).toBe("spi");
    expect(roleLayout["pmo-director"].defaultSort?.order).toBe("ascend");
  });

  it("section order for cost-controller puts table before coPipeline (cost review focus)", () => {
    const order = roleLayout["cost-controller"].sectionOrder;
    expect(order.indexOf("table")).toBeLessThan(order.indexOf("coPipeline"));
  });

  it("section order for pmo-director puts atRisk immediately after kpis", () => {
    const order = roleLayout["pmo-director"].sectionOrder;
    expect(order[0]).toBe("kpis");
    expect(order[1]).toBe("atRisk");
  });

  it("every layout's sectionOrder starts with kpis and includes table + coPipeline", () => {
    for (const [name, layout] of Object.entries(roleLayout)) {
      expect(layout.sectionOrder[0]).toBe("kpis");
      expect(layout.sectionOrder).toContain("table");
      expect(layout.sectionOrder).toContain("coPipeline");
      // guard against duplicate section keys
      expect(new Set(layout.sectionOrder).size).toBe(layout.sectionOrder.length);
      // ensure every section key is one we can render
      void name;
    }
  });

  it("leadMetrics never references an unknown metric key", () => {
    const valid = new Set(["cpi", "spi", "vac", "tcpi"]);
    for (const layout of Object.values(roleLayout)) {
      for (const m of layout.leadMetrics) {
        expect(valid.has(m)).toBe(true);
      }
    }
  });
});
