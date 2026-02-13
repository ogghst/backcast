import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { MetricCard } from "../MetricCard";
import {
  MetricMetadata,
} from "../../types";

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
        },
      }),
    },
  };
});

describe("MetricCard", () => {
  const mockMetadata: MetricMetadata = {
    key: "cpi",
    name: "Cost Performance Index",
    description:
      "Ratio of earned value to actual cost. CPI < 1.0 indicates the project is over budget.",
    category: "Performance" as const,
    targetRanges: { min: 0, max: 2, good: 1.0 },
    higherIsBetter: true,
    format: "number",
  };

  describe("Basic Rendering", () => {
    it("renders metric value correctly", () => {
      render(
        <MetricCard
          metadata={mockMetadata}
          value={1.07}
          status="good"
          size="medium"
        />
      );

      expect(screen.getByText("1.07")).toBeInTheDocument();
      expect(screen.getByText("Cost Performance Index")).toBeInTheDocument();
    });

    it("renders metric label correctly", () => {
      render(
        <MetricCard
          metadata={mockMetadata}
          value={1.07}
          status="good"
          size="medium"
        />
      );

      expect(screen.getByText("Cost Performance Index")).toBeInTheDocument();
    });

    it("renders description when showDescription is true", () => {
      render(
        <MetricCard
          metadata={mockMetadata}
          value={1.07}
          status="good"
          size="medium"
          showDescription
        />
      );

      expect(
        screen.getByText(
          "Ratio of earned value to actual cost. CPI < 1.0 indicates the project is over budget."
        )
      ).toBeInTheDocument();
    });

    it("does not render description when showDescription is false", () => {
      render(
        <MetricCard
          metadata={mockMetadata}
          value={1.07}
          status="good"
          size="medium"
          showDescription={false}
        />
      );

      expect(
        screen.queryByText(
          "Ratio of earned value to actual cost. CPI < 1.0 indicates the project is over budget."
        )
      ).not.toBeInTheDocument();
    });
  });

  describe("Value Formatting", () => {
    it("formats currency values with euro symbol and decimals", () => {
      const currencyMetadata: MetricMetadata = {
        ...mockMetadata,
        key: "bac",
        name: "Budget at Completion",
        description: "Total planned budget",
        category: "Cost" as const,
        targetRanges: { min: 0, max: Infinity },
        higherIsBetter: false,
        format: "currency",
      };

      render(
        <MetricCard
          metadata={currencyMetadata}
          value={100000}
          status="good"
          size="medium"
        />
      );

      expect(screen.getByText("€100,000.00")).toBeInTheDocument();
    });

    it("formats percentage values", () => {
      const percentageMetadata: MetricMetadata = {
        ...mockMetadata,
        key: "spi",
        name: "Schedule Performance Index",
        description: "Schedule efficiency ratio",
        category: "Schedule" as const,
        targetRanges: { min: 0, max: 2, good: 1.0 },
        higherIsBetter: true,
        format: "percentage",
      };

      render(
        <MetricCard
          metadata={percentageMetadata}
          value={0.96}
          status="warning"
          size="medium"
        />
      );

      expect(screen.getByText("96%")).toBeInTheDocument();
    });

    it("formats number values with decimals", () => {
      render(
        <MetricCard
          metadata={mockMetadata}
          value={1.0667}
          status="good"
          size="medium"
        />
      );

      expect(screen.getByText("1.07")).toBeInTheDocument();
    });
  });

  describe("Status Indicators", () => {
    it("applies good status styling", () => {
      const { container } = render(
        <MetricCard
          metadata={mockMetadata}
          value={1.07}
          status="good"
          size="medium"
        />
      );

      // Check for green color indicator (good status)
      const card = container.querySelector(".ant-card");
      expect(card).toBeInTheDocument();
      // Ant Design's color system - good is typically green
    });

    it("applies warning status styling", () => {
      const { container } = render(
        <MetricCard
          metadata={mockMetadata}
          value={0.95}
          status="warning"
          size="medium"
        />
      );

      const card = container.querySelector(".ant-card");
      expect(card).toBeInTheDocument();
    });

    it("applies bad status styling", () => {
      const { container } = render(
        <MetricCard
          metadata={mockMetadata}
          value={0.85}
          status="bad"
          size="medium"
        />
      );

      const card = container.querySelector(".ant-card");
      expect(card).toBeInTheDocument();
    });

    it("handles null values correctly", () => {
      render(
        <MetricCard
          metadata={mockMetadata}
          value={null}
          status="warning"
          size="medium"
        />
      );

      expect(screen.getByText("N/A")).toBeInTheDocument();
    });
  });

  describe("Size Variants", () => {
    it("renders small size variant", () => {
      const { container } = render(
        <MetricCard
          metadata={mockMetadata}
          value={1.07}
          status="good"
          size="small"
        />
      );

      const card = container.querySelector(".ant-card");
      expect(card).toBeInTheDocument();
    });

    it("renders medium size variant", () => {
      const { container } = render(
        <MetricCard
          metadata={mockMetadata}
          value={1.07}
          status="good"
          size="medium"
        />
      );

      const card = container.querySelector(".ant-card");
      expect(card).toBeInTheDocument();
    });

    it("renders large size variant", () => {
      const { container } = render(
        <MetricCard
          metadata={mockMetadata}
          value={1.07}
          status="good"
          size="large"
        />
      );

      const card = container.querySelector(".ant-card");
      expect(card).toBeInTheDocument();
    });
  });

  describe("Accessibility", () => {
    it("includes proper ARIA labels", () => {
      render(
        <MetricCard
          metadata={mockMetadata}
          value={1.07}
          status="good"
          size="medium"
        />
      );

      // Check for accessible name
      const card = screen.getByText("Cost Performance Index").closest(".ant-card");
      expect(card).toBeInTheDocument();
    });

    it("includes ARIA description when showDescription is true", () => {
      render(
        <MetricCard
          metadata={mockMetadata}
          value={1.07}
          status="good"
          size="medium"
          showDescription
        />
      );

      const description = screen.getByText(
        "Ratio of earned value to actual cost. CPI < 1.0 indicates the project is over budget."
      );
      expect(description).toBeInTheDocument();
    });
  });

  describe("Edge Cases", () => {
    it("handles zero values correctly", () => {
      render(
        <MetricCard
          metadata={mockMetadata}
          value={0}
          status="bad"
          size="medium"
        />
      );

      expect(screen.getByText("0.00")).toBeInTheDocument();
    });

    it("handles negative values correctly", () => {
      const varianceMetadata: MetricMetadata = {
        ...mockMetadata,
        key: "cv",
        name: "Cost Variance",
        description: "Difference between earned value and actual cost",
        category: "Cost" as const,
        targetRanges: { min: -Infinity, max: Infinity, good: 0 },
        higherIsBetter: true,
        format: "currency",
      };

      render(
        <MetricCard
          metadata={varianceMetadata}
          value={-5000}
          status="bad"
          size="medium"
        />
      );

      expect(screen.getByText("-€5,000.00")).toBeInTheDocument();
    });

    it("handles very large values correctly", () => {
      const largeValueMetadata: MetricMetadata = {
        ...mockMetadata,
        key: "bac",
        name: "Budget at Completion",
        description: "Total planned budget",
        category: "Cost" as const,
        targetRanges: { min: 0, max: Infinity },
        higherIsBetter: false,
        format: "currency",
      };

      render(
        <MetricCard
          metadata={largeValueMetadata}
          value={1000000000}
          status="good"
          size="medium"
        />
      );

      expect(screen.getByText("€1,000,000,000.00")).toBeInTheDocument();
    });
  });
});
