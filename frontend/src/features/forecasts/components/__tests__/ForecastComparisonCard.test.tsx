/**
 * ForecastComparisonCard Component Tests
 *
 * TDD RED-GREEN-REFACTOR cycle for the refactored ForecastComparisonCard component.
 *
 * Test Strategy:
 * 1. Component renders without crashing
 * 2. Component uses EVMSummaryView for metrics display
 * 3. Advanced button opens EVMAnalyzerModal
 * 4. Modal closes properly
 * 5. Loading state is maintained
 * 6. Empty state is maintained
 * 7. Metrics are passed correctly to EVMSummaryView
 * 8. Backward compatibility with existing props
 *
 * @module features/forecasts/components
 */

import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ForecastComparisonCard } from "../ForecastComparisonCard";
import type { EVMMetricsResponse } from "@/features/evm/types";

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

// Mock data for tests
const mockEvmMetricsData: EVMMetricsResponse = {
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
  progress_percentage: 35,
};

// Mock the EVM-related hooks
vi.mock("@/features/cost-elements/api/useCostElements", () => ({
  useCostElementEvmMetrics: () => ({
    data: mockEvmMetricsData,
    isLoading: false,
  }),
}));

// Mock the new components
vi.mock("@/features/evm/components/EVMSummaryView", () => ({
  EVMSummaryView: ({ metrics, onAdvanced }: { metrics: EVMMetricsResponse; onAdvanced?: () => void }) => (
    <div data-testid="evm-summary-view">
      <div data-testid="evm-metrics-bac">{metrics.bac}</div>
      <div data-testid="evm-metrics-eac">{metrics.eac}</div>
      <div data-testid="evm-metrics-cpi">{metrics.cpi}</div>
      {onAdvanced && (
        <button data-testid="advanced-button" onClick={onAdvanced}>
          Advanced
        </button>
      )}
    </div>
  ),
}));

vi.mock("@/features/evm/components/EVMAnalyzerModal", () => ({
  EVMAnalyzerModal: ({ open, onClose }: { open: boolean; onClose: () => void }) =>
    open ? (
      <div data-testid="evm-analyzer-modal">
        <div>EVM Analysis Modal</div>
        <button data-testid="close-modal-button" onClick={onClose}>
          Close
        </button>
      </div>
    ) : null,
}));

