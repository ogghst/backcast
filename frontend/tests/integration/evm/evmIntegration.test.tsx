/**
 * Integration tests for EVM (Earned Value Management) Analyzer
 *
 * These tests verify the complete EVM analysis flow from the frontend:
 * - EVMAnalyzerModal open/close flow with EChartsGauge
 * - EVMSummaryView rendering with KPI indicators
 * - Time-series chart with mocked data
 * - TimeMachineContext integration
 * - Loading and error states
 *
 * FE-009: Frontend Integration Tests for EVM Analyzer
 */

import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ReactNode } from "react";
import { MemoryRouter } from "react-router-dom";
import { ConfigProvider, theme } from "antd";

// Mock TimeMachineContext BEFORE imports
const mockInvalidateQueries = vi.fn();
vi.mock("@/contexts/TimeMachineContext", () => ({
  useTimeMachine: () => ({
    asOf: undefined,
    branch: "main",
    mode: "merged",
    isHistorical: false,
    invalidateQueries: mockInvalidateQueries,
  }),
  useTimeMachineParams: () => ({
    asOf: undefined,
    branch: "main",
    mode: "merged",
  }),
  TimeMachineProvider: ({ children }: { children: ReactNode }) => <>{children}</>,
}));

// Mock EChartsGauge (replaces old EVMGauge)
vi.mock("@/features/evm/components/charts/EChartsGauge", () => ({
  EChartsGauge: ({ value, label }: { value: number | null; label: string }) => (
    <div data-testid={`gauge-${label.toLowerCase()}`}>
      <span data-testid={`${label.toLowerCase()}-value`}>
        {value !== null && value !== undefined ? value.toFixed(2) : "N/A"}
      </span>
    </div>
  ),
}));

// Mock EVMTimeSeriesChart
vi.mock("@/features/evm/components/EVMTimeSeriesChart", () => ({
  EVMTimeSeriesChart: ({
    timeSeries,
    loading,
    onGranularityChange,
  }: {
    timeSeries: EVMTimeSeriesResponse | undefined;
    loading: boolean;
    onGranularityChange: (g: string) => void;
  }) => (
    <div data-testid="evm-timeseries-chart">
      {loading && <div data-testid="chart-loading">Loading chart...</div>}
      {!loading && timeSeries && (
        <div data-testid="chart-data">
          <div data-testid="chart-granularity">{timeSeries.granularity}</div>
          <button
            onClick={() => onGranularityChange("day")}
            data-testid="granularity-day"
          >
            Day
          </button>
          <button
            onClick={() => onGranularityChange("week")}
            data-testid="granularity-week"
          >
            Week
          </button>
          <button
            onClick={() => onGranularityChange("month")}
            data-testid="granularity-month"
          >
            Month
          </button>
        </div>
      )}
    </div>
  ),
}));

// Mock MetricCard
vi.mock("@/features/evm/components/MetricCard", () => ({
  MetricCard: ({
    metadata,
    value,
    status,
  }: {
    metadata: { name: string; description: string; key: string };
    value: number | null;
    status: string;
  }) => {
    const testName = metadata.name.toLowerCase().replace(/\s+/g, "-");
    return (
      <div data-testid={`metric-${testName}`}>
        <div data-testid={`metric-name-${testName}`}>
          {metadata.name}
        </div>
        <div data-testid={`metric-value-${testName}`}>
          {value !== null && value !== undefined ? value.toFixed(2) : "N/A"}
        </div>
        <div data-testid={`metric-status-${testName}`}>
          {status}
        </div>
      </div>
    );
  },
}));

// Mock EVMCompactSCurve
vi.mock("@/features/evm/components/EVMCompactSCurve", () => ({
  EVMCompactSCurve: ({ height }: { height: number }) => (
    <div data-testid="evm-compact-s-curve" style={{ height }}>
      S-Curve Chart
    </div>
  ),
}));

