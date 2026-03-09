/**
 * Tests for ProjectEVMAnalysis page component
 *
 * Test IDs from plan:
 * - T-002: test_project_evm_analysis_renders_summary_view
 * - T-003: test_project_evm_analysis_granularity_selection
 * - T-004: test_project_evm_analysis_opens_modal
 * - T-005: test_project_evm_analysis_calls_hooks_with_project_type
 * - T-006: test_project_evm_analysis_shows_loading_state
 * - T-007: test_project_evm_analysis_handles_missing_project_id
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import React from "react";

import { ProjectEVMAnalysis } from "./ProjectEVMAnalysis";

// Import the mocked hooks
import { useEVMMetrics, useEVMTimeSeries } from "@/features/evm/api/useEVMMetrics";
vi.mock("@/features/evm/api/useEVMMetrics", () => ({
  useEVMMetrics: vi.fn(),
  useEVMTimeSeries: vi.fn(),
}));

// Type alias for the mocked hooks
type MockedUseEVMMetrics = {
  data: {
    entity_type: string;
    entity_id: string;
    bac: number;
    pv: number;
    ac: number;
    ev: number;
    cv: number;
    sv: number;
    cpi: number;
    spi: number;
    eac: number;
    vac: number;
    etc: number;
    control_date: string;
    branch: string;
  } | undefined;
  isLoading: boolean;
  isError: boolean;
};

type MockedUseEVMTimeSeries = {
  data: {
    granularity: string;
    points: Array<{
      date: string;
      pv: number;
      ev: number;
      ac: number;
      forecast: number;
      actual: number;
      cpi: number;
      spi: number;
    }>;
    start_date: string;
    end_date: string;
    total_points: number;
  } | undefined;
  isLoading: boolean;
  isError: boolean;
};

// Mock ECharts to avoid canvas issues in tests
vi.mock("echarts-for-react", () => ({
  default: () => null,
}));

// Mock antd theme
vi.mock("antd", async () => {
  const actual = await vi.importActual("antd");
  return {
    ...actual,
    theme: {
      useToken: () => ({
        token: {
          colorBgContainer: "#ffffff",
          colorBorder: "#d9d9d9",
          borderRadiusLG: 8,
        },
      }),
    },
  };
});

// Test query client for each test
let queryClient: QueryClient;

const createWrapper = () => {
  return ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={queryClient}>
      {children}
    </QueryClientProvider>
  );
};

// Mock EVM metrics data
const mockMetrics = {
  entity_type: "project",
  entity_id: "proj-123",
  bac: 1000000,
  pv: 800000,
  ac: 750000,
  ev: 720000,
  cv: -30000,
  sv: -80000,
  cpi: 0.96,
  spi: 0.9,
  eac: 1041667,
  vac: -41667,
  etc: 291667,
  control_date: "2025-01-15T10:00:00Z",
  branch: "main",
};

// Mock time series data
const mockTimeSeries = {
  granularity: "week",
  points: [
    {
      date: "2024-01-01T00:00:00Z",
      pv: 100000,
      ev: 95000,
      ac: 92000,
      forecast: 1000000,
      actual: 92000,
      cpi: 1.03,
      spi: 0.95,
    },
  ],
  start_date: "2024-01-01T00:00:00Z",
  end_date: "2024-03-31T00:00:00Z",
  total_points: 1,
};

describe("ProjectEVMAnalysis", () => {
  beforeEach(() => {
    queryClient = new QueryClient({
      defaultOptions: {
        queries: {
          retry: false,
        },
      },
    });
    vi.clearAllMocks();
  });

  /**
   * T-002: test_project_evm_analysis_renders_summary_view
   */
  it("test_project_evm_analysis_renders_summary_view", () => {
    // Arrange
    vi.mocked(useEVMMetrics).mockReturnValue({
      data: mockMetrics,
      isLoading: false,
      isError: false,
    } as MockedUseEVMMetrics);
    vi.mocked(useEVMTimeSeries).mockReturnValue({
      data: mockTimeSeries,
      isLoading: false,
      isError: false,
    } as MockedUseEVMTimeSeries);

    // Act
    render(
      <MemoryRouter initialEntries={["/projects/proj-123/evm-analysis"]}>
        <Routes>
          <Route
            path="/projects/:projectId/evm-analysis"
            element={<ProjectEVMAnalysis />}
          />
        </Routes>
      </MemoryRouter>,
      { wrapper: createWrapper() }
    );

    // Assert - Page title renders
    expect(screen.getByText("EVM Analysis")).toBeInTheDocument();
  });

  /**
   * T-006: test_project_evm_analysis_shows_loading_state
   */
  it("test_project_evm_analysis_shows_loading_state", () => {
    // Arrange
    vi.mocked(useEVMMetrics).mockReturnValue({
      data: undefined,
      isLoading: true,
      isError: false,
    } as MockedUseEVMMetrics);
    vi.mocked(useEVMTimeSeries).mockReturnValue({
      data: undefined,
      isLoading: true,
      isError: false,
    } as MockedUseEVMTimeSeries);

    // Act
    render(
      <MemoryRouter initialEntries={["/projects/proj-123/evm-analysis"]}>
        <Routes>
          <Route
            path="/projects/:projectId/evm-analysis"
            element={<ProjectEVMAnalysis />}
          />
        </Routes>
      </MemoryRouter>,
      { wrapper: createWrapper() }
    );

    // Assert - Loading spinner should be visible
    expect(screen.getByRole("status")).toBeInTheDocument();
  });

  /**
   * T-007: test_project_evm_analysis_handles_missing_project_id
   */
  it("test_project_evm_analysis_handles_missing_project_id", () => {
    // Arrange
    vi.mocked(useEVMMetrics).mockReturnValue({
      data: undefined,
      isLoading: false,
      isError: false,
    } as MockedUseEVMMetrics);
    vi.mocked(useEVMTimeSeries).mockReturnValue({
      data: undefined,
      isLoading: false,
      isError: false,
    } as MockedUseEVMTimeSeries);

    // Act & Assert - Should not throw error
    expect(() => {
      render(
        <MemoryRouter initialEntries={["/projects/undefined/evm-analysis"]}>
          <Routes>
            <Route
              path="/projects/:projectId/evm-analysis"
              element={<ProjectEVMAnalysis />}
            />
          </Routes>
        </MemoryRouter>,
        { wrapper: createWrapper() }
      );
    }).not.toThrow();
  });
});