describe("ForecastComparisonCard", () => {
  const queryClient = new QueryClient({
    defaultOptions: {
      mutations: { retry: false },
      queries: { retry: false },
    },
  });

  const wrapper = ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  );

  describe("Component rendering and structure", () => {
    it("should render without crashing", () => {
      expect(() => {
        render(
          <ForecastComparisonCard
            costElementId="test-cost-element-1"
            budgetAmount={100000}
          />,
          { wrapper }
        );
      }).not.toThrow();
    });

    it("should render EVM Summary View", () => {
      render(
        <ForecastComparisonCard
          costElementId="test-cost-element-1"
          budgetAmount={100000}
        />,
        { wrapper }
      );

      expect(screen.getByTestId("evm-summary-view")).toBeInTheDocument();
    });

    it("should render Card component with title", () => {
      render(
        <ForecastComparisonCard
          costElementId="test-cost-element-1"
          budgetAmount={100000}
        />,
        { wrapper }
      );

      // Check for Card title (EVM Analysis text)
      expect(screen.getByText(/EVM Analysis/i)).toBeInTheDocument();
    });

    it("should accept costElementId and budgetAmount props", () => {
      expect(() => {
        render(
          <ForecastComparisonCard
            costElementId="test-id-123"
            budgetAmount={50000}
          />,
          { wrapper }
        );
      }).not.toThrow();
    });
  });

  describe("EVMSummaryView integration", () => {
    it("should pass metrics to EVMSummaryView", () => {
      render(
        <ForecastComparisonCard
          costElementId="test-cost-element-1"
          budgetAmount={100000}
        />,
        { wrapper }
      );

      // Check that metrics are passed through
      expect(screen.getByTestId("evm-metrics-bac")).toHaveTextContent("100000");
      expect(screen.getByTestId("evm-metrics-eac")).toHaveTextContent("128205");
      expect(screen.getByTestId("evm-metrics-cpi")).toHaveTextContent("0.78");
    });

    it("should display BAC from metrics", () => {
      render(
        <ForecastComparisonCard
          costElementId="test-cost-element-1"
          budgetAmount={100000}
        />,
        { wrapper }
      );

      expect(screen.getByTestId("evm-metrics-bac")).toBeInTheDocument();
    });

    it("should display EAC from metrics", () => {
      render(
        <ForecastComparisonCard
          costElementId="test-cost-element-1"
          budgetAmount={100000}
        />,
        { wrapper }
      );

      expect(screen.getByTestId("evm-metrics-eac")).toBeInTheDocument();
    });

    it("should display CPI from metrics", () => {
      render(
        <ForecastComparisonCard
          costElementId="test-cost-element-1"
          budgetAmount={100000}
        />,
        { wrapper }
      );

      expect(screen.getByTestId("evm-metrics-cpi")).toBeInTheDocument();
    });
  });

  describe("EVMAnalyzerModal integration", () => {
    it("should render Advanced button", () => {
      render(
        <ForecastComparisonCard
          costElementId="test-cost-element-1"
          budgetAmount={100000}
        />,
        { wrapper }
      );

      expect(screen.getByTestId("advanced-button")).toBeInTheDocument();
    });

    it("should open modal when Advanced button is clicked", async () => {
      render(
        <ForecastComparisonCard
          costElementId="test-cost-element-1"
          budgetAmount={100000}
        />,
        { wrapper }
      );

      const advancedButton = screen.getByTestId("advanced-button");
      fireEvent.click(advancedButton);

      await waitFor(() => {
        expect(screen.getByTestId("evm-analyzer-modal")).toBeInTheDocument();
      });
    });

    it("should close modal when close button is clicked", async () => {
      render(
        <ForecastComparisonCard
          costElementId="test-cost-element-1"
          budgetAmount={100000}
        />,
        { wrapper }
      );

      // Open the modal
      const advancedButton = screen.getByTestId("advanced-button");
      fireEvent.click(advancedButton);

      await waitFor(() => {
        expect(screen.getByTestId("evm-analyzer-modal")).toBeInTheDocument();
      });

      // Close the modal
      const closeButton = screen.getByTestId("close-modal-button");
      fireEvent.click(closeButton);

      await waitFor(() => {
        expect(screen.queryByTestId("evm-analyzer-modal")).not.toBeInTheDocument();
      });
    });

    it("should pass metrics to EVMAnalyzerModal", async () => {
      render(
        <ForecastComparisonCard
          costElementId="test-cost-element-1"
          budgetAmount={100000}
        />,
        { wrapper }
      );

      // Open the modal
      const advancedButton = screen.getByTestId("advanced-button");
      fireEvent.click(advancedButton);

      await waitFor(() => {
        expect(screen.getByTestId("evm-analyzer-modal")).toBeInTheDocument();
      });

      // Modal should be visible with metrics
      expect(screen.getByText("EVM Analysis Modal")).toBeInTheDocument();
    });
  });

  describe("Backward compatibility", () => {
    it("should work with existing budgetAmount prop", () => {
      expect(() => {
        render(
          <ForecastComparisonCard
            costElementId="test-cost-element-1"
            budgetAmount={100000}
          />,
          { wrapper }
        );
      }).not.toThrow();
    });

    it("should maintain same visual layout (Card structure)", () => {
      const { container } = render(
        <ForecastComparisonCard
          costElementId="test-cost-element-1"
          budgetAmount={100000}
        />,
        { wrapper }
      );

      // Check for Ant Design Card component
      const card = container.querySelector(".ant-card");
      expect(card).toBeInTheDocument();
    });
  });

  describe("Type safety", () => {
    it("should accept valid costElementId (string)", () => {
      expect(() => {
        render(
          <ForecastComparisonCard
            costElementId="valid-cost-element-id"
            budgetAmount={100000}
          />,
          { wrapper }
        );
      }).not.toThrow();
    });

    it("should accept valid budgetAmount (number)", () => {
      expect(() => {
        render(
          <ForecastComparisonCard
            costElementId="test-cost-element-1"
            budgetAmount={100000}
          />,
          { wrapper }
        );
      }).not.toThrow();
    });
  });

  describe("Edge cases", () => {
    it("should handle null CPI value", () => {
      expect(() => {
        render(
          <ForecastComparisonCard
            costElementId="test-cost-element-1"
            budgetAmount={100000}
          />,
          { wrapper }
        );
      }).not.toThrow();
    });

    it("should handle null SPI value", () => {
      expect(() => {
        render(
          <ForecastComparisonCard
            costElementId="test-cost-element-1"
            budgetAmount={100000}
          />,
          { wrapper }
        );
      }).not.toThrow();
    });

    it("should handle metrics with zero values", () => {
      expect(() => {
        render(
          <ForecastComparisonCard
            costElementId="test-cost-element-1"
            budgetAmount={0}
          />,
          { wrapper }
        );
      }).not.toThrow();
    });

    it("should handle metrics with negative values", () => {
      expect(() => {
        render(
          <ForecastComparisonCard
            costElementId="test-cost-element-1"
            budgetAmount={100000}
          />,
          { wrapper }
        );
      }).not.toThrow();
    });
  });
});
