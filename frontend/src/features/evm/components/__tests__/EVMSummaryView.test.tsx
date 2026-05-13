import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { EVMSummaryView } from "../EVMSummaryView";
import { EVMMetricsResponse, EVMTimeSeriesResponse } from "../../types";

vi.mock("echarts-for-react", () => ({
  __esModule: true,
  default: () => <div data-testid="echarts-mock" />,
}));

vi.mock("antd", async () => {
  const actual = await vi.importActual("antd");
  return {
    ...actual,
    theme: {
      useToken: () => ({
        token: {
          colorBgContainer: "#ffffff",
          colorBorder: "#d9d9d9",
          colorText: "#000000",
          colorTextSecondary: "#666666",
          colorTextTertiary: "#999999",
          colorSuccess: "#5da572",
          colorWarning: "#d4a549",
          colorError: "#c95d5f",
          colorPrimary: "#4a7c91",
          borderRadiusLG: 8,
          borderRadiusSM: 4,
          paddingXXS: 4,
          paddingMD: 16,
          paddingLG: 24,
          paddingXL: 32,
          colorFillSecondary: "#f0f0f0",
          boxShadow: "0 2px 8px rgba(0,0,0,0.15)",
          colorBorderSecondary: "#f0f0f0",
          colorBgElevated: "#ffffff",
        },
      }),
    },
  };
});

const mockMetrics: EVMMetricsResponse = {
  entity_type: "project" as const,
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
  progress_percentage: 72,
};

const mockTimeSeries: EVMTimeSeriesResponse = {
  granularity: "week" as const,
  points: [
    { date: "2025-01-06", pv: 200000, ev: 180000, ac: 190000, forecast: 185000, actual: 188000, cpi: 0.95, spi: 0.9 },
    { date: "2025-01-13", pv: 400000, ev: 360000, ac: 380000, forecast: 370000, actual: 375000, cpi: 0.95, spi: 0.9 },
    { date: "2025-01-20", pv: 600000, ev: 540000, ac: 560000, forecast: 555000, actual: 558000, cpi: 0.96, spi: 0.9 },
    { date: "2025-01-27", pv: 800000, ev: 720000, ac: 750000, forecast: 740000, actual: 745000, cpi: 0.96, spi: 0.9 },
  ],
  start_date: "2025-01-06",
  end_date: "2025-01-27",
  total_points: 4,
};

