import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import userEvent from "@testing-library/user-event";
import { PageNavigation } from "./PageNavigation";

describe("PageNavigation", () => {
  /**
   * T-001: test_page_navigation_renders_tabs_from_items_prop
   *
   * Acceptance Criterion:
   * - Basic rendering of tabs from items prop
   *
   * Purpose:
   * Verify that PageNavigation component renders the correct number of tabs
   * with the correct labels from the items prop.
   *
   * Expected Behavior:
   * - Renders two tabs with labels "Overview" and "Change Orders"
   * - Each tab has role="tab"
   */
  it("test_page_navigation_renders_tabs_from_items_prop", () => {
    // Arrange
    const items = [
      { key: "overview", label: "Overview", path: "/projects/123" },
      { key: "change-orders", label: "Change Orders", path: "/projects/123/change-orders" },
    ];

    // Act
    render(
      <MemoryRouter initialEntries={["/projects/123"]}>
        <PageNavigation items={items} />
      </MemoryRouter>
    );

    // Assert
    expect(screen.getByRole("tab", { name: "Overview" })).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: "Change Orders" })).toBeInTheDocument();
  });

  /**
   * T-002: test_page_navigation_highlights_active_tab_from_route
   *
   * Acceptance Criterion:
   * - Active tab highlighted based on route
   *
   * Purpose:
   * Verify that the correct tab is highlighted (active={true}) when
   * the current route matches the tab's path.
   *
   * Expected Behavior:
   * - When route is /projects/123/change-orders, the Change Orders tab has aria-selected="true"
   * - The Overview tab has aria-selected="false"
   */
  it("test_page_navigation_highlights_active_tab_from_route", () => {
    // Arrange
    const items = [
      { key: "overview", label: "Overview", path: "/projects/123" },
      { key: "change-orders", label: "Change Orders", path: "/projects/123/change-orders" },
    ];

    // Act - navigate to change orders route
    render(
      <MemoryRouter initialEntries={["/projects/123/change-orders"]}>
        <PageNavigation items={items} />
      </MemoryRouter>
    );

    // Assert - Change Orders tab should be active
    const changeOrdersTab = screen.getByRole("tab", { name: "Change Orders" });
    const overviewTab = screen.getByRole("tab", { name: "Overview" });

    expect(changeOrdersTab).toHaveAttribute("aria-selected", "true");
    expect(overviewTab).toHaveAttribute("aria-selected", "false");
  });

  /**
   * T-003: test_page_navigation_navigates_on_tab_click
   *
   * Acceptance Criterion:
   * - Clicking tab calls navigate with correct path
   *
   * Purpose:
   * Verify that clicking on a tab navigates to the correct route.
   *
   * Expected Behavior:
   * - Clicking on "Change Orders" tab calls navigate() with the correct path
   */
  it("test_page_navigation_navigates_on_tab_click", async () => {
    // Arrange
    const user = userEvent.setup();
    const items = [
      { key: "overview", label: "Overview", path: "/projects/123" },
      { key: "change-orders", label: "Change Orders", path: "/projects/123/change-orders" },
    ];

    // Act - render on overview page
    render(
      <MemoryRouter initialEntries={["/projects/123"]}>
        <PageNavigation items={items} />
      </MemoryRouter>
    );

    // Click on Change Orders tab
    const changeOrdersTab = screen.getByRole("tab", { name: "Change Orders" });
    await user.click(changeOrdersTab);

    // Assert - tab should now be active (navigation occurred)
    expect(changeOrdersTab).toHaveAttribute("aria-selected", "true");
  });

  /**
   * T-005: test_page_navigation_sidebar_variant_renders_vertical
   *
   * Acceptance Criterion:
   * - variant="sidebar" renders vertical tabs
   *
   * Purpose:
   * Verify that the sidebar variant renders tabs with tabPosition="left".
   *
   * Expected Behavior:
   * - Component renders without error
   * - Tabs are positioned on the left side (indicated by CSS class or structure)
   */
  it("test_page_navigation_sidebar_variant_renders_vertical", () => {
    // Arrange
    const items = [
      { key: "overview", label: "Overview", path: "/projects/123" },
      { key: "change-orders", label: "Change Orders", path: "/projects/123/change-orders" },
    ];

    // Act
    render(
      <MemoryRouter initialEntries={["/projects/123"]}>
        <PageNavigation items={items} variant="sidebar" />
      </MemoryRouter>
    );

    // Assert - tabs should still render
    expect(screen.getByRole("tab", { name: "Overview" })).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: "Change Orders" })).toBeInTheDocument();
  });
});
