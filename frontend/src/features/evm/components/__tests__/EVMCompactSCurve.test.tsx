import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { EVMCompactSCurve } from "../EVMCompactSCurve";
import { EVMTimeSeriesResponse } from "../../types";

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

describe("EVMCompactSCurve", () => {
  describe("Skeleton State", () => {
    it("shows Skeleton when timeSeries is undefined", () => {
      const { container } = render(<EVMCompactSCurve />);

      expect(container.querySelector(".ant-skeleton")).toBeInTheDocument();
      expect(screen.queryByTestId("echarts-mock")).not.toBeInTheDocument();
    });
  });

  describe("Chart Rendering", () => {
    it("renders chart when timeSeries is provided", () => {
      render(<EVMCompactSCurve timeSeries={mockTimeSeries} />);

      expect(screen.getByTestId("echarts-mock")).toBeInTheDocument();
    });
  });

  describe("Loading State", () => {
    it("shows loading spinner when loading is true", () => {
      const { container } = render(
        <EVMCompactSCurve timeSeries={mockTimeSeries} loading />
      );

      expect(container.querySelector(".ant-spin")).toBeInTheDocument();
    });
  });

  describe("Default Height", () => {
    it("uses default height of 220", () => {
      render(<EVMCompactSCurve timeSeries={mockTimeSeries} />);

      const chart = screen.getByTestId("echarts-mock");
      expect(chart).toBeInTheDocument();
    });
  });
});