describe("EVMSummaryView", () => {
  describe("Basic Rendering", () => {
    it("renders EVM Summary header", () => {
      render(<EVMSummaryView metrics={mockMetrics} />);

      expect(screen.getByText("EVM Summary")).toBeInTheDocument();
    });

    it("renders Advanced button", () => {
      render(<EVMSummaryView metrics={mockMetrics} />);

      expect(screen.getByRole("button", { name: /advanced/i })).toBeInTheDocument();
    });

    it("renders KPI indicators", () => {
      render(<EVMSummaryView metrics={mockMetrics} />);

      expect(screen.getByText("CPI")).toBeInTheDocument();
      expect(screen.getByText("SPI")).toBeInTheDocument();
      expect(screen.getByText("BAC")).toBeInTheDocument();
      expect(screen.getByText("EAC")).toBeInTheDocument();
      expect(screen.getByText("VAC")).toBeInTheDocument();
      expect(screen.getByText("Progress")).toBeInTheDocument();
    });

    it("renders forecast bar with budget labels", () => {
      render(<EVMSummaryView metrics={mockMetrics} />);

      const bacElements = screen.getAllByText(/BAC/);
      expect(bacElements.length).toBeGreaterThanOrEqual(1);
      const eacElements = screen.getAllByText(/EAC/);
      expect(eacElements.length).toBeGreaterThanOrEqual(1);
      expect(screen.getByText(/Spent/)).toBeInTheDocument();
      expect(screen.getByText(/Remaining/)).toBeInTheDocument();
    });

    it("renders Detail Metrics collapse collapsed by default", () => {
      render(<EVMSummaryView metrics={mockMetrics} />);

      expect(screen.getByText("Detail Metrics")).toBeInTheDocument();
      expect(screen.queryByText("Schedule Variance")).not.toBeInTheDocument();
    });

    it("hides header when hideHeader is true", () => {
      render(<EVMSummaryView metrics={mockMetrics} hideHeader />);

      expect(screen.queryByText("EVM Summary")).not.toBeInTheDocument();
      expect(screen.queryByRole("button", { name: /advanced/i })).not.toBeInTheDocument();
    });
  });

  describe("KPI Strip Values", () => {
    it("displays correct CPI value", () => {
      render(<EVMSummaryView metrics={mockMetrics} />);

      expect(screen.getByText("0.96")).toBeInTheDocument();
    });

    it("displays correct SPI value", () => {
      render(<EVMSummaryView metrics={mockMetrics} />);

      expect(screen.getByText("0.90")).toBeInTheDocument();
    });

    it("displays BAC as currency", () => {
      render(<EVMSummaryView metrics={mockMetrics} />);

      expect(screen.getByText("€1,000,000.00")).toBeInTheDocument();
    });

    it("displays progress as percentage", () => {
      render(<EVMSummaryView metrics={mockMetrics} />);

      expect(screen.getByText("72%")).toBeInTheDocument();
    });

    it("shows N/A for null values", () => {
      const metricsWithNulls: EVMMetricsResponse = {
        ...mockMetrics,
        cpi: null,
        spi: null,
        eac: null,
        vac: null,
        etc: null,
      };

      render(<EVMSummaryView metrics={metricsWithNulls} />);

      const naElements = screen.getAllByText("N/A");
      expect(naElements.length).toBeGreaterThanOrEqual(4);
    });
  });

  describe("Detail Metrics", () => {
    it("expands to show metric cards when clicked", () => {
      render(<EVMSummaryView metrics={mockMetrics} />);

      const collapseHeader = screen.getByText("Detail Metrics").closest(".ant-collapse-header");
      expect(collapseHeader).toBeInTheDocument();
      fireEvent.click(collapseHeader!);

      expect(screen.getByText("Schedule Variance")).toBeInTheDocument();
      expect(screen.getByText("Cost Variance")).toBeInTheDocument();
      expect(screen.getByText("Actual Cost")).toBeInTheDocument();
      expect(screen.getByText("Estimate to Complete")).toBeInTheDocument();
    });
  });

  describe("Advanced Button", () => {
    it("calls onAdvanced callback when clicked", () => {
      const onAdvanced = vi.fn();

      render(<EVMSummaryView metrics={mockMetrics} onAdvanced={onAdvanced} />);

      const advancedButton = screen.getByRole("button", { name: /advanced/i });
      fireEvent.click(advancedButton);

      expect(onAdvanced).toHaveBeenCalledTimes(1);
    });

    it("does not throw when onAdvanced is not provided", () => {
      expect(() => {
        render(<EVMSummaryView metrics={mockMetrics} />);

        const advancedButton = screen.getByRole("button", { name: /advanced/i });
        fireEvent.click(advancedButton);
      }).not.toThrow();
    });
  });

  describe("Edge Cases", () => {
    it("handles zero values", () => {
      const zeroMetrics: EVMMetricsResponse = {
        ...mockMetrics,
        bac: 0,
        pv: 0,
        ac: 0,
        ev: 0,
        cv: 0,
        sv: 0,
        cpi: null,
        spi: null,
        eac: null,
        vac: null,
        etc: null,
        progress_percentage: 0,
      };

      expect(() => {
        render(<EVMSummaryView metrics={zeroMetrics} />);
      }).not.toThrow();
    });

    it("handles negative values", () => {
      const negativeMetrics: EVMMetricsResponse = {
        ...mockMetrics,
        cv: -100000,
        sv: -50000,
        vac: -200000,
      };

      expect(() => {
        render(<EVMSummaryView metrics={negativeMetrics} />);
      }).not.toThrow();
    });

    it("handles very large values", () => {
      const largeMetrics: EVMMetricsResponse = {
        ...mockMetrics,
        bac: 10000000000,
        eac: 12000000000,
      };

      expect(() => {
        render(<EVMSummaryView metrics={largeMetrics} />);
      }).not.toThrow();
    });

    it("handles null EAC, ETC, and VAC", () => {
      const nullForecastMetrics: EVMMetricsResponse = {
        ...mockMetrics,
        eac: null,
        etc: null,
        vac: null,
      };

      render(<EVMSummaryView metrics={nullForecastMetrics} />);

      const naElements = screen.getAllByText("N/A");
      expect(naElements.length).toBeGreaterThanOrEqual(2);
    });
  });

  describe("TimeSeries prop", () => {
    it("renders Skeleton when timeSeries is undefined", () => {
      const { container } = render(<EVMSummaryView metrics={mockMetrics} />);

      expect(container.querySelector(".ant-skeleton")).toBeInTheDocument();
      expect(screen.queryByTestId("echarts-mock")).not.toBeInTheDocument();
    });

    it("renders chart when timeSeries is provided", () => {
      render(<EVMSummaryView metrics={mockMetrics} timeSeries={mockTimeSeries} />);

      expect(screen.getByTestId("echarts-mock")).toBeInTheDocument();
    });
  });
});
