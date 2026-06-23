import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { ProjectLayout } from "./ProjectLayout";

describe("ProjectLayout", () => {
  /**
   * T-Layout-001: test_project_layout_renders_outlet
   *
   * Acceptance Criterion:
   * - Layout renders Outlet for nested routes
   *
   * Purpose:
   * Verify that ProjectLayout renders an Outlet for nested route content.
   * Entity-detail navigation is sidebar-owned (Phase 3 nav redesign), so the
   * layout no longer renders an in-page tab strip.
   *
   * Expected Behavior:
   * - Renders child route content via Outlet
   * - Does NOT render in-page navigation tabs
   */
  it("test_project_layout_renders_outlet", () => {
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

    // Assert - child content rendered via Outlet
    expect(screen.getByText("Test Child Content")).toBeInTheDocument();

    // Assert - no in-page tab strip (nav is sidebar-owned)
    expect(screen.queryByRole("tab", { name: "Overview" })).not.toBeInTheDocument();
    expect(screen.queryByRole("tab", { name: "Change Orders" })).not.toBeInTheDocument();
    expect(screen.queryByRole("tab", { name: "EVM Analysis" })).not.toBeInTheDocument();
  });
});
