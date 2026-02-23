/**
 * ChangeOrderAnalytics Component Tests
 *
 * Tests for the main analytics dashboard component.
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import React from "react";
import { ChangeOrderAnalytics } from "../ChangeOrderAnalytics";

// Mock the useChangeOrderStats hook
const mockStats = {
  total_count: 5,
  total_cost_exposure: 190000,
  pending_value: 85000,
  approved_value: 100000,
  by_status: [
    { status: "Draft", count: 1, total_value: 10000 },
    { status: "Submitted for Approval", count: 1, total_value: 25000 },
    { status: "Under Review", count: 1, total_value: 50000 },
    { status: "Approved", count: 1, total_value: 100000 },
    { status: "Rejected", count: 1, total_value: 5000 },
  ],
  by_impact_level: [
    { impact_level: "LOW", count: 2, total_value: 15000 },
    { impact_level: "MEDIUM", count: 1, total_value: 25000 },
    { impact_level: "HIGH", count: 1, total_value: 50000 },
    { impact_level: "CRITICAL", count: 1, total_value: 100000 },
  ],
  cost_trend: [
    { trend_date: "2026-01-01", cumulative_value: 50000, count: 2 },
    { trend_date: "2026-01-08", cumulative_value: 190000, count: 5 },
  ],
  avg_approval_time_days: 7.5,
  approval_workload: [
    {
      approver_id: "approver-1",
      approver_name: "John Doe",
      pending_count: 2,
      overdue_count: 1,
      avg_days_waiting: 3.5,
    },
  ],
  aging_items: [
    {
      change_order_id: "co-1",
      code: "CO-2026-001",
      title: "Aging CO 1",
      status: "Under Review",
      days_in_status: 12,
      impact_level: "HIGH",
      sla_status: "overdue",
    },
  ],
  aging_threshold_days: 7,
};

vi.mock("@/features/change-orders/api/useChangeOrderStats", () => ({
  useChangeOrderStats: vi.fn(),
}));

// Mock child chart components
vi.mock("../StatusDistributionChart", () => ({
  StatusDistributionChart: ({ data }: { data: unknown[] }) =>
    React.createElement("div", { "data-testid": "status-chart" }, `Status Chart: ${data.length} items`),
}));

vi.mock("../ImpactLevelChart", () => ({
  ImpactLevelChart: ({ data }: { data: unknown[] }) =>
    React.createElement("div", { "data-testid": "impact-chart" }, `Impact Chart: ${data.length} items`),
}));

vi.mock("../CostTrendChart", () => ({
  CostTrendChart: ({ data }: { data: unknown[] }) =>
    React.createElement("div", { "data-testid": "cost-trend-chart" }, `Trend Chart: ${data.length} points`),
}));

vi.mock("../ApprovalWorkloadTable", () => ({
  ApprovalWorkloadTable: ({ data }: { data: unknown[] }) =>
    React.createElement("div", { "data-testid": "approval-table" }, `Workload: ${data.length} approvers`),
}));

vi.mock("../AgingItemsList", () => ({
  AgingItemsList: ({ data }: { data: unknown[] }) =>
    React.createElement("div", { "data-testid": "aging-list" }, `Aging: ${data.length} items`),
}));

// Mock antd components for simpler testing
vi.mock("antd", async () => {
  const actual = await vi.importActual("antd");
  return {
    ...actual,
    Spin: ({ tip }: { tip: string }) =>
      React.createElement("div", { "data-testid": "loading-spinner" }, tip),
    Alert: ({ type, message }: { type: string; message: string }) =>
      React.createElement("div", { "data-testid": `alert-${type}` }, message),
    Empty: ({ description }: { description: string }) =>
      React.createElement("div", { "data-testid": "empty-state" }, description),
  };
});

import { useChangeOrderStats } from "@/features/change-orders/api/useChangeOrderStats";

const mockUseChangeOrderStats = vi.mocked(useChangeOrderStats);

describe("ChangeOrderAnalytics", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe("Loading State", () => {
    it("shows loading spinner while data is loading", () => {
      mockUseChangeOrderStats.mockReturnValue({
        data: undefined,
        isLoading: true,
        error: null,
      } as ReturnType<typeof useChangeOrderStats>);

      render(<ChangeOrderAnalytics projectId="test-project-id" />);

      expect(screen.getByTestId("loading-spinner")).toBeInTheDocument();
      expect(screen.getByText("Loading analytics...")).toBeInTheDocument();
    });
  });

  describe("Error State", () => {
    it("shows error alert when data fetch fails", () => {
      const errorMessage = "Failed to fetch analytics";
      mockUseChangeOrderStats.mockReturnValue({
        data: undefined,
        isLoading: false,
        error: new Error(errorMessage),
      } as ReturnType<typeof useChangeOrderStats>);

      render(<ChangeOrderAnalytics projectId="test-project-id" />);

      expect(screen.getByTestId("alert-error")).toBeInTheDocument();
      expect(screen.getByText("Error loading analytics")).toBeInTheDocument();
    });
  });

  describe("Empty State", () => {
    it("shows empty state when no data available", () => {
      mockUseChangeOrderStats.mockReturnValue({
        data: undefined,
        isLoading: false,
        error: null,
      } as ReturnType<typeof useChangeOrderStats>);

      render(<ChangeOrderAnalytics projectId="test-project-id" />);

      expect(screen.getByTestId("empty-state")).toBeInTheDocument();
      expect(screen.getByText("No analytics data available")).toBeInTheDocument();
    });
  });

  describe("Rendering with Mock Data", () => {
    it("renders all KPI cards with correct labels", () => {
      mockUseChangeOrderStats.mockReturnValue({
        data: mockStats,
        isLoading: false,
        error: null,
      } as ReturnType<typeof useChangeOrderStats>);

      render(<ChangeOrderAnalytics projectId="test-project-id" />);

      // Check KPI card labels exist
      expect(screen.getByText("Total Change Orders")).toBeInTheDocument();
      expect(screen.getByText("Total Cost Exposure")).toBeInTheDocument();
      expect(screen.getByText("Pending Value")).toBeInTheDocument();
      expect(screen.getByText("Approved Value")).toBeInTheDocument();
    });

    it("renders all chart components", () => {
      mockUseChangeOrderStats.mockReturnValue({
        data: mockStats,
        isLoading: false,
        error: null,
      } as ReturnType<typeof useChangeOrderStats>);

      render(<ChangeOrderAnalytics projectId="test-project-id" />);

      expect(screen.getByTestId("status-chart")).toBeInTheDocument();
      expect(screen.getByTestId("impact-chart")).toBeInTheDocument();
      expect(screen.getByTestId("cost-trend-chart")).toBeInTheDocument();
    });

    it("renders approval workload table", () => {
      mockUseChangeOrderStats.mockReturnValue({
        data: mockStats,
        isLoading: false,
        error: null,
      } as ReturnType<typeof useChangeOrderStats>);

      render(<ChangeOrderAnalytics projectId="test-project-id" />);

      expect(screen.getByTestId("approval-table")).toBeInTheDocument();
      expect(screen.getByText(/Workload: 1 approvers/)).toBeInTheDocument();
    });

    it("renders aging items list", () => {
      mockUseChangeOrderStats.mockReturnValue({
        data: mockStats,
        isLoading: false,
        error: null,
      } as ReturnType<typeof useChangeOrderStats>);

      render(<ChangeOrderAnalytics projectId="test-project-id" />);

      expect(screen.getByTestId("aging-list")).toBeInTheDocument();
      expect(screen.getByText(/Aging: 1 items/)).toBeInTheDocument();
    });

    it("renders average approval time when available", () => {
      mockUseChangeOrderStats.mockReturnValue({
        data: mockStats,
        isLoading: false,
        error: null,
      } as ReturnType<typeof useChangeOrderStats>);

      render(<ChangeOrderAnalytics projectId="test-project-id" />);

      expect(screen.getByText("Average Approval Time (Historical)")).toBeInTheDocument();
      // Check that "days" suffix is displayed
      expect(screen.getByText("days")).toBeInTheDocument();
    });

    it("hides average approval time when null", () => {
      mockUseChangeOrderStats.mockReturnValue({
        data: { ...mockStats, avg_approval_time_days: null },
        isLoading: false,
        error: null,
      } as ReturnType<typeof useChangeOrderStats>);

      render(<ChangeOrderAnalytics projectId="test-project-id" />);

      expect(screen.queryByText("Average Approval Time (Historical)")).not.toBeInTheDocument();
    });
  });

  describe("Props Handling", () => {
    it("calls useChangeOrderStats with correct project ID", () => {
      mockUseChangeOrderStats.mockReturnValue({
        data: mockStats,
        isLoading: false,
        error: null,
      } as ReturnType<typeof useChangeOrderStats>);

      render(<ChangeOrderAnalytics projectId="custom-project-123" />);

      expect(mockUseChangeOrderStats).toHaveBeenCalledWith(
        expect.objectContaining({
          projectId: "custom-project-123",
        })
      );
    });

    it("passes branch prop to hook", () => {
      mockUseChangeOrderStats.mockReturnValue({
        data: mockStats,
        isLoading: false,
        error: null,
      } as ReturnType<typeof useChangeOrderStats>);

      render(<ChangeOrderAnalytics projectId="test-project" branch="feature-branch" />);

      expect(mockUseChangeOrderStats).toHaveBeenCalledWith(
        expect.objectContaining({
          projectId: "test-project",
          branch: "feature-branch",
        })
      );
    });

    it("uses default branch 'main' when not specified", () => {
      mockUseChangeOrderStats.mockReturnValue({
        data: mockStats,
        isLoading: false,
        error: null,
      } as ReturnType<typeof useChangeOrderStats>);

      render(<ChangeOrderAnalytics projectId="test-project" />);

      expect(mockUseChangeOrderStats).toHaveBeenCalledWith(
        expect.objectContaining({
          branch: "main",
        })
      );
    });
  });

  describe("Currency Formatting", () => {
    it("formats large numbers with proper currency format", () => {
      mockUseChangeOrderStats.mockReturnValue({
        data: {
          ...mockStats,
          total_cost_exposure: 1500000,
        },
        isLoading: false,
        error: null,
      } as ReturnType<typeof useChangeOrderStats>);

      render(<ChangeOrderAnalytics projectId="test-project-id" />);

      // Should show Total Cost Exposure label
      expect(screen.getByText("Total Cost Exposure")).toBeInTheDocument();
    });

    it("handles zero values correctly", () => {
      mockUseChangeOrderStats.mockReturnValue({
        data: {
          ...mockStats,
          total_count: 0,
          total_cost_exposure: 0,
          pending_value: 0,
          approved_value: 0,
        },
        isLoading: false,
        error: null,
      } as ReturnType<typeof useChangeOrderStats>);

      render(<ChangeOrderAnalytics projectId="test-project-id" />);

      // Check for KPI card labels exist
      expect(screen.getByText("Total Change Orders")).toBeInTheDocument();
      expect(screen.getByText("Total Cost Exposure")).toBeInTheDocument();
    });
  });

  describe("Edge Cases", () => {
    it("handles empty arrays in stats data", () => {
      mockUseChangeOrderStats.mockReturnValue({
        data: {
          ...mockStats,
          by_status: [],
          by_impact_level: [],
          cost_trend: [],
          approval_workload: [],
          aging_items: [],
        },
        isLoading: false,
        error: null,
      } as ReturnType<typeof useChangeOrderStats>);

      render(<ChangeOrderAnalytics projectId="test-project-id" />);

      // Should still render main KPIs
      expect(screen.getByText("Total Change Orders")).toBeInTheDocument();

      // Charts should show 0 items
      expect(screen.getByText("Status Chart: 0 items")).toBeInTheDocument();
      expect(screen.getByText("Impact Chart: 0 items")).toBeInTheDocument();
    });
  });
});
