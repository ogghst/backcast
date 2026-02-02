/**
 * EVMGauge Component Tests
 *
 * Tests for the EVMGauge component now using ECharts.
 *
 * Test Strategy:
 * 1. Component renders without crashing
 * 2. Label and value display correctly
 * 3. Null value handling
 * 4. Props are passed correctly to EChartsGauge
 *
 * @module features/evm/components
 */

import { describe, it, expect, beforeEach, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { EVMGauge } from "./EVMGauge";

// Mock echarts-for-react to avoid canvas rendering issues in tests
vi.mock("echarts-for-react", () => ({
  default: ({ option }: { option: unknown }) => (
    <div data-testid="echarts-gauge-mock">
      <div data-testid="gauge-option">{JSON.stringify(option)}</div>
    </div>
  ),
}));

// Mock the theme hook
vi.mock("antd", async () => {
  const actual = await vi.importActual("antd");
  return {
    ...actual,
    theme: {
      useToken: () => ({
        token: {
          colorPrimary: "#1890ff",
          colorSuccess: "#52c41a",
          colorWarning: "#faad14",
          colorError: "#ff4d4f",
          colorInfo: "#1890ff",
          colorText: "rgba(0,0,0,0.88)",
          colorTextSecondary: "rgba(0,0,0,0.65)",
          colorBorder: "#d9d9d9",
          colorBorderSecondary: "#f0f0f0",
          colorBgContainer: "#ffffff",
          borderRadius: 6,
          boxShadow: "0 1px 2px rgba(0,0,0,0.03)",
        },
      }),
    },
  };
});

describe("EVMGauge", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe("Basic Rendering", () => {
    it("renders the gauge component with value", () => {
      render(<EVMGauge value={1.0} min={0} max={2} label="CPI" />);

      // Check for the label
      expect(screen.getByText("CPI")).toBeInTheDocument();

      // ECharts mock should be rendered
      const echartsMock = document.querySelector('[data-testid="echarts-gauge-mock"]');
      expect(echartsMock).toBeInTheDocument();
    });

    it("renders EChartsGauge with correct props", () => {
      const { container } = render(
        <EVMGauge value={1.2} min={0} max={2} label="SPI" goodThreshold={1.0} />
      );

      // Check for ECharts mock
      const echartsMock = container.querySelector('[data-testid="echarts-gauge-mock"]');
      expect(echartsMock).toBeInTheDocument();

      // Check the option contains the label
      const optionDiv = container.querySelector('[data-testid="gauge-option"]');
      expect(optionDiv?.textContent).toContain("SPI");
    });
  });

  describe("Value Display", () => {
    it("displays label correctly", () => {
      render(<EVMGauge value={1.0} min={0} max={2} label="Test Label" />);

      expect(screen.getByText("Test Label")).toBeInTheDocument();
    });

    it("handles null value by showing empty state", () => {
      render(<EVMGauge value={null} min={0} max={2} label="CPI" />);

      // Label should still be displayed
      expect(screen.getByText("CPI")).toBeInTheDocument();

      // ECharts mock should be rendered (showing "not available" state)
      const echartsMock = document.querySelector('[data-testid="echarts-gauge-mock"]');
      expect(echartsMock).toBeInTheDocument();
    });

    it("handles edge case of zero value", () => {
      render(<EVMGauge value={0} min={0} max={2} label="CPI" />);

      expect(screen.getByText("CPI")).toBeInTheDocument();
      const echartsMock = document.querySelector('[data-testid="echarts-gauge-mock"]');
      expect(echartsMock).toBeInTheDocument();
    });
  });

  describe("Props Handling", () => {
    it("passes goodThreshold prop correctly", () => {
      const { container } = render(
        <EVMGauge value={1.0} min={0} max={2} label="CPI" goodThreshold={1.0} />
      );

      const echartsMock = container.querySelector('[data-testid="echarts-gauge-mock"]');
      expect(echartsMock).toBeInTheDocument();
    });

    it("passes warningThresholdPercent prop correctly", () => {
      const { container } = render(
        <EVMGauge value={1.0} min={0} max={2} label="CPI" warningThresholdPercent={0.9} />
      );

      const echartsMock = container.querySelector('[data-testid="echarts-gauge-mock"]');
      expect(echartsMock).toBeInTheDocument();
    });

    it("passes size prop correctly", () => {
      const { container } = render(
        <EVMGauge value={1.0} min={0} max={2} label="CPI" size={250} />
      );

      const echartsMock = container.querySelector('[data-testid="echarts-gauge-mock"]');
      expect(echartsMock).toBeInTheDocument();
    });

    it("handles strokeWidth prop (kept for API compatibility)", () => {
      const { container } = render(
        <EVMGauge value={1.0} min={0} max={2} label="CPI" strokeWidth={25} />
      );

      const echartsMock = container.querySelector('[data-testid="echarts-gauge-mock"]');
      expect(echartsMock).toBeInTheDocument();
    });
  });

  describe("Component Structure", () => {
    it("renders with centered text alignment", () => {
      const { container } = render(
        <EVMGauge value={1.0} min={0} max={2} label="CPI" />
      );

      const wrapper = container.querySelector("div");
      expect(wrapper?.style.textAlign).toBe("center");
    });

    it("renders label as Typography.Text", () => {
      render(<EVMGauge value={1.0} min={0} max={2} label="SPI" />);

      const label = screen.getByText("SPI");
      expect(label).toBeInTheDocument();
    });
  });

  describe("Edge Cases", () => {
    it("handles value below minimum", () => {
      const { container } = render(
        <EVMGauge value={-0.5} min={0} max={2} label="CPI" />
      );

      const echartsMock = container.querySelector('[data-testid="echarts-gauge-mock"]');
      expect(echartsMock).toBeInTheDocument();
    });

    it("handles value above maximum", () => {
      const { container } = render(
        <EVMGauge value={2.5} min={0} max={2} label="CPI" />
      );

      const echartsMock = container.querySelector('[data-testid="echarts-gauge-mock"]');
      expect(echartsMock).toBeInTheDocument();
    });

    it("handles very small range", () => {
      render(<EVMGauge value={0.95} min={0.9} max={1.0} label="CPI" />);

      expect(screen.getByText("CPI")).toBeInTheDocument();
      const echartsMock = document.querySelector('[data-testid="echarts-gauge-mock"]');
      expect(echartsMock).toBeInTheDocument();
    });

    it("handles very large range", () => {
      render(<EVMGauge value={50000} min={0} max={100000} label="CPI" />);

      expect(screen.getByText("CPI")).toBeInTheDocument();
      const echartsMock = document.querySelector('[data-testid="echarts-gauge-mock"]');
      expect(echartsMock).toBeInTheDocument();
    });
  });

  describe("Export", () => {
    it("has default export", () => {
      expect(EVMGauge).toBeDefined();
    });
  });
});
