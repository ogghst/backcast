// @ts-nocheck — test file uses mock data that does not match full generated types
import { renderHook } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import type { ReactNode } from "react";
import { useImpactLevelConfig } from "./useImpactLevelConfig";
import type { WorkflowConfigResponse } from "../api/useWorkflowConfig";

// ---------------------------------------------------------------------------
// Mock the API hooks so we control the query results
// ---------------------------------------------------------------------------

const mockUseGlobalConfig = vi.fn();
const mockUseProjectConfig = vi.fn();

vi.mock("../api/useWorkflowConfig", () => ({
  useGlobalConfig: (...args: unknown[]) => mockUseGlobalConfig(...args),
  useProjectConfig: (...args: unknown[]) => mockUseProjectConfig(...args),
}));

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return function Wrapper({ children }: { children: ReactNode }) {
    return (
      <QueryClientProvider client={queryClient}>
        {children}
      </QueryClientProvider>
    );
  };
}

function makeConfig(
  overrides?: Partial<WorkflowConfigResponse>,
): WorkflowConfigResponse {
  return {
    id: "cfg-1",
    config_id: "cfg-uuid-1",
    project_id: null,
    is_active: true,
    version: 1,
    created_by: "admin",
    updated_by: null,
    created_at: "2026-01-01T00:00:00Z",
    updated_at: "2026-01-01T00:00:00Z",
    impact_levels: [
      {
        level_name: "LOW",
        level_order: 1,
        threshold_amount: 10000,
        score_threshold_min: 0,
        score_threshold_max: 25,
        is_active: true,
      },
      {
        level_name: "MEDIUM",
        level_order: 2,
        threshold_amount: 50000,
        score_threshold_min: 25,
        score_threshold_max: 50,
        is_active: true,
      },
      {
        level_name: "HIGH",
        level_order: 3,
        threshold_amount: 100000,
        score_threshold_min: 50,
        score_threshold_max: 75,
        is_active: true,
      },
      {
        level_name: "CRITICAL",
        level_order: 4,
        threshold_amount: 999999999,
        score_threshold_min: 75,
        score_threshold_max: 100,
        is_active: true,
      },
    ],
    approval_rules: [
      { impact_level_name: "LOW", required_authority_level: "LOW", approver_role: "editor_pm" },
      { impact_level_name: "MEDIUM", required_authority_level: "MEDIUM", approver_role: "dept_head" },
      { impact_level_name: "HIGH", required_authority_level: "HIGH", approver_role: "director" },
      { impact_level_name: "CRITICAL", required_authority_level: "CRITICAL", approver_role: "admin" },
    ],
    sla_rules: [
      { impact_level_name: "LOW", business_days: 2, escalation_trigger_pct: 80 },
      { impact_level_name: "MEDIUM", business_days: 5, escalation_trigger_pct: 75 },
      { impact_level_name: "HIGH", business_days: 10, escalation_trigger_pct: 70 },
      { impact_level_name: "CRITICAL", business_days: 15, escalation_trigger_pct: 60 },
    ],
    impact_weights: { budget: 0.4, schedule: 0.3, revenue: 0.2, evm: 0.1 },
    score_boundaries: { LOW: 25, MEDIUM: 50, HIGH: 75, CRITICAL: 100 },
    holiday_country_code: null,
    ...overrides,
  };
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe("useImpactLevelConfig", () => {
  beforeEach(() => {
    vi.clearAllMocks();

    // Default: global config is loading (no data yet)
    mockUseGlobalConfig.mockReturnValue({ data: undefined, isLoading: true });
    mockUseProjectConfig.mockReturnValue({ data: undefined, isLoading: false });
  });

  // -------------------------------------------------------------------------
  // 1. Fallback values while loading
  // -------------------------------------------------------------------------

  it("returns fallback defaults when config is loading", () => {
    const { result } = renderHook(() => useImpactLevelConfig(), {
      wrapper: createWrapper(),
    });

    // isLoading should be true since global query reports loading
    expect(result.current.isLoading).toBe(true);

    // Fallback colors should be present
    expect(result.current.impactColors).toEqual({
      LOW: "#52c41a",
      MEDIUM: "#faad14",
      HIGH: "#fa8c16",
      CRITICAL: "#ff4d4f",
      Unassigned: "#8c8c8c",
    });

    // Fallback tag colors
    expect(result.current.impactTagColors).toEqual({
      LOW: "green",
      MEDIUM: "gold",
      HIGH: "orange",
      CRITICAL: "red",
    });

    // Fallback authority levels
    expect(result.current.authorityLevels).toEqual([
      "LOW",
      "MEDIUM",
      "HIGH",
      "CRITICAL",
    ]);

    // No SLA info when no config
    expect(result.current.slaInfo).toEqual({});
  });

  // -------------------------------------------------------------------------
  // 2. Config-driven values when data is available
  // -------------------------------------------------------------------------

  it("returns config-driven values when global config is fetched", () => {
    const config = makeConfig();
    mockUseGlobalConfig.mockReturnValue({ data: config, isLoading: false });

    const { result } = renderHook(() => useImpactLevelConfig(), {
      wrapper: createWrapper(),
    });

    expect(result.current.isLoading).toBe(false);

    // impactColors derived from config levels (uses fallback hex values)
    expect(result.current.impactColors).toEqual({
      LOW: "#52c41a",
      MEDIUM: "#faad14",
      HIGH: "#fa8c16",
      CRITICAL: "#ff4d4f",
    });

    // SLA info derived from config sla_rules
    expect(result.current.slaInfo).toEqual({
      LOW: { businessDays: 2, escalationPct: 80 },
      MEDIUM: { businessDays: 5, escalationPct: 75 },
      HIGH: { businessDays: 10, escalationPct: 70 },
      CRITICAL: { businessDays: 15, escalationPct: 60 },
    });

    // Authority levels derived and ordered by level_order
    expect(result.current.authorityLevels).toEqual([
      "LOW",
      "MEDIUM",
      "HIGH",
      "CRITICAL",
    ]);
  });

  // -------------------------------------------------------------------------
  // 3. getImpactLevelStyle returns correct style per level
  // -------------------------------------------------------------------------

  it("getImpactLevelStyle returns correct style for each impact level", () => {
    const config = makeConfig();
    mockUseGlobalConfig.mockReturnValue({ data: config, isLoading: false });

    const { result } = renderHook(() => useImpactLevelConfig(), {
      wrapper: createWrapper(),
    });

    const { getImpactLevelStyle } = result.current;

    expect(getImpactLevelStyle("LOW")).toEqual({
      color: "success",
      label: "Low Impact",
    });
    expect(getImpactLevelStyle("MEDIUM")).toEqual({
      color: "warning",
      label: "Medium Impact",
    });
    expect(getImpactLevelStyle("HIGH")).toEqual({
      color: "error",
      label: "High Impact",
    });
    expect(getImpactLevelStyle("CRITICAL")).toEqual({
      color: "purple",
      label: "Critical Impact",
    });
  });

  it("getImpactLevelStyle returns Not Assessed for unknown or null level", () => {
    mockUseGlobalConfig.mockReturnValue({
      data: makeConfig(),
      isLoading: false,
    });

    const { result } = renderHook(() => useImpactLevelConfig(), {
      wrapper: createWrapper(),
    });

    const { getImpactLevelStyle } = result.current;

    expect(getImpactLevelStyle(null)).toEqual({
      color: "default",
      label: "Not Assessed",
    });
    expect(getImpactLevelStyle("UNKNOWN")).toEqual({
      color: "default",
      label: "Not Assessed",
    });
  });

  // -------------------------------------------------------------------------
  // 4. Authority levels populated from config
  // -------------------------------------------------------------------------

  it("authorityLevels respects custom level_order from config", () => {
    // Reverse the level_order to verify ordering is config-driven
    const config = makeConfig({
      impact_levels: [
        {
          level_name: "CRITICAL",
          level_order: 1,
          threshold_amount: 999999999,
          score_threshold_min: 75,
          score_threshold_max: 100,
          is_active: true,
        },
        {
          level_name: "HIGH",
          level_order: 2,
          threshold_amount: 100000,
          score_threshold_min: 50,
          score_threshold_max: 75,
          is_active: true,
        },
        {
          level_name: "MEDIUM",
          level_order: 3,
          threshold_amount: 50000,
          score_threshold_min: 25,
          score_threshold_max: 50,
          is_active: true,
        },
        {
          level_name: "LOW",
          level_order: 4,
          threshold_amount: 10000,
          score_threshold_min: 0,
          score_threshold_max: 25,
          is_active: true,
        },
      ],
    });
    mockUseGlobalConfig.mockReturnValue({ data: config, isLoading: false });

    const { result } = renderHook(() => useImpactLevelConfig(), {
      wrapper: createWrapper(),
    });

    // Should be ordered by level_order (ascending), not alphabetical
    expect(result.current.authorityLevels).toEqual([
      "CRITICAL",
      "HIGH",
      "MEDIUM",
      "LOW",
    ]);
  });
});
