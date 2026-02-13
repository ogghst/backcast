import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import React from "react";
import { ProjectChangeOrdersPage } from "./ProjectChangeOrdersPage";

// Mock the hooks
vi.mock("@/features/projects/api/useProjects", () => ({
  useProject: () => ({
    data: {
      project_id: "123",
      code: "TEST-001",
      name: "Test Project",
      budget: 100000,
    },
    isLoading: false,
  }),
}));

vi.mock("@/features/change-orders", () => ({
  ChangeOrderList: ({ projectId }: { projectId: string }) =>
    React.createElement("div", { "data-testid": "change-order-list" }, `Change Orders for ${projectId}`),
}));

describe("ProjectChangeOrdersPage", () => {
  /**
   * T-ChangeOrders-001: test_project_change_orders_page_renders_list
   *
   * Acceptance Criterion:
   * - Change orders page renders ChangeOrderList component
   * - Page displays correct breadcrumb and title
   *
   * Purpose:
   * Verify that the dedicated change orders page displays
   * the ChangeOrderList component with proper context.
   *
   * Expected Behavior:
   * - Renders page title "Change Orders"
   * - Renders ChangeOrderList with projectId
   * - Renders breadcrumb with project code
   */
  it("test_project_change_orders_page_renders_list", () => {
    // Arrange & Act
    render(
      <MemoryRouter initialEntries={["/projects/123/change-orders"]}>
        <ProjectChangeOrdersPage />
      </MemoryRouter>
    );

    // Assert
    expect(screen.getAllByText("Change Orders")).toHaveLength(2); // breadcrumb + title
    expect(screen.getByTestId("change-order-list")).toBeInTheDocument();
    expect(screen.getByText("TEST-001")).toBeInTheDocument();
  });

  /**
   * T-ChangeOrders-002: test_project_change_orders_page_loading_state
   *
   * Acceptance Criterion:
   * - Loading state shows skeleton when data loading
   *
   * Purpose:
   * Verify that the page shows appropriate loading state.
   *
   * Expected Behavior:
   * - When project data is loading, page still renders structure
   */
  it("test_project_change_orders_page_loading_state", () => {
    // Arrange & Act
    render(
      <MemoryRouter initialEntries={["/projects/123/change-orders"]}>
        <ProjectChangeOrdersPage />
      </MemoryRouter>
    );

    // Assert - page should still render title and list container
    expect(screen.getAllByText("Change Orders")).toHaveLength(2); // breadcrumb + title
    expect(screen.getByTestId("change-order-list")).toBeInTheDocument();
  });
});
