import { describe, it, expect } from "vitest";
import type { ChangeOrderStatsResponse } from "@/api/generated/models/ChangeOrderStatsResponse";
import { transformCOStatsNumeric } from "../usePortfolioCO";

/**
 * Cast helper: the generated `ChangeOrderStatsResponse` types the monetary
 * fields as `string`, but the transform deliberately accepts `number | null`
 * too (the backend may emit either, and post-transform the value is a number).
 * Fixtures therefore model the runtime payload, not the narrow generated type.
 */
function makeStats(overrides: Record<string, unknown>): ChangeOrderStatsResponse {
  return { ...overrides } as unknown as ChangeOrderStatsResponse;
}

describe("transformCOStatsNumeric", () => {
  it("coerces Decimal-string monetary fields to numbers", () => {
    const data = makeStats({
      total_count: 12,
      total_cost_exposure: "12345.67",
      pending_value: "5000.5",
      approved_value: "7345.17",
    });

    const out = transformCOStatsNumeric(data);

    expect(out.total_cost_exposure).toBeCloseTo(12345.67, 2);
    expect(out.pending_value).toBeCloseTo(5000.5, 2);
    expect(out.approved_value).toBeCloseTo(7345.17, 2);
    expect(typeof out.total_cost_exposure).toBe("number");
  });

  it("passes already-numeric values through as numbers", () => {
    const data = makeStats({
      total_cost_exposure: 999.5,
      pending_value: 100,
      approved_value: 0,
    });

    const out = transformCOStatsNumeric(data);

    expect(out.total_cost_exposure).toBe(999.5);
    expect(out.pending_value).toBe(100);
    expect(out.approved_value).toBe(0);
  });

  it("maps an unparseable string to null (NaN → null)", () => {
    const data = makeStats({
      total_cost_exposure: "garbage",
      pending_value: "NaN",
      approved_value: "12.34",
    });

    const out = transformCOStatsNumeric(data);

    expect(out.total_cost_exposure).toBeNull();
    expect(out.pending_value).toBeNull();
    expect(out.approved_value).toBeCloseTo(12.34, 2);
  });

  it("preserves null/undefined for the monetary fields", () => {
    const data = makeStats({
      total_cost_exposure: null,
      pending_value: undefined,
      approved_value: undefined,
    });

    const out = transformCOStatsNumeric(data);

    expect(out.total_cost_exposure).toBeNull();
    expect(out.pending_value).toBeUndefined();
    expect(out.approved_value).toBeUndefined();
  });

  it("leaves the nested collections (cost_trend, by_status, ...) untouched", () => {
    const data = makeStats({
      total_cost_exposure: "100",
      cost_trend: [
        // cumulative_value stays a string per the documented contract
        { cumulative_value: "50.5" } as never,
      ],
      by_status: [{ status: "Approved", count: 3, total_value: "100.00" }],
      aging_items: [
        {
          change_order_id: "co-1",
          code: "CO-2026-001",
          title: "Scope add",
          status: "Submitted for Approval",
          days_in_status: 9,
        },
      ],
    });

    const out = transformCOStatsNumeric(data);

    // top-level field coerced
    expect(out.total_cost_exposure).toBe(100);
    // nested structures preserved verbatim (same reference, not transformed)
    expect(out.cost_trend).toBe(data.cost_trend);
    expect(out.by_status).toBe(data.by_status);
    expect(out.aging_items).toBe(data.aging_items);
    expect(out.cost_trend?.[0].cumulative_value).toBe("50.5");
  });

  it("does not mutate the input object", () => {
    const data = makeStats({
      total_cost_exposure: "100",
      pending_value: "50",
      approved_value: "50",
    });

    transformCOStatsNumeric(data);

    expect(data.total_cost_exposure).toBe("100");
    expect(data.pending_value).toBe("50");
    expect(data.approved_value).toBe("50");
  });
});