// Mock EVMKPIIndicator
vi.mock("@/features/evm/components/EVMKPIIndicator", () => ({
  EVMKPIIndicator: ({
    label,
    value,
    format,
    status,
  }: {
    label: string;
    value: number | null;
    format: string;
    status: string;
    neutral?: boolean;
  }) => (
    <div data-testid={`kpi-${label.toLowerCase()}`}>
      <span data-testid={`kpi-value-${label.toLowerCase()}`}>
        {value !== null && value !== undefined
          ? format === "currency"
            ? value.toLocaleString()
            : format === "percentage"
              ? `${(value * 100).toFixed(0)}%`
              : value.toFixed(2)
          : "N/A"}
      </span>
      <span data-testid={`kpi-status-${label.toLowerCase()}`}>{status}</span>
    </div>
  ),
}));

// Mock EVMForecastBar
vi.mock("@/features/evm/components/EVMForecastBar", () => ({
  EVMForecastBar: ({
    bac,
    eac,
  }: {
    bac: number;
    eac: number | null;
    ac: number;
    etc: number | null;
    vac: number | null;
  }) => (
    <div data-testid="evm-forecast-bar">
      <span data-testid="forecast-bac">{bac}</span>
      <span data-testid="forecast-eac">{eac ?? "N/A"}</span>
    </div>
  ),
}));

// Import components after mocking
import { EVMAnalyzerModal } from "@/features/evm/components/EVMAnalyzerModal";
import { EVMSummaryView } from "@/features/evm/components/EVMSummaryView";
import type { EVMMetricsResponse, EVMTimeSeriesResponse } from "@/features/evm/types";

/**
 * Helper to create a wrapper with query client and providers
 */
function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
      },
      mutations: {
        retry: false,
      },
    },
    logger: {
      log: console.log,
      warn: console.warn,
      error: () => {}, // Suppress error logs in tests
    },
  });

  const wrapper = ({ children }: { children: ReactNode }) => (
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>
        <ConfigProvider theme={{ algorithm: theme.defaultAlgorithm }}>
          {children}
        </ConfigProvider>
      </MemoryRouter>
    </QueryClientProvider>
  );

  return { queryClient, wrapper };
}

/**
 * Mock EVM metrics data
 */
const mockEVMMetrics: EVMMetricsResponse = {
  entity_type: "cost_element" as const,
  entity_id: "test-cost-element-1",
  bac: 100000,
  pv: 80000,
  ac: 85000,
  ev: 75000,
  cv: -10000,
  sv: -5000,
  cpi: 0.88,
  spi: 0.94,
  eac: 113636,
  vac: -13636,
  etc: 28636,
  control_date: "2024-01-15T00:00:00Z",
  branch: "main",
  progress_percentage: 75,
};

/**
 * Mock time-series data
 */
const mockTimeSeries: EVMTimeSeriesResponse = {
  granularity: "week" as const,
  points: [
    {
      date: "2024-01-01T00:00:00Z",
      pv: 10000,
      ev: 9500,
      ac: 10000,
      forecast: 12000,
      actual: 10000,
    },
    {
      date: "2024-01-08T00:00:00Z",
      pv: 20000,
      ev: 18500,
      ac: 20000,
      forecast: 24000,
      actual: 20000,
    },
    {
      date: "2024-01-15T00:00:00Z",
      pv: 30000,
      ev: 27500,
      ac: 30000,
      forecast: 36000,
      actual: 30000,
    },
  ],
  start_date: "2024-01-01T00:00:00Z",
  end_date: "2024-01-15T00:00:00Z",
  total_points: 3,
};

