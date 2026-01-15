import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { ProjectOverview } from "./ProjectOverview";

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

vi.mock("@/features/wbes/api/useWBEs", () => ({
  useWBEs: () => ({
    data: { items: [] },
    isLoading: false,
    refetch: vi.fn(),
  }),
  useCreateWBE: () => ({ mutateAsync: vi.fn() }),
  useUpdateWBE: () => ({ mutateAsync: vi.fn() }),
  useDeleteWBE: () => ({ mutate: vi.fn() }),
}));

vi.mock("@/hooks/useEntityHistory", () => ({
  useEntityHistory: () => ({
    data: [],
    isLoading: false,
  }),
}));

describe("ProjectOverview", () => {
  /**
   * T-Overview-001: test_project_overview_renders_project_details_and_wbes
   *
   * Acceptance Criterion:
   * - ProjectOverview renders project summary and root WBEs
   * - Does NOT render change orders card (moved to separate page)
   *
   * Purpose:
   * Verify that ProjectOverview displays the expected content
   * and that change orders are not displayed inline.
   *
   * Expected Behavior:
   * - Renders page title "Project Details"
   * - Renders "Root Work Breakdown Elements" card
   * - Does NOT render "Change Orders" card
   */
  it("test_project_overview_renders_project_details_and_wbes", () => {
    // Arrange & Act
    render(
      <MemoryRouter initialEntries={["/projects/123"]}>
        <ProjectOverview />
      </MemoryRouter>
    );

    // Assert
    expect(screen.getByText("Project Details")).toBeInTheDocument();
    expect(screen.getByText("Root Work Breakdown Elements")).toBeInTheDocument();
    // Change Orders card should NOT be present
    expect(screen.queryByText("Change Orders")).not.toBeInTheDocument();
  });
});
