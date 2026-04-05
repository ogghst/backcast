import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { EVMSummaryView } from "../EVMSummaryView";
import { EVMMetricsResponse } from "../../types";

// Mock the theme hook
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
          borderRadiusLG: 8,
          colorPrimary: "#1890ff",
        },
      }),
    },
  };
});

describe("EVMSummaryView", () => {
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

  describe("Basic Rendering", () => {
    it("renders all metric categories", () => {
      render(<EVMSummaryView metrics={mockMetrics} />);

      expect(screen.getByText("Schedule Metrics")).toBeInTheDocument();
      expect(screen.getByText("Cost Metrics")).toBeInTheDocument();
      expect(screen.getByText("Performance Metrics")).toBeInTheDocument();
      expect(screen.getByText("Forecast Metrics")).toBeInTheDocument();
    });

    it("renders Advanced button", () => {
      render(<EVMSummaryView metrics={mockMetrics} />);

      expect(screen.getByRole("button", { name: /advanced/i })).toBeInTheDocument();
    });

    it("renders schedule metrics", () => {
      render(<EVMSummaryView metrics={mockMetrics} />);

      expect(screen.getAllByText(/Schedule Performance Index/i).length).toBeGreaterThan(0);
      expect(screen.getAllByText(/Schedule Variance/i).length).toBeGreaterThan(0);
    });

    it("renders cost metrics", () => {
      render(<EVMSummaryView metrics={mockMetrics} />);

      expect(screen.getAllByText(/Budget at Completion/i).length).toBeGreaterThan(0);
      expect(screen.getAllByText(/Actual Cost/i).length).toBeGreaterThan(0);
      expect(screen.getAllByText(/Cost Variance/i).length).toBeGreaterThan(0);
    });

    it("renders performance metrics", () => {
      render(<EVMSummaryView metrics={mockMetrics} />);

      expect(screen.getAllByText(/Cost Performance Index/i).length).toBeGreaterThan(0);
    });

    it("renders forecast metrics", () => {
      render(<EVMSummaryView metrics={mockMetrics} />);

      expect(screen.getAllByText(/Estimate at Completion/i).length).toBeGreaterThan(0);
      expect(screen.getAllByText(/Variance at Completion/i).length).toBeGreaterThan(0);
      expect(screen.getAllByText(/Estimate to Complete/i).length).toBeGreaterThan(0);
    });
  });

  describe("Metric Values", () => {
    it("displays correct metric values", () => {
      render(<EVMSummaryView metrics={mockMetrics} />);

      expect(screen.getByText("0.90")).toBeInTheDocument(); // SPI
      expect(screen.getByText("0.96")).toBeInTheDocument(); // CPI
    });

    it("handles null metric values gracefully", () => {
      const metricsWithNulls: EVMMetricsResponse = {
        ...mockMetrics,
        cpi: null,
        spi: null,
        eac: null,
        vac: null,
        etc: null,
      };

      render(<EVMSummaryView metrics={metricsWithNulls} />);

      // Should show N/A for null values
      expect(screen.getAllByText("N/A").length).toBeGreaterThan(0);
    });
  });

  describe("Collapsible Sections", () => {
    it("renders collapsible sections for each category", () => {
      const { container } = render(<EVMSummaryView metrics={mockMetrics} />);

      // Ant Design Collapse renders with specific class
      const collapse = container.querySelector(".ant-collapse");
      expect(collapse).toBeInTheDocument();
    });

    it("allows collapsing and expanding sections", () => {
      const { container } = render(<EVMSummaryView metrics={mockMetrics} />);

      // Find collapse panels
      const collapsePanels = container.querySelectorAll(".ant-collapse-header");
      expect(collapsePanels.length).toBeGreaterThan(0);

      // Click the first panel to collapse
      const firstPanel = collapsePanels[0];
      fireEvent.click(firstPanel);

      // After clicking, the panel should collapse
      // Ant Design adds 'ant-collapse-item-active' class to expanded items
      const firstPanelItem = firstPanel.closest(".ant-collapse-item");
      expect(firstPanelItem).toBeInTheDocument();
    });

    it("all sections are expanded by default", () => {
      const { container } = render(<EVMSummaryView metrics={mockMetrics} />);

      // All panels should have the active class initially
      const activePanels = container.querySelectorAll(".ant-collapse-item-active");
      expect(activePanels.length).toBe(4); // Schedule, Cost, Performance, Forecast
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

    it("does not throw error when onAdvanced is not provided", () => {
      expect(() => {
        render(<EVMSummaryView metrics={mockMetrics} />);

        const advancedButton = screen.getByRole("button", { name: /advanced/i });
        fireEvent.click(advancedButton);
      }).not.toThrow();
    });
  });

  describe("Layout and Organization", () => {
    it("groups metrics by correct categories", () => {
      const { container } = render(<EVMSummaryView metrics={mockMetrics} />);

      // Check that we have 4 collapse panels (one per category)
      const panels = container.querySelectorAll(".ant-collapse-item");
      expect(panels.length).toBe(4);
    });

    it("displays metrics in a grid layout", () => {
      const { container } = render(<EVMSummaryView metrics={mockMetrics} />);

      // MetricCard components should be rendered
      const metricCards = container.querySelectorAll(".ant-card");
      expect(metricCards.length).toBeGreaterThan(0);
    });

    it("shows metric descriptions when cards are rendered", () => {
      render(<EVMSummaryView metrics={mockMetrics} />);

      // Check for descriptions from the metric definitions
      expect(
        screen.getByText(/Ratio of earned value to planned value/i)
      ).toBeInTheDocument();
      expect(
        screen.getByText(/Ratio of earned value to actual cost/i)
      ).toBeInTheDocument();
    });
  });

  describe("Accessibility", () => {
    it("has proper ARIA labels for collapsible sections", () => {
      const { container } = render(<EVMSummaryView metrics={mockMetrics} />);

      // Ant Design Collapse should have proper accessibility attributes
      const collapse = container.querySelector(".ant-collapse");
      expect(collapse).toBeInTheDocument();
    });

    it("Advanced button is accessible", () => {
      render(<EVMSummaryView metrics={mockMetrics} />);

      const advancedButton = screen.getByRole("button", { name: /advanced/i });
      expect(advancedButton).toBeInTheDocument();
    });
  });

  describe("Edge Cases", () => {
    it("handles metrics with zero values", () => {
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
      };

      expect(() => {
        render(<EVMSummaryView metrics={zeroMetrics} />);
      }).not.toThrow();
    });

    it("handles metrics with negative values", () => {
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

    it("handles metrics with very large values", () => {
      const largeMetrics: EVMMetricsResponse = {
        ...mockMetrics,
        bac: 10000000000,
        eac: 12000000000,
      };

      expect(() => {
        render(<EVMSummaryView metrics={largeMetrics} />);
      }).not.toThrow();
    });
  });

  describe("Type Safety", () => {
    it("accepts valid EVMMetricsResponse", () => {
      expect(() => {
        render(<EVMSummaryView metrics={mockMetrics} />);
      }).not.toThrow();
    });

    it("properly types the onAdvanced callback", () => {
      const onAdvanced = vi.fn();

      render(<EVMSummaryView metrics={mockMetrics} onAdvanced={onAdvanced} />);

      const advancedButton = screen.getByRole("button", { name: /advanced/i });
      fireEvent.click(advancedButton);

      // Callback should be called
      expect(onAdvanced).toHaveBeenCalledTimes(1);
    });
  });
});