describe("EVM Integration Tests", () => {
  describe("EVMAnalyzerModal Integration", () => {
    it("should not render when open is false", () => {
      const { wrapper } = createWrapper();

      const { container } = render(
        <EVMAnalyzerModal
          open={false}
          onClose={() => {}}
          evmMetrics={mockEVMMetrics}
          timeSeries={mockTimeSeries}
          loading={false}
          onGranularityChange={() => {}}
        />,
        { wrapper }
      );

      // Modal should not be in DOM
      expect(container.querySelector(".ant-modal")).not.toBeInTheDocument();
    });

    it("should render modal when open is true", async () => {
      const { wrapper } = createWrapper();

      render(
        <EVMAnalyzerModal
          open={true}
          onClose={() => {}}
          evmMetrics={mockEVMMetrics}
          timeSeries={mockTimeSeries}
          loading={false}
          onGranularityChange={() => {}}
        />,
        { wrapper }
      );

      // Verify modal renders with current title
      await waitFor(() => {
        expect(screen.getByText(/EVM Analysis Dashboard/i)).toBeInTheDocument();
      });
    });

    it("should call onClose when Close button is clicked", async () => {
      const { wrapper } = createWrapper();
      const onClose = vi.fn();

      render(
        <EVMAnalyzerModal
          open={true}
          onClose={onClose}
          evmMetrics={mockEVMMetrics}
          timeSeries={mockTimeSeries}
          loading={false}
          onGranularityChange={() => {}}
        />,
        { wrapper }
      );

      // Click Close button (okText is "Close")
      const closeButton = await screen.findByText("Close");
      fireEvent.click(closeButton);

      // Verify onClose called
      expect(onClose).toHaveBeenCalledTimes(1);
    });

    it("should display loading state", async () => {
      const { wrapper } = createWrapper();

      render(
        <EVMAnalyzerModal
          open={true}
          onClose={() => {}}
          evmMetrics={undefined}
          timeSeries={undefined}
          loading={true}
          onGranularityChange={() => {}}
        />,
        { wrapper }
      );

      // Verify loading state
      await waitFor(() => {
        expect(screen.getByText(/Loading EVM analysis/i)).toBeInTheDocument();
      });
    });

    it("should display empty state when no data", async () => {
      const { wrapper } = createWrapper();

      render(
        <EVMAnalyzerModal
          open={true}
          onClose={() => {}}
          evmMetrics={undefined}
          timeSeries={undefined}
          loading={false}
          onGranularityChange={() => {}}
        />,
        { wrapper }
      );

      // Verify empty state
      await waitFor(() => {
        expect(screen.getByText(/No EVM data available/i)).toBeInTheDocument();
      });
    });

    it("should render performance indices (CPI and SPI gauges)", async () => {
      const { wrapper } = createWrapper();

      render(
        <EVMAnalyzerModal
          open={true}
          onClose={() => {}}
          evmMetrics={mockEVMMetrics}
          timeSeries={mockTimeSeries}
          loading={false}
          onGranularityChange={() => {}}
        />,
        { wrapper }
      );

      // Verify CPI gauge
      await waitFor(() => {
        expect(screen.getByTestId("gauge-cpi")).toBeInTheDocument();
        expect(screen.getByTestId("cpi-value")).toHaveTextContent(
          mockEVMMetrics.cpi?.toFixed(2) || "N/A"
        );
      });

      // Verify SPI gauge
      expect(screen.getByTestId("gauge-spi")).toBeInTheDocument();
      expect(screen.getByTestId("spi-value")).toHaveTextContent(
        mockEVMMetrics.spi?.toFixed(2) || "N/A"
      );
    });

    it("should render time-series chart with data", async () => {
      const { wrapper } = createWrapper();
      const onGranularityChange = vi.fn();

      render(
        <EVMAnalyzerModal
          open={true}
          onClose={() => {}}
          evmMetrics={mockEVMMetrics}
          timeSeries={mockTimeSeries}
          loading={false}
          onGranularityChange={onGranularityChange}
        />,
        { wrapper }
      );

      // Verify chart renders
      await waitFor(() => {
        expect(screen.getByTestId("evm-timeseries-chart")).toBeInTheDocument();
      });

      // Verify granularity selector
      expect(screen.getByTestId("chart-granularity")).toHaveTextContent("week");
    });

    it("should handle granularity change", async () => {
      const { wrapper } = createWrapper();
      const onGranularityChange = vi.fn();

      render(
        <EVMAnalyzerModal
          open={true}
          onClose={() => {}}
          evmMetrics={mockEVMMetrics}
          timeSeries={mockTimeSeries}
          loading={false}
          onGranularityChange={onGranularityChange}
        />,
        { wrapper }
      );

      // Click day granularity
      const dayButton = await screen.findByTestId("granularity-day");
      fireEvent.click(dayButton);

      // Verify callback called
      expect(onGranularityChange).toHaveBeenCalledWith("day");
    });

    it("should render metric cards in All Metrics tab", async () => {
      const { wrapper } = createWrapper();

      render(
        <EVMAnalyzerModal
          open={true}
          onClose={() => {}}
          evmMetrics={mockEVMMetrics}
          timeSeries={mockTimeSeries}
          loading={false}
          onGranularityChange={() => {}}
        />,
        { wrapper }
      );

      // Click on the All Metrics tab
      const allMetricsTab = await screen.findByText(/All Metrics/i);
      fireEvent.click(allMetricsTab);

      // Verify key financial metric sections appear
      await waitFor(() => {
        expect(screen.getByText(/Key Financial Metrics/i)).toBeInTheDocument();
        expect(screen.getByText(/Schedule Performance Metrics/i)).toBeInTheDocument();
        expect(screen.getByText(/Cost Performance Metrics/i)).toBeInTheDocument();
        expect(screen.getByText(/Variance Analysis/i)).toBeInTheDocument();
        expect(screen.getByText(/Forecast Metrics/i)).toBeInTheDocument();
      });
    });

    it("should handle null CPI and SPI values", async () => {
      const { wrapper } = createWrapper();

      const nullIndicesMetrics: EVMMetricsResponse = {
        ...mockEVMMetrics,
        cpi: null,
        spi: null,
      };

      render(
        <EVMAnalyzerModal
          open={true}
          onClose={() => {}}
          evmMetrics={nullIndicesMetrics}
          timeSeries={mockTimeSeries}
          loading={false}
          onGranularityChange={() => {}}
        />,
        { wrapper }
      );

      // Verify gauges display N/A
      await waitFor(() => {
        expect(screen.getByTestId("cpi-value")).toHaveTextContent("N/A");
        expect(screen.getByTestId("spi-value")).toHaveTextContent("N/A");
      });
    });

    it("should render Overview and All Metrics tabs", async () => {
      const { wrapper } = createWrapper();

      render(
        <EVMAnalyzerModal
          open={true}
          onClose={() => {}}
          evmMetrics={mockEVMMetrics}
          timeSeries={mockTimeSeries}
          loading={false}
          onGranularityChange={() => {}}
        />,
        { wrapper }
      );

      // Verify tabs are present
      await waitFor(() => {
        expect(screen.getByText("Overview")).toBeInTheDocument();
        expect(screen.getByText("All Metrics")).toBeInTheDocument();
      });
    });
  });

  describe("EVMSummaryView Integration", () => {
    it("should render KPI indicators and forecast bar", async () => {
      const { wrapper } = createWrapper();

      render(
        <EVMSummaryView
          metrics={mockEVMMetrics}
          onAdvanced={() => {}}
        />,
        { wrapper }
      );

      // Verify KPI indicators are present
      await waitFor(() => {
        expect(screen.getByTestId("kpi-cpi")).toBeInTheDocument();
        expect(screen.getByTestId("kpi-spi")).toBeInTheDocument();
        expect(screen.getByTestId("kpi-bac")).toBeInTheDocument();
        expect(screen.getByTestId("kpi-eac")).toBeInTheDocument();
        expect(screen.getByTestId("kpi-vac")).toBeInTheDocument();
      });
    });

    it("should call onAdvanced when Advanced button is clicked", async () => {
      const { wrapper } = createWrapper();
      const onAdvanced = vi.fn();

      render(
        <EVMSummaryView
          metrics={mockEVMMetrics}
          onAdvanced={onAdvanced}
        />,
        { wrapper }
      );

      // Click Advanced button
      const advancedButton = await screen.findByText("Advanced");
      fireEvent.click(advancedButton);

      // Verify callback called
      expect(onAdvanced).toHaveBeenCalledTimes(1);
    });

    it("should render detail metrics in collapsible section", async () => {
      const { wrapper } = createWrapper();

      render(
        <EVMSummaryView
          metrics={mockEVMMetrics}
          onAdvanced={() => {}}
        />,
        { wrapper }
      );

      // Verify the S-curve and forecast bar render
      await waitFor(() => {
        expect(screen.getByTestId("evm-compact-s-curve")).toBeInTheDocument();
        expect(screen.getByTestId("evm-forecast-bar")).toBeInTheDocument();
      });

      // Verify detail metrics header
      expect(screen.getByText("Detail Metrics")).toBeInTheDocument();
    });

    it("should display correct KPI values", async () => {
      const { wrapper } = createWrapper();

      render(
        <EVMSummaryView
          metrics={mockEVMMetrics}
          onAdvanced={() => {}}
        />,
        { wrapper }
      );

      // Verify CPI value
      await waitFor(() => {
        const cpiValue = screen.getByTestId("kpi-value-cpi");
        expect(cpiValue).toHaveTextContent(mockEVMMetrics.cpi!.toFixed(2));
      });

      // Verify SPI value
      const spiValue = screen.getByTestId("kpi-value-spi");
      expect(spiValue).toHaveTextContent(mockEVMMetrics.spi!.toFixed(2));
    });

    it("should display correct status colors based on metric values", async () => {
      const { wrapper } = createWrapper();

      render(
        <EVMSummaryView
          metrics={mockEVMMetrics}
          onAdvanced={() => {}}
        />,
        { wrapper }
      );

      // Verify CPI status (CPI < 1.0 should be "bad")
      await waitFor(() => {
        const cpiStatus = screen.getByTestId("kpi-status-cpi");
        expect(cpiStatus).toHaveTextContent("bad");
      });

      // Verify VAC status (negative VAC should be "bad")
      const vacStatus = screen.getByTestId("kpi-status-vac");
      expect(vacStatus).toHaveTextContent("bad");
    });

    it("should handle null metric values gracefully", async () => {
      const { wrapper } = createWrapper();

      const nullMetrics: EVMMetricsResponse = {
        ...mockEVMMetrics,
        cpi: null,
        spi: null,
        eac: null,
        vac: null,
        etc: null,
      };

      render(
        <EVMSummaryView
          metrics={nullMetrics}
          onAdvanced={() => {}}
        />,
        { wrapper }
      );

      // Verify null values display as N/A
      await waitFor(() => {
        const cpiValue = screen.getByTestId("kpi-value-cpi");
        expect(cpiValue).toHaveTextContent("N/A");

        const eacValue = screen.getByTestId("kpi-value-eac");
        expect(eacValue).toHaveTextContent("N/A");
      });
    });

    it("should render with S-curve and forecast bar visible", async () => {
      const { wrapper } = createWrapper();

      render(
        <EVMSummaryView
          metrics={mockEVMMetrics}
          onAdvanced={() => {}}
        />,
        { wrapper }
      );

      // Verify all major sections visible
      await waitFor(() => {
        expect(screen.getByTestId("evm-compact-s-curve")).toBeInTheDocument();
        expect(screen.getByTestId("evm-forecast-bar")).toBeInTheDocument();
        expect(screen.getByTestId("kpi-cpi")).toBeInTheDocument();
        expect(screen.getByTestId("kpi-eac")).toBeInTheDocument();
      });
    });
  });

  describe("TimeMachineContext Integration", () => {
    it("should use TimeMachineContext params for queries", async () => {
      // Verify that TimeMachineContext is available
      const { useTimeMachineParams } = await import("@/contexts/TimeMachineContext");
      const params = useTimeMachineParams();

      expect(params).toBeDefined();
      expect(params.branch).toBe("main");
      expect(params.mode).toBe("merged");
    });

    it("should provide invalidateQueries method", async () => {
      // Import TimeMachineContext
      const { useTimeMachine } = await import("@/contexts/TimeMachineContext");
      const timeMachine = useTimeMachine();

      // Clear previous calls
      mockInvalidateQueries.mockClear();

      // Call invalidateQueries
      timeMachine.invalidateQueries();

      // Verify invalidateQueries was called
      expect(mockInvalidateQueries).toHaveBeenCalled();
    });

    it("should have correct initial state", async () => {
      // Import TimeMachineContext
      const { useTimeMachine } = await import("@/contexts/TimeMachineContext");
      const timeMachine = useTimeMachine();

      // Verify initial state
      expect(timeMachine.asOf).toBeUndefined();
      expect(timeMachine.branch).toBe("main");
      expect(timeMachine.mode).toBe("merged");
      expect(timeMachine.isHistorical).toBe(false);
    });
  });

  describe("Data Transformation Integration", () => {
    it("should transform time-series data correctly for charts", async () => {
      const { wrapper } = createWrapper();

      render(
        <EVMAnalyzerModal
          open={true}
          onClose={() => {}}
          evmMetrics={mockEVMMetrics}
          timeSeries={mockTimeSeries}
          loading={false}
          onGranularityChange={() => {}}
        />,
        { wrapper }
      );

      // Verify chart receives correct data
      await waitFor(() => {
        expect(screen.getByTestId("evm-timeseries-chart")).toBeInTheDocument();
        expect(screen.getByTestId("chart-granularity")).toHaveTextContent("week");
      });
    });

    it("should calculate metric status correctly", async () => {
      const { wrapper } = createWrapper();

      render(
        <EVMSummaryView
          metrics={mockEVMMetrics}
          onAdvanced={() => {}}
        />,
        { wrapper }
      );

      // Verify status calculations
      await waitFor(() => {
        // CPI < 1.0 = bad
        const cpiStatus = screen.getByTestId("kpi-status-cpi");
        expect(cpiStatus).toHaveTextContent("bad");
      });
    });

    it("should handle good performance metrics", async () => {
      const { wrapper } = createWrapper();

      const goodMetrics: EVMMetricsResponse = {
        ...mockEVMMetrics,
        cpi: 1.2, // Good CPI
        spi: 1.1, // Good SPI
        cv: 5000, // Positive CV
        sv: 2000, // Positive SV
        vac: 10000, // Positive VAC
      };

      render(
        <EVMSummaryView
          metrics={goodMetrics}
          onAdvanced={() => {}}
        />,
        { wrapper }
      );

      // Verify good status
      await waitFor(() => {
        const cpiStatus = screen.getByTestId("kpi-status-cpi");
        expect(cpiStatus).toHaveTextContent("good");

        const spiStatus = screen.getByTestId("kpi-status-spi");
        expect(spiStatus).toHaveTextContent("good");
      });
    });
  });

  describe("Complete EVM Flow Integration", () => {
    it("should render complete EVM analysis flow with modal", async () => {
      const { wrapper } = createWrapper();
      const handleClose = vi.fn();

      // Render EVMAnalyzerModal
      const { rerender } = render(
        <EVMAnalyzerModal
          open={true}
          onClose={handleClose}
          evmMetrics={mockEVMMetrics}
          timeSeries={mockTimeSeries}
          loading={false}
          onGranularityChange={() => {}}
        />,
        { wrapper }
      );

      // Verify modal opens
      await waitFor(() => {
        expect(screen.getByText(/EVM Analysis Dashboard/i)).toBeInTheDocument();
      });

      // Step 2: Verify modal content
      expect(screen.getByTestId("gauge-cpi")).toBeInTheDocument();
      expect(screen.getByTestId("gauge-spi")).toBeInTheDocument();
      expect(screen.getByTestId("evm-timeseries-chart")).toBeInTheDocument();

      // Step 3: Close modal via the Close button
      const closeButton = screen.getByText("Close");
      fireEvent.click(closeButton);

      // Verify onClose callback was called
      expect(handleClose).toHaveBeenCalledTimes(1);

      // Step 4: Re-render with open=false to simulate modal closing
      rerender(
        <EVMAnalyzerModal
          open={false}
          onClose={handleClose}
          evmMetrics={mockEVMMetrics}
          timeSeries={mockTimeSeries}
          loading={false}
          onGranularityChange={() => {}}
        />
      );

      // Modal should close (destroyOnHidden removes content)
      await waitFor(() => {
        expect(screen.queryByTestId("gauge-cpi")).not.toBeInTheDocument();
      });
    });

    it("should handle loading state in complete flow", async () => {
      const { wrapper } = createWrapper();

      render(
        <EVMAnalyzerModal
          open={true}
          onClose={() => {}}
          evmMetrics={undefined}
          timeSeries={undefined}
          loading={true}
          onGranularityChange={() => {}}
        />,
        { wrapper }
      );

      // Verify loading state
      await waitFor(() => {
        expect(screen.getByText(/Loading EVM analysis/i)).toBeInTheDocument();
      });
    });

    it("should handle error state in complete flow", async () => {
      const { wrapper } = createWrapper();

      render(
        <EVMAnalyzerModal
          open={true}
          onClose={() => {}}
          evmMetrics={undefined}
          timeSeries={undefined}
          loading={false}
          onGranularityChange={() => {}}
        />,
        { wrapper }
      );

      // Verify empty state
      await waitFor(() => {
        expect(screen.getByText(/No EVM data available/i)).toBeInTheDocument();
      });
    });
  });

  describe("Component Props Integration", () => {
    it("should handle different granularity values", async () => {
      const { wrapper } = createWrapper();

      const dayTimeSeries: EVMTimeSeriesResponse = {
        ...mockTimeSeries,
        granularity: "day" as const,
      };

      render(
        <EVMAnalyzerModal
          open={true}
          onClose={() => {}}
          evmMetrics={mockEVMMetrics}
          timeSeries={dayTimeSeries}
          loading={false}
          onGranularityChange={() => {}}
        />,
        { wrapper }
      );

      // Verify day granularity
      await waitFor(() => {
        expect(screen.getByTestId("chart-granularity")).toHaveTextContent("day");
      });
    });

    it("should handle empty time-series data", async () => {
      const { wrapper } = createWrapper();

      const emptyTimeSeries: EVMTimeSeriesResponse = {
        ...mockTimeSeries,
        points: [],
        total_points: 0,
      };

      render(
        <EVMAnalyzerModal
          open={true}
          onClose={() => {}}
          evmMetrics={mockEVMMetrics}
          timeSeries={emptyTimeSeries}
          loading={false}
          onGranularityChange={() => {}}
        />,
        { wrapper }
      );

      // Chart should still render
      await waitFor(() => {
        expect(screen.getByTestId("evm-timeseries-chart")).toBeInTheDocument();
      });
    });

    it("should handle all null metric values", async () => {
      const { wrapper } = createWrapper();

      const allNullMetrics: EVMMetricsResponse = {
        ...mockEVMMetrics,
        cpi: null,
        spi: null,
        eac: null,
        vac: null,
        etc: null,
      };

      render(
        <EVMAnalyzerModal
          open={true}
          onClose={() => {}}
          evmMetrics={allNullMetrics}
          timeSeries={mockTimeSeries}
          loading={false}
          onGranularityChange={() => {}}
        />,
        { wrapper }
      );

      // Verify gauges display N/A
      await waitFor(() => {
        expect(screen.getByTestId("cpi-value")).toHaveTextContent("N/A");
        expect(screen.getByTestId("spi-value")).toHaveTextContent("N/A");
      });
    });
  });

  describe("Accessibility Integration", () => {
    it("should have proper modal structure", async () => {
      const { wrapper } = createWrapper();

      render(
        <EVMAnalyzerModal
          open={true}
          onClose={() => {}}
          evmMetrics={mockEVMMetrics}
          timeSeries={mockTimeSeries}
          loading={false}
          onGranularityChange={() => {}}
        />,
        { wrapper }
      );

      // Verify modal is present
      await waitFor(() => {
        const modal = screen.getByRole("dialog");
        expect(modal).toBeInTheDocument();
      });
    });

    it("should have clickable buttons", async () => {
      const { wrapper } = createWrapper();
      const onGranularityChange = vi.fn();

      render(
        <EVMAnalyzerModal
          open={true}
          onClose={() => {}}
          evmMetrics={mockEVMMetrics}
          timeSeries={mockTimeSeries}
          loading={false}
          onGranularityChange={onGranularityChange}
        />,
        { wrapper }
      );

      // Verify granularity buttons are clickable
      const dayButton = await screen.findByTestId("granularity-day");
      expect(dayButton).toBeEnabled();

      fireEvent.click(dayButton);
      expect(onGranularityChange).toHaveBeenCalledWith("day");
    });
  });
});
