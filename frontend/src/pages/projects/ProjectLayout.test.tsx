import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { ProjectLayout } from "./ProjectLayout";

describe("ProjectLayout", () => {
  /**
   * T-Layout-001: test_project_layout_renders_navigation_and_outlet
   *
   * Acceptance Criterion:
   * - Layout renders PageNavigation with configured items
   * - Layout renders Outlet for nested routes
   *
   * Purpose:
   * Verify that ProjectLayout renders the PageNavigation component
   * and provides an Outlet for nested route content.
   *
   * Expected Behavior:
   * - Renders navigation tabs ("Overview", "Change Orders", "EVM Analysis")
   * - Renders child route content via Outlet
   */
  it("test_project_layout_renders_navigation_and_outlet", () => {
    // Arrange
    const TestChild = () => <div>Test Child Content</div>;

    // Act
    render(
      <MemoryRouter initialEntries={["/projects/123"]}>
        <Routes>
          <Route path="/projects/:projectId" element={<ProjectLayout />}>
            <Route index element={<TestChild />} />
          </Route>
        </Routes>
      </MemoryRouter>
    );

    // Assert
    expect(screen.getByRole("tab", { name: "Overview" })).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: "Change Orders" })).toBeInTheDocument();
    expect(screen.getByText("Test Child Content")).toBeInTheDocument();
  });

  /**
   * T-001: test_project_layout_renders_evm_analysis_tab
   *
   * Acceptance Criterion:
   * - "EVM Analysis" tab visible in navigation
   *
   * Purpose:
   * Verify that ProjectLayout renders the EVM Analysis navigation tab
   * allowing users to navigate to the project-level EVM analysis page.
   *
   * Expected Behavior:
   * - Renders "EVM Analysis" tab
   */
  it("test_project_layout_renders_evm_analysis_tab", () => {
    // Arrange
    const TestChild = () => <div>Test Child Content</div>;

    // Act
    render(
      <MemoryRouter initialEntries={["/projects/123"]}>
        <Routes>
          <Route path="/projects/:projectId" element={<ProjectLayout />}>
            <Route index element={<TestChild />} />
          </Route>
        </Routes>
      </MemoryRouter>
    );

    // Assert
    expect(screen.getByRole("tab", { name: "EVM Analysis" })).toBeInTheDocument();
  });
});
