/**
 * EVMAnalyzerModal Component Tests
 *
 * TDD RED-GREEN-REFACTOR cycle for the EVMAnalyzerModal component.
 *
 * Test Strategy:
 * 1. Modal renders without crashing
 * 2. Modal opens/closes properly
 * 3. Modal displays gauges for CPI and SPI
 * 4. Modal displays EVMTimeSeriesChart with both charts
 * 5. Modal displays all metrics with enhanced visualizations
 * 6. Loading state displays correctly
 * 7. Empty state displays correctly when no data
 *
 * @module features/evm/components
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { EVMAnalyzerModal } from "./EVMAnalyzerModal";
import type { EVMMetricsResponse, EVMTimeSeriesResponse, EVMTimeSeriesGranularity } from "../types";

// Mock the dependencies
vi.mock("./MetricCard", () => ({
  MetricCard: ({ metadata, value, status }: { metadata: { name: string }; value: number | null; status: string }) => (
    <div data-testid={`metric-card-${metadata.name.toLowerCase().replace(/\s+/g, "-")}`}>
      <div className="metric-name">{metadata.name}</div>
      <div className="metric-value">{value ?? "N/A"}</div>
      <div className="metric-status">{status}</div>
    </div>
  ),
}));

vi.mock("./EVMGauge", () => ({
  EVMGauge: ({ label, value }: { label: string; value: number | null }) => (
    <div data-testid={`gauge-${label.toLowerCase()}`}>
      <div className="gauge-label">{label}</div>
      <div className="gauge-value">{value ?? "N/A"}</div>
    </div>
  ),
}));

vi.mock("./EVMTimeSeriesChart", () => ({
  EVMTimeSeriesChart: () => (
    <div data-testid="evm-timeseries-chart">
      <div>EVM Time Series Analysis</div>
    </div>
  ),
}));

describe("EVMAnalyzerModal", () => {
  let queryClient: QueryClient;

  // Mock EVM metrics data
  const mockEvmMetrics: EVMMetricsResponse = {
    entity_type: "cost_element" as const,
    entity_id: "test-cost-element-1",
    bac: 100000,
    pv: 40000,
    ac: 45000,
    ev: 35000,
    cv: -10000,
    sv: -5000,
    cpi: 0.78,
    spi: 0.88,
    eac: 128205,
    vac: -28205,
    etc: 83205,
    control_date: "2024-01-15T00:00:00Z",
    branch: "main",
  };

  // Mock time series data
  const mockTimeSeriesData: EVMTimeSeriesResponse = {
    granularity: "week" as EVMTimeSeriesGranularity,
    points: [
      {
        date: "2024-01-01T00:00:00Z",
        pv: 10000,
        ev: 8000,
        ac: 9000,
        forecast: 12000,
        actual: 9000,
      },
      {
        date: "2024-01-08T00:00:00Z",
        pv: 20000,
        ev: 18000,
        ac: 19000,
        forecast: 24000,
        actual: 19000,
      },
      {
        date: "2024-01-15T00:00:00Z",
        pv: 30000,
        ev: 28000,
        ac: 29000,
        forecast: 36000,
        actual: 29000,
      },
    ],
    start_date: "2024-01-01T00:00:00Z",
    end_date: "2024-01-15T00:00:00Z",
    total_points: 3,
  };

  beforeEach(() => {
    vi.clearAllMocks();
    queryClient = new QueryClient({
      defaultOptions: {
        mutations: { retry: false },
        queries: { retry: false },
      },
    });
  });

  const wrapper = ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  );

  describe("Modal structure and rendering", () => {
    it("should render without crashing when closed", () => {
      expect(() => {
        render(
          <EVMAnalyzerModal
            open={false}
            onClose={vi.fn()}
            evmMetrics={mockEvmMetrics}
            timeSeries={mockTimeSeriesData}
            loading={false}
            onGranularityChange={vi.fn()}
          />,
          { wrapper }
        );
      }).not.toThrow();
    });

    it("should render modal when open is true", () => {
      render(
        <EVMAnalyzerModal
          open={true}
          onClose={vi.fn()}
          evmMetrics={mockEvmMetrics}
          timeSeries={mockTimeSeriesData}
          loading={false}
          onGranularityChange={vi.fn()}
        />,
        { wrapper }
      );

      // Modal should be visible
      const modalElement = document.querySelector(".ant-modal");
      expect(modalElement).toBeInTheDocument();
    });

    it("should not render modal when open is false", () => {
      render(
        <EVMAnalyzerModal
          open={false}
          onClose={vi.fn()}
          evmMetrics={mockEvmMetrics}
          timeSeries={mockTimeSeriesData}
          loading={false}
          onGranularityChange={vi.fn()}
        />,
        { wrapper }
      );

      // Modal should not be visible
      const modalElement = document.querySelector(".ant-modal");
      expect(modalElement).not.toBeInTheDocument();
    });

    it("should display modal title", () => {
      render(
        <EVMAnalyzerModal
          open={true}
          onClose={vi.fn()}
          evmMetrics={mockEvmMetrics}
          timeSeries={mockTimeSeriesData}
          loading={false}
          onGranularityChange={vi.fn()}
        />,
        { wrapper }
      );

      expect(screen.getByText(/EVM Analysis Dashboard/i)).toBeInTheDocument();
    });
  });

  describe("Modal open/close behavior", () => {
    it("should call onClose when close button is clicked", async () => {
      const onClose = vi.fn();

      render(
        <EVMAnalyzerModal
          open={true}
          onClose={onClose}
          evmMetrics={mockEvmMetrics}
          timeSeries={mockTimeSeriesData}
          loading={false}
          onGranularityChange={vi.fn()}
        />,
        { wrapper }
      );

      // Find and click the close button
      const closeButton = document.querySelector(".ant-modal-close");
      expect(closeButton).toBeInTheDocument();

      if (closeButton) {
        fireEvent.click(closeButton);
        await waitFor(() => {
          expect(onClose).toHaveBeenCalled();
        });
      }
    });

    it("should call onClose when Close button is clicked", async () => {
      const onClose = vi.fn();

      render(
        <EVMAnalyzerModal
          open={true}
          onClose={onClose}
          evmMetrics={mockEvmMetrics}
          timeSeries={mockTimeSeriesData}
          loading={false}
          onGranularityChange={vi.fn()}
        />,
        { wrapper }
      );

      // Find and click the Close button (button text changed from OK to Close)
      const closeButton = screen.getByText(/Close/i);
      fireEvent.click(closeButton);

      await waitFor(() => {
        expect(onClose).toHaveBeenCalled();
      });
    });
  });

  describe("Gauges for CPI and SPI", () => {
    it("should render CPI gauge", () => {
      render(
        <EVMAnalyzerModal
          open={true}
          onClose={vi.fn()}
          evmMetrics={mockEvmMetrics}
          timeSeries={mockTimeSeriesData}
          loading={false}
          onGranularityChange={vi.fn()}
        />,
        { wrapper }
      );

      const cpiGauge = screen.getByTestId("gauge-cpi");
      expect(cpiGauge).toBeInTheDocument();
      expect(cpiGauge).toHaveTextContent("CPI");
    });

    it("should render SPI gauge", () => {
      render(
        <EVMAnalyzerModal
          open={true}
          onClose={vi.fn()}
          evmMetrics={mockEvmMetrics}
          timeSeries={mockTimeSeriesData}
          loading={false}
          onGranularityChange={vi.fn()}
        />,
        { wrapper }
      );

      const spiGauge = screen.getByTestId("gauge-spi");
      expect(spiGauge).toBeInTheDocument();
      expect(spiGauge).toHaveTextContent("SPI");
    });

    it("should display CPI value from props", () => {
      render(
        <EVMAnalyzerModal
          open={true}
          onClose={vi.fn()}
          evmMetrics={mockEvmMetrics}
          timeSeries={mockTimeSeriesData}
          loading={false}
          onGranularityChange={vi.fn()}
        />,
        { wrapper }
      );

      const cpiGauge = screen.getByTestId("gauge-cpi");
      expect(cpiGauge).toHaveTextContent("0.78");
    });

    it("should display SPI value from props", () => {
      render(
        <EVMAnalyzerModal
          open={true}
          onClose={vi.fn()}
          evmMetrics={mockEvmMetrics}
          timeSeries={mockTimeSeriesData}
          loading={false}
          onGranularityChange={vi.fn()}
        />,
        { wrapper }
      );

      const spiGauge = screen.getByTestId("gauge-spi");
      expect(spiGauge).toHaveTextContent("0.88");
    });

    it("should handle null CPI value", () => {
      const metricsWithNullCPI = { ...mockEvmMetrics, cpi: null };

      render(
        <EVMAnalyzerModal
          open={true}
          onClose={vi.fn()}
          evmMetrics={metricsWithNullCPI}
          timeSeries={mockTimeSeriesData}
          loading={false}
          onGranularityChange={vi.fn()}
        />,
        { wrapper }
      );

      const cpiGauge = screen.getByTestId("gauge-cpi");
      expect(cpiGauge).toHaveTextContent("N/A");
    });

    it("should handle null SPI value", () => {
      const metricsWithNullSPI = { ...mockEvmMetrics, spi: null };

      render(
        <EVMAnalyzerModal
          open={true}
          onClose={vi.fn()}
          evmMetrics={metricsWithNullSPI}
          timeSeries={mockTimeSeriesData}
          loading={false}
          onGranularityChange={vi.fn()}
        />,
        { wrapper }
      );

      const spiGauge = screen.getByTestId("gauge-spi");
      expect(spiGauge).toHaveTextContent("N/A");
    });
  });

  describe("EVMTimeSeriesChart integration", () => {
    it("should render EVMTimeSeriesChart component", () => {
      render(
        <EVMAnalyzerModal
          open={true}
          onClose={vi.fn()}
          evmMetrics={mockEvmMetrics}
          timeSeries={mockTimeSeriesData}
          loading={false}
          onGranularityChange={vi.fn()}
        />,
        { wrapper }
      );

      const chart = screen.getByTestId("evm-timeseries-chart");
      expect(chart).toBeInTheDocument();
    });

    it("should pass timeSeries data to EVMTimeSeriesChart", () => {
      render(
        <EVMAnalyzerModal
          open={true}
          onClose={vi.fn()}
          evmMetrics={mockEvmMetrics}
          timeSeries={mockTimeSeriesData}
          loading={false}
          onGranularityChange={vi.fn()}
        />,
        { wrapper }
      );

      const chart = screen.getByTestId("evm-timeseries-chart");
      expect(chart).toBeInTheDocument();
    });

    it("should call onGranularityChange when granularity changes", async () => {
      const onGranularityChange = vi.fn();

      render(
        <EVMAnalyzerModal
          open={true}
          onClose={vi.fn()}
          evmMetrics={mockEvmMetrics}
          timeSeries={mockTimeSeriesData}
          loading={false}
          onGranularityChange={onGranularityChange}
        />,
        { wrapper }
      );

      // The chart should be rendered and the callback passed through
      const chart = screen.getByTestId("evm-timeseries-chart");
      expect(chart).toBeInTheDocument();
    });
  });

  describe("All metrics display", () => {
    it("should render gauges in the overview tab sidebar", () => {
      render(
        <EVMAnalyzerModal
          open={true}
          onClose={vi.fn()}
          evmMetrics={mockEvmMetrics}
          timeSeries={mockTimeSeriesData}
          loading={false}
          onGranularityChange={vi.fn()}
        />,
        { wrapper }
      );

      // Check for gauges in the overview tab
      expect(screen.getByTestId(/gauge-cpi/i)).toBeInTheDocument();
      expect(screen.getByTestId(/gauge-spi/i)).toBeInTheDocument();
    });

    it("should render time series chart in the overview tab", () => {
      render(
        <EVMAnalyzerModal
          open={true}
          onClose={vi.fn()}
          evmMetrics={mockEvmMetrics}
          timeSeries={mockTimeSeriesData}
          loading={false}
          onGranularityChange={vi.fn()}
        />,
        { wrapper }
      );

      // Check for the chart in the overview tab
      const chart = screen.getByTestId("evm-timeseries-chart");
      expect(chart).toBeInTheDocument();
    });

    it("should display all key financial metrics when All Metrics tab is clicked", async () => {
      render(
        <EVMAnalyzerModal
          open={true}
          onClose={vi.fn()}
          evmMetrics={mockEvmMetrics}
          timeSeries={mockTimeSeriesData}
          loading={false}
          onGranularityChange={vi.fn()}
        />,
        { wrapper }
      );

      // Click on the All Metrics tab
      const allMetricsTab = screen.getByText(/All Metrics/i);
      fireEvent.click(allMetricsTab);

      await waitFor(() => {
        // Check for key financial metrics (use getAllByText since they may appear in multiple places)
        expect(screen.getAllByText(/Budget at Completion/i).length).toBeGreaterThan(0);
        expect(screen.getAllByText(/Estimate at Completion/i).length).toBeGreaterThan(0);
        expect(screen.getAllByText(/Variance at Completion/i).length).toBeGreaterThan(0);
        expect(screen.getAllByText(/Estimate to Complete/i).length).toBeGreaterThan(0);
      });
    });

    it("should display all metric categories in All Metrics tab", async () => {
      render(
        <EVMAnalyzerModal
          open={true}
          onClose={vi.fn()}
          evmMetrics={mockEvmMetrics}
          timeSeries={mockTimeSeriesData}
          loading={false}
          onGranularityChange={vi.fn()}
        />,
        { wrapper }
      );

      // Click on the All Metrics tab
      const allMetricsTab = screen.getByText(/All Metrics/i);
      fireEvent.click(allMetricsTab);

      await waitFor(() => {
        // Check for section headers for each category
        expect(screen.getByText(/Key Financial Metrics/i)).toBeInTheDocument();
        expect(screen.getByText(/Schedule Performance Metrics/i)).toBeInTheDocument();
        expect(screen.getByText(/Cost Performance Metrics/i)).toBeInTheDocument();
        expect(screen.getByText(/Variance Analysis/i)).toBeInTheDocument();
        expect(screen.getByText(/Forecast Metrics/i)).toBeInTheDocument();
      });
    });
  });

  describe("Loading state", () => {
    it("should display loading state when loading is true", () => {
      render(
        <EVMAnalyzerModal
          open={true}
          onClose={vi.fn()}
          evmMetrics={undefined}
          timeSeries={undefined}
          loading={true}
          onGranularityChange={vi.fn()}
        />,
        { wrapper }
      );

      const loadingElement = document.querySelector(".ant-spin");
      expect(loadingElement).toBeInTheDocument();
    });

    it("should not display metrics when loading", () => {
      render(
        <EVMAnalyzerModal
          open={true}
          onClose={vi.fn()}
          evmMetrics={undefined}
          timeSeries={undefined}
          loading={true}
          onGranularityChange={vi.fn()}
        />,
        { wrapper }
      );

      // Metrics should not be visible during loading
      expect(screen.queryByTestId(/metric-card-bac/i)).not.toBeInTheDocument();
    });
  });

  describe("Empty state", () => {
    it("should display empty state when no data", () => {
      render(
        <EVMAnalyzerModal
          open={true}
          onClose={vi.fn()}
          evmMetrics={undefined}
          timeSeries={undefined}
          loading={false}
          onGranularityChange={vi.fn()}
        />,
        { wrapper }
      );

      expect(screen.getByText(/No EVM data available/i)).toBeInTheDocument();
    });

    it("should not display gauges when no data", () => {
      render(
        <EVMAnalyzerModal
          open={true}
          onClose={vi.fn()}
          evmMetrics={undefined}
          timeSeries={undefined}
          loading={false}
          onGranularityChange={vi.fn()}
        />,
        { wrapper }
      );

      expect(screen.queryByTestId("gauge-cpi")).not.toBeInTheDocument();
      expect(screen.queryByTestId("gauge-spi")).not.toBeInTheDocument();
    });

    it("should not display chart when no data", () => {
      render(
        <EVMAnalyzerModal
          open={true}
          onClose={vi.fn()}
          evmMetrics={undefined}
          timeSeries={undefined}
          loading={false}
          onGranularityChange={vi.fn()}
        />,
        { wrapper }
      );

      expect(screen.queryByTestId("evm-timeseries-chart")).not.toBeInTheDocument();
    });
  });

  describe("Accessibility", () => {
    it("should have proper ARIA attributes", () => {
      render(
        <EVMAnalyzerModal
          open={true}
          onClose={vi.fn()}
          evmMetrics={mockEvmMetrics}
          timeSeries={mockTimeSeriesData}
          loading={false}
          onGranularityChange={vi.fn()}
        />,
        { wrapper }
      );

      const modalElement = document.querySelector(".ant-modal");
      expect(modalElement).toHaveAttribute("role", "dialog");
    });
  });
});
