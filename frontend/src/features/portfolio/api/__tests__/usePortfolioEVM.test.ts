import { describe, it, expect } from "vitest";
import type { PortfolioEVMResponse } from "@/api/generated/models/PortfolioEVMResponse";
import { transformPortfolioNumeric } from "../usePortfolioEVM";

/**
 * Minimal summary fixture: only the numeric fields the transform touches.
 *
 * The generated `EVMMetricsResponse` types the metrics as `number`, but the
 * whole reason `transformPortfolioNumeric` exists is that the backend ships
 * Decimal-serialized strings at runtime — so the fixtures deliberately use
 * strings and cast through `unknown` (the documented TS escape hatch).
 */
function makeSummary(overrides: Record<string, unknown> = {}): PortfolioEVMResponse["summary"] {
  return {
    entity_type: "project",
    entity_id: "portfolio",
    control_date: "2026-06-28",
    branch: "main",
    branch_mode: "MERGE",
    bac: "1000",
    pv: "500",
    ac: "600",
    ev: "450",
    cv: "-150",
    sv: "-50",
    cpi: "0.75",
    spi: "0.9",
    eac: "1333.33",
    vac: "-333.33",
    etc: "733.33",
    tcpi: "1.36",
    ...overrides,
  } as unknown as PortfolioEVMResponse["summary"];
}

function makeProject(overrides: Record<string, unknown> = {}): PortfolioEVMResponse["projects"][number] {
  return {
    project_id: "p1",
    name: "Project One",
    status: "active",
    cpi: "1.05",
    spi: "0.88",
    vac: "-100.5",
    contract_value: "12345.67",
    bac: "50000",
    eac: "51000.5",
    delta_eac: "250.25",
    currency: "EUR",
    at_risk: true,
    ...overrides,
  } as unknown as PortfolioEVMResponse["projects"][number];
}

describe("transformPortfolioNumeric", () => {
  it("coerces Decimal-string summary fields to numbers", () => {
    const data: PortfolioEVMResponse = {
      summary: makeSummary(),
      projects: [],
      at_risk_projects: [],
      control_date: "2026-06-28",
    };

    const out = transformPortfolioNumeric(data);

    expect(out.summary.cpi).toBe(0.75);
    expect(out.summary.spi).toBe(0.9);
    expect(out.summary.bac).toBe(1000);
    expect(out.summary.eac).toBeCloseTo(1333.33, 2);
    expect(out.summary.tcpi).toBeCloseTo(1.36, 2);
    // every declared numeric field is a real number
    expect(typeof out.summary.cpi).toBe("number");
    expect(typeof out.summary.vac).toBe("number");
  });

  it("coerces Decimal-string fields on each project row", () => {
    const project = makeProject();
    const data: PortfolioEVMResponse = {
      summary: makeSummary(),
      projects: [project],
      at_risk_projects: [project],
      control_date: "2026-06-28",
    };

    const out = transformPortfolioNumeric(data);

    expect(out.projects[0].cpi).toBeCloseTo(1.05, 2);
    expect(out.projects[0].contract_value).toBeCloseTo(12345.67, 2);
    expect(out.projects[0].delta_eac).toBeCloseTo(250.25, 2);
    // at_risk_projects is transformed the same way (it's a subset)
    expect(out.at_risk_projects[0].cpi).toBeCloseTo(1.05, 2);
    expect(out.at_risk_projects[0].spi).toBeCloseTo(0.88, 2);
  });

  it("passes null/undefined through untouched", () => {
    const project = makeProject({
      cpi: null,
      spi: undefined,
      eac: null,
      delta_eac: null,
      vac: null,
      contract_value: null,
    });
    const data: PortfolioEVMResponse = {
      summary: makeSummary({ cpi: null, spi: null, vac: null }),
      projects: [project],
      at_risk_projects: [],
      control_date: "2026-06-28",
    };

    const out = transformPortfolioNumeric(data);

    expect(out.summary.cpi).toBeNull();
    expect(out.summary.spi).toBeNull();
    expect(out.summary.vac).toBeNull();
    expect(out.projects[0].cpi).toBeNull();
    expect(out.projects[0].spi).toBeUndefined();
    expect(out.projects[0].eac).toBeNull();
  });

  it("maps an unparseable string to null (NaN → null)", () => {
    const data: PortfolioEVMResponse = {
      summary: makeSummary({ cpi: "not-a-number", spi: "NaN" }),
      projects: [],
      at_risk_projects: [],
      control_date: "2026-06-28",
    };

    const out = transformPortfolioNumeric(data);

    expect(out.summary.cpi).toBeNull();
    expect(out.summary.spi).toBeNull();
  });

  it("leaves already-numeric values as numbers", () => {
    const data: PortfolioEVMResponse = {
      summary: makeSummary({ cpi: 1.1, spi: 0.95, vac: -42 }),
      projects: [],
      at_risk_projects: [],
      control_date: "2026-06-28",
    };

    const out = transformPortfolioNumeric(data);

    expect(out.summary.cpi).toBe(1.1);
    expect(out.summary.spi).toBe(0.95);
    expect(out.summary.vac).toBe(-42);
  });

  it("does not mutate the input (returns new objects)", () => {
    const summary = makeSummary();
    const project = makeProject();
    const data: PortfolioEVMResponse = {
      summary,
      projects: [project],
      at_risk_projects: [project],
      control_date: "2026-06-28",
    };

    const out = transformPortfolioNumeric(data);

    // input objects keep their original (string) values
    expect(data.summary.cpi).toBe("0.75");
    expect(data.projects[0].cpi).toBe("1.05");
    // output is a new structure
    expect(out).not.toBe(data);
    expect(out.summary).not.toBe(data.summary);
    expect(out.projects[0]).not.toBe(data.projects[0]);
  });
});
