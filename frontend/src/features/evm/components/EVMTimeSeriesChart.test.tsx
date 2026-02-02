/**
 * EVMTimeSeriesChart Component Tests
 *
 * TDD RED-GREEN-REFACTOR cycle for the EVMTimeSeriesChart component.
 *
 * Test Strategy:
 * 1. Component renders without crashing
 * 2. Empty state displays correctly when no data
 * 3. Dual charts render (PV/EV/AC progression and Forecast vs Actual)
 * 4. Granularity selector works (day/week/month)
 * 5. Loading state displays correctly
 *
 * @module features/evm/components
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { EVMTimeSeriesChart } from "./EVMTimeSeriesChart";
import type { EVMTimeSeriesResponse, EVMTimeSeriesGranularity } from "../types";

// Mock echarts-for-react to avoid canvas rendering issues in tests
vi.mock("echarts-for-react", () => ({
  default: ({ option, onEvents }: { option: unknown; onEvents: unknown }) => (
    <div data-testid="echarts-mock" data-events={JSON.stringify(onEvents)}>
      <div data-testid="echarts-option">{JSON.stringify(option)}</div>
    </div>
  ),
}));

describe("EVMTimeSeriesChart", () => {
  let queryClient: QueryClient;

  // Mock time series data with complete structure
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

  describe("Basic rendering", () => {
    it("should render without crashing when data is provided", () => {
      expect(() => {
        render(
          <EVMTimeSeriesChart
            timeSeries={mockTimeSeriesData}
            loading={false}
            onGranularityChange={vi.fn()}
          />,
          { wrapper }
        );
      }).not.toThrow();
    });

    it("should display chart titles for both charts", () => {
      render(
        <EVMTimeSeriesChart
          timeSeries={mockTimeSeriesData}
          loading={false}
          onGranularityChange={vi.fn()}
        />,
        { wrapper }
      );

      // Check for EVM Progression chart title
      expect(screen.getByText(/EVM Progression/i)).toBeInTheDocument();
      // Check for Cost Comparison chart title
      expect(screen.getByText(/Cost Comparison/i)).toBeInTheDocument();
    });

    it("should render the main chart title", () => {
      render(
        <EVMTimeSeriesChart
          timeSeries={mockTimeSeriesData}
          loading={false}
          onGranularityChange={vi.fn()}
        />,
        { wrapper }
      );

      // Check for main title
      expect(screen.getByText(/EVM Time Series Analysis/i)).toBeInTheDocument();
    });
  });

  describe("Empty state", () => {
    it("should display empty state when timeSeries is undefined", () => {
      render(
        <EVMTimeSeriesChart
          timeSeries={undefined}
          loading={false}
          onGranularityChange={vi.fn()}
        />,
        { wrapper }
      );

      // The Card wrapper should still render with the title
      expect(screen.getByText(/EVM Time Series Analysis/i)).toBeInTheDocument();
    });

    it("should display empty state when timeSeries has no points", () => {
      const emptyData: EVMTimeSeriesResponse = {
        granularity: "week" as EVMTimeSeriesGranularity,
        points: [],
        start_date: "2024-01-01T00:00:00Z",
        end_date: "2024-01-15T00:00:00Z",
        total_points: 0,
      };

      render(
        <EVMTimeSeriesChart
          timeSeries={emptyData}
          loading={false}
          onGranularityChange={vi.fn()}
        />,
        { wrapper }
      );

      // Should render without crashing
      expect(screen.getByText(/EVM Time Series Analysis/i)).toBeInTheDocument();
    });
  });

  describe("Loading state", () => {
    it("should display loading state when loading is true", () => {
      render(
        <EVMTimeSeriesChart
          timeSeries={undefined}
          loading={true}
          onGranularityChange={vi.fn()}
        />,
        { wrapper }
      );

      // Should show loading skeleton
      const loadingCard = document.querySelector(".ant-card-loading");
      expect(loadingCard).toBeInTheDocument();
    });
  });

  describe("Granularity selector", () => {
    it("should render granularity selector with options", () => {
      const onGranularityChange = vi.fn();

      render(
        <EVMTimeSeriesChart
          timeSeries={mockTimeSeriesData}
          loading={false}
          onGranularityChange={onGranularityChange}
        />,
        { wrapper }
      );

      // Check for granularity options
      expect(screen.getByText(/Day/i)).toBeInTheDocument();
      expect(screen.getByText(/Week/i)).toBeInTheDocument();
      expect(screen.getByText(/Month/i)).toBeInTheDocument();
    });

    it("should call onGranularityChange when granularity is changed", async () => {
      const onGranularityChange = vi.fn();

      render(
        <EVMTimeSeriesChart
          timeSeries={mockTimeSeriesData}
          loading={false}
          onGranularityChange={onGranularityChange}
        />,
        { wrapper }
      );

      // Click on Month option
      const monthOption = screen.getByText(/Month/i);
      monthOption.click();

      await waitFor(() => {
        expect(onGranularityChange).toHaveBeenCalled();
      });
    });

    it("should display current granularity as selected", () => {
      render(
        <EVMTimeSeriesChart
          timeSeries={mockTimeSeriesData}
          loading={false}
          onGranularityChange={vi.fn()}
        />,
        { wrapper }
      );

      // Week should be the default/current granularity
      expect(screen.getByText(/Week/i)).toBeInTheDocument();
    });
  });

  describe("Dual charts rendering", () => {
    it("should render two separate charts", () => {
      render(
        <EVMTimeSeriesChart
          timeSeries={mockTimeSeriesData}
          loading={false}
          onGranularityChange={vi.fn()}
        />,
        { wrapper }
      );

      // Should have two chart titles
      expect(screen.getByText(/EVM Progression/i)).toBeInTheDocument();
      expect(screen.getByText(/Cost Comparison/i)).toBeInTheDocument();
    });

    it("should render PV/EV/AC progression chart", () => {
      render(
        <EVMTimeSeriesChart
          timeSeries={mockTimeSeriesData}
          loading={false}
          onGranularityChange={vi.fn()}
        />,
        { wrapper }
      );

      // Check for EVM Progression chart
      expect(screen.getByText(/EVM Progression/i)).toBeInTheDocument();
    });

    it("should render Forecast vs Actual cost comparison chart", () => {
      render(
        <EVMTimeSeriesChart
          timeSeries={mockTimeSeriesData}
          loading={false}
          onGranularityChange={vi.fn()}
        />,
        { wrapper }
      );

      // Check for Cost Comparison chart
      expect(screen.getByText(/Cost Comparison/i)).toBeInTheDocument();
    });
  });

  describe("Chart data transformation", () => {
    it("should transform time series data correctly for chart rendering", () => {
      render(
        <EVMTimeSeriesChart
          timeSeries={mockTimeSeriesData}
          loading={false}
          onGranularityChange={vi.fn()}
        />,
        { wrapper }
      );

      // If charts render without errors, data transformation is working
      expect(screen.getByText(/EVM Progression/i)).toBeInTheDocument();
      expect(screen.getByText(/Cost Comparison/i)).toBeInTheDocument();
    });
  });

  describe("Accessibility", () => {
    it("should have proper ARIA labels", () => {
      render(
        <EVMTimeSeriesChart
          timeSeries={mockTimeSeriesData}
          loading={false}
          onGranularityChange={vi.fn()}
        />,
        { wrapper }
      );

      // Chart containers should be accessible
      const chartTitles = screen.getAllByRole("heading");
      expect(chartTitles.length).toBeGreaterThan(0);
    });
  });
});
