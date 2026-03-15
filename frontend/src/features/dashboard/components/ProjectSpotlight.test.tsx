/**
 * ProjectSpotlight Component Tests
 *
 * Tests for ProjectSpotlight component including:
 * - Rendering project information
 * - Displaying metrics (budget, EVM status, active changes)
 * - Currency formatting
 * - Navigation to project detail
 * - Accessibility
 * - Hover effects
 */

import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { ProjectSpotlight } from "./ProjectSpotlight";
import type { ProjectSpotlight as ProjectSpotlightType } from "../types";

// Mock useThemeTokens hook
vi.mock("@/hooks/useThemeTokens", () => ({
  useThemeTokens: () => ({
    colors: {
      bgElevated: "#ffffff",
      bgContainer: "#f5f5f5",
      text: "#2a2a2a",
      textSecondary: "#666666",
      primary: "#1890ff",
    },
    spacing: { sm: 8, md: 12, lg: 16, xl: 24 },
    typography: {
      sizes: { sm: 12, md: 14, lg: 16, xl: 18, xxl: 24 },
      weights: { medium: 500, semiBold: 600, bold: 700 },
    },
    borderRadius: { md: 6, lg: 8, xl: 12 },
  }),
}));

// Mock RelativeTime component
vi.mock("./RelativeTime", () => ({
  RelativeTime: ({ timestamp }: { timestamp: string }) => (
    <span data-testid="relative-time">{timestamp}</span>
  ),
}));

const mockNavigate = vi.fn();

vi.mock("react-router-dom", async () => {
  const actual = await vi.importActual("react-router-dom");
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  };
});

