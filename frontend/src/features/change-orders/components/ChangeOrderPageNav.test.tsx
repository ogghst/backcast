import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { ChangeOrderPageNav } from "./ChangeOrderPageNav";

/**
 * T-015: test_page_nav_renders_anchor_links
 *
 * Acceptance Criterion:
 * - Sticky sub-navigation renders with anchor links
 *
 * Purpose:
 * Verify that the ChangeOrderPageNav component renders anchor links
 * for quick navigation to different sections.
 *
 * Expected Behavior:
 * - Anchor links are present for each section
 * - Navigation is sticky/fixed position
 */

describe("ChangeOrderPageNav", () => {
  /**
   * T-015: test_page_nav_renders_anchor_links
   *
   * Test that the page navigation renders anchor links.
   */
  it("test_page_nav_renders_anchor_links", () => {
    // Arrange & Act
    render(
      <MemoryRouter>
        <ChangeOrderPageNav createMode={false} />
      </MemoryRouter>
    );

    // Assert
    expect(screen.getByText("Details")).toBeInTheDocument();
    expect(screen.getByText("Workflow")).toBeInTheDocument();
    expect(screen.getByText("Impact")).toBeInTheDocument();
  });

  /**
   * T-018: test_page_nav_hides_workflow_and_impact_in_create_mode
   *
   * Test that workflow and impact links are hidden in create mode.
   */
  it("test_page_nav_hides_workflow_and_impact_in_create_mode", () => {
    // Arrange & Act
    render(
      <MemoryRouter>
        <ChangeOrderPageNav createMode={true} />
      </MemoryRouter>
    );

    // Assert
    expect(screen.getByText("Details")).toBeInTheDocument();
    expect(screen.queryByText("Workflow")).not.toBeInTheDocument();
    expect(screen.queryByText("Impact")).not.toBeInTheDocument();
  });
});
