/**
 * BudgetSettingsWidget Component Tests
 *
 * Tests for the budget settings configuration widget,
 * including the enforce_budget checkbox.
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import React from "react";
import { BudgetSettingsWidget } from "./BudgetSettingsWidget";

// Mock the hooks
vi.mock("../api/useProjectBudgetSettings", () => ({
  useProjectBudgetSettings: vi.fn(),
  useUpdateProjectBudgetSettings: vi.fn(),
}));

// Mock useThemeTokens hook
vi.mock("@/hooks/useThemeTokens", () => ({
  useThemeTokens: () => ({
    spacing: { xs: 4, sm: 8, md: 16, lg: 24, xl: 32, xxl: 40 },
    typography: {
      sizes: { xs: 10, sm: 12, md: 14, lg: 16, xl: 20, xxl: 24 },
      weights: { normal: 400, medium: 500, semiBold: 600, bold: 700 },
    },
    borderRadius: { sm: 4, md: 6, lg: 8, xl: 12 },
    colors: {
      primary: "#1890ff",
      success: "#52c41a",
      warning: "#faad14",
      error: "#ff4d4f",
      info: "#1890ff",
      textSecondary: "#666666",
      text: { primary: "#000000", secondary: "#666666" },
      border: "#d9d9d9",
      borderSecondary: "#f0f0f0",
      background: { default: "#f0f0f0" },
    },
  }),
}));

import {
  useProjectBudgetSettings,
  useUpdateProjectBudgetSettings,
} from "../api/useProjectBudgetSettings";

const mockUseProjectBudgetSettings = vi.mocked(useProjectBudgetSettings);
const mockUseUpdateProjectBudgetSettings = vi.mocked(
  useUpdateProjectBudgetSettings,
);

describe("BudgetSettingsWidget", () => {
  let queryClient: QueryClient;

  beforeEach(() => {
    vi.clearAllMocks();
    queryClient = new QueryClient({
      defaultOptions: {
        queries: { retry: false },
        mutations: { retry: false },
      },
    });

    mockUseProjectBudgetSettings.mockReturnValue({
      data: {
        id: "settings-1",
        project_budget_settings_id: "pbs-1",
        project_id: "project-123",
        created_by: "user-1",
        warning_threshold_percent: "80.0",
        allow_project_admin_override: true,
        enforce_budget: false,
      },
      isLoading: false,
      isError: false,
      error: null,
      isSuccess: true,
    } as ReturnType<typeof useProjectBudgetSettings>);

    mockUseUpdateProjectBudgetSettings.mockReturnValue({
      mutate: vi.fn(),
      isPending: false,
    } as ReturnType<typeof useUpdateProjectBudgetSettings>);
  });

  const createWrapper = () => {
    return ({ children }: { children: React.ReactNode }) =>
      React.createElement(
        QueryClientProvider,
        { client: queryClient },
        children,
      );
  };

  it("should render the enforce budget checkbox", () => {
    render(<BudgetSettingsWidget projectId="project-123" />, {
      wrapper: createWrapper(),
    });

    expect(
      screen.getByRole("checkbox", {
        name: /enforce budget limits/i,
      }),
    ).toBeInTheDocument();
  });

  it("should render the enforce budget checkbox with correct label text", () => {
    render(<BudgetSettingsWidget projectId="project-123" />, {
      wrapper: createWrapper(),
    });

    expect(
      screen.getByText("Enforce budget limits (block over-budget registrations)"),
    ).toBeInTheDocument();
  });

  it("should render the warning threshold field", () => {
    render(<BudgetSettingsWidget projectId="project-123" />, {
      wrapper: createWrapper(),
    });

    expect(
      screen.getByText("Warning Threshold (%)"),
    ).toBeInTheDocument();
  });

  it("should render the allow override checkbox", () => {
    render(<BudgetSettingsWidget projectId="project-123" />, {
      wrapper: createWrapper(),
    });

    expect(
      screen.getByRole("checkbox", {
        name: /allow project admins to override/i,
      }),
    ).toBeInTheDocument();
  });
});