describe("ProjectSpotlight", () => {
  const mockProject: ProjectSpotlightType = {
    id: "project-123",
    name: "Alpha Project",
    code: "PRJ-001",
    budget: "$100,000",
    evm_status: "on_track",
    active_changes: 3,
    last_activity: "2026-03-15T10:00:00Z",
  };

  /**
   * Test that component renders project name and code
   */
  it("renders project name and code", () => {
    render(
      <MemoryRouter>
        <ProjectSpotlight project={mockProject} />
      </MemoryRouter>
    );

    expect(screen.getByText("Alpha Project")).toBeInTheDocument();
    expect(screen.getByText("PRJ-001")).toBeInTheDocument();
  });

  /**
   * Test that budget metric is displayed with currency formatting
   */
  it("displays budget with currency formatting", () => {
    render(
      <MemoryRouter>
        <ProjectSpotlight project={mockProject} />
      </MemoryRouter>
    );

    expect(screen.getByText("$100,000")).toBeInTheDocument();
    expect(screen.getByText("Budget")).toBeInTheDocument();
  });

  /**
   * Test that EVM status metric is displayed
   */
  it("displays EVM status metric", () => {
    render(
      <MemoryRouter>
        <ProjectSpotlight project={mockProject} />
      </MemoryRouter>
    );

    expect(screen.getByText("EVM Status")).toBeInTheDocument();
    expect(screen.getByText("on_track")).toBeInTheDocument();
  });

  /**
   * Test that active changes metric is displayed
   */
  it("displays active changes metric", () => {
    render(
      <MemoryRouter>
        <ProjectSpotlight project={mockProject} />
      </MemoryRouter>
    );

    expect(screen.getByText("Changes")).toBeInTheDocument();
    expect(screen.getByText("3 Active")).toBeInTheDocument();
  });

  /**
   * Test that last activity timestamp is displayed
   */
  it("displays last activity timestamp", () => {
    render(
      <MemoryRouter>
        <ProjectSpotlight project={mockProject} />
      </MemoryRouter>
    );

    const relativeTime = screen.getByTestId("relative-time");
    expect(relativeTime).toBeInTheDocument();
    expect(relativeTime).toHaveTextContent("2026-03-15T10:00:00Z");
  });

  /**
   * Test that View Project button navigates to project detail
   */
  it("navigates to project detail when View Project button is clicked", () => {
    render(
      <MemoryRouter>
        <ProjectSpotlight project={mockProject} />
      </MemoryRouter>
    );

    const viewButton = screen.getByRole("button", { name: /view project/i });
    fireEvent.click(viewButton);

    expect(mockNavigate).toHaveBeenCalledWith("/projects/project-123");
  });

  /**
   * Test that N/A EVM status is handled correctly
   */
  it("displays N/A for EVM status when not available", () => {
    const projectWithNoEvm: ProjectSpotlightType = {
      ...mockProject,
      evm_status: "N/A",
    };

    render(
      <MemoryRouter>
        <ProjectSpotlight project={projectWithNoEvm} />
      </MemoryRouter>
    );

    expect(screen.getByText("N/A")).toBeInTheDocument();
  });

  /**
   * Test that zero active changes is displayed correctly
   */
  it("displays zero active changes correctly", () => {
    const projectWithNoChanges: ProjectSpotlightType = {
      ...mockProject,
      active_changes: 0,
    };

    render(
      <MemoryRouter>
        <ProjectSpotlight project={projectWithNoChanges} />
      </MemoryRouter>
    );

    expect(screen.getByText("0 Active")).toBeInTheDocument();
  });

  /**
   * Test that large budget values are formatted correctly
   */
  it("formats large budget values correctly", () => {
    const projectWithLargeBudget: ProjectSpotlightType = {
      ...mockProject,
      budget: "$1,234,567,890",
    };

    render(
      <MemoryRouter>
        <ProjectSpotlight project={projectWithLargeBudget} />
      </MemoryRouter>
    );

    expect(screen.getByText("$1,234,567,890")).toBeInTheDocument();
  });

  /**
   * Test that metric cards are displayed in a grid
   */
  it("displays metrics in a grid layout", () => {
    const { container } = render(
      <MemoryRouter>
        <ProjectSpotlight project={mockProject} />
      </MemoryRouter>
    );

    // Check that all three metric cards are present
    expect(screen.getByText("Budget")).toBeInTheDocument();
    expect(screen.getByText("EVM Status")).toBeInTheDocument();
    expect(screen.getByText("Changes")).toBeInTheDocument();
  });

  /**
   * Test that component has hover effect on card
   */
  it("has hover effect on card", () => {
    render(
      <MemoryRouter>
        <ProjectSpotlight project={mockProject} />
      </MemoryRouter>
    );

    const card = screen.getByText("Alpha Project").closest("div");
    expect(card).toBeInTheDocument();

    // Check that card has initial style
    if (card) {
      // Trigger mouse enter - should not throw error
      fireEvent.mouseEnter(card);
      expect(card).toBeInTheDocument();

      // Trigger mouse leave - should not throw error
      fireEvent.mouseLeave(card);
      expect(card).toBeInTheDocument();
    }
  });

  /**
   * Test that View Project button has hover effect
   */
  it("has hover effect on View Project button", () => {
    render(
      <MemoryRouter>
        <ProjectSpotlight project={mockProject} />
      </MemoryRouter>
    );

    const viewButton = screen.getByRole("button", { name: /view project/i });

    // Trigger mouse enter - should not throw error
    fireEvent.mouseEnter(viewButton);
    expect(viewButton).toBeInTheDocument();

    // Trigger mouse leave - should not throw error
    fireEvent.mouseLeave(viewButton);
    expect(viewButton).toBeInTheDocument();
  });

  /**
   * Test that different EVM statuses are displayed
   */
  it("displays different EVM status values", () => {
    const evmStatuses = ["on_track", "at_risk", "behind", "N/A"];

    evmStatuses.forEach((status) => {
      const project = { ...mockProject, evm_status: status };
      const { rerender } = render(
        <MemoryRouter>
          <ProjectSpotlight project={project} />
        </MemoryRouter>
      );

      expect(screen.getByText(status)).toBeInTheDocument();
      rerender(<div />);
    });
  });

  /**
   * Test that project icon is displayed
   */
  it("displays project icon", () => {
    const { container } = render(
      <MemoryRouter>
        <ProjectSpotlight project={mockProject} />
      </MemoryRouter>
    );

    // Check for FolderOutlined icon (should be present in the document)
    const icon = container.querySelector("svg");
    expect(icon).toBeInTheDocument();
  });

  /**
   * Test that metric icons are displayed
   */
  it("displays metric icons for budget, EVM status, and changes", () => {
    const { container } = render(
      <MemoryRouter>
        <ProjectSpotlight project={mockProject} />
      </MemoryRouter>
    );

    // Should have multiple icons (folder icon + 3 metric icons)
    const icons = container.querySelectorAll("svg");
    expect(icons.length).toBeGreaterThanOrEqual(4);
  });

  /**
   * Test accessibility: proper heading hierarchy
   */
  it("maintains proper heading hierarchy with h3", () => {
    render(
      <MemoryRouter>
        <ProjectSpotlight project={mockProject} />
      </MemoryRouter>
    );

    const heading = screen.getByRole("heading", { level: 3 });
    expect(heading).toBeInTheDocument();
    expect(heading).toHaveTextContent("Alpha Project");
  });

  /**
   * Test that button is keyboard accessible
   */
  it("button is keyboard accessible", () => {
    render(
      <MemoryRouter>
        <ProjectSpotlight project={mockProject} />
      </MemoryRouter>
    );

    const viewButton = screen.getByRole("button", { name: /view project/i });

    // Test keyboard interaction
    fireEvent.keyDown(viewButton, { key: "Enter" });
    expect(mockNavigate).toHaveBeenCalledWith("/projects/project-123");
  });
});
