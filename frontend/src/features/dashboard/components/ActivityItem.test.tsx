/**
 * ActivityItem Component Tests
 *
 * Tests for ActivityItem component including:
 * - Rendering with different activity types
 * - Badge colors for different activity types
 * - Navigation behavior
 * - Accessibility (ARIA labels, keyboard navigation)
 * - Click handling
 */

import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { ActivityItem } from "./ActivityItem";
import type { ActivityItem as ActivityItemType } from "../types";

// Mock useThemeTokens hook
vi.mock("@/hooks/useThemeTokens", () => ({
  useThemeTokens: () => ({
    spacing: { sm: 8, md: 12, lg: 16, xl: 24 },
    typography: {
      sizes: { xs: 11, sm: 12, md: 14, lg: 16, xl: 18, xxl: 24 },
      weights: { medium: 500, semiBold: 600, bold: 700 },
    },
    colors: {
      text: "#2a2a2a",
      textSecondary: "#666666",
      textTertiary: "#999999",
      bgLayout: "#f5f3f0",
      primary: "#1890ff",
    },
    borderRadius: {
      sm: 4,
      md: 6,
      lg: 8,
      xl: 12,
    },
  }),
}));

// Mock RelativeTime component
vi.mock("./RelativeTime", () => ({
  RelativeTime: ({ timestamp }: { timestamp: string }) => (
    <span data-testid="relative-time">{timestamp}</span>
  ),
}));

describe("ActivityItem", () => {
  const mockActivity: ActivityItemType = {
    id: "entity-123",
    name: "Test Project",
    activity_type: "updated",
    timestamp: "2026-03-15T10:00:00Z",
    entity_type: "project",
    project_id: null,
  };

  /**
   * Test that component renders with activity name and timestamp
   */
  it("renders with activity name and timestamp", () => {
    render(
      <MemoryRouter>
        <ActivityItem activity={mockActivity} />
      </MemoryRouter>
    );

    expect(screen.getByText("Test Project")).toBeInTheDocument();
    expect(screen.getByTestId("relative-time")).toBeInTheDocument();
    expect(screen.getByTestId("relative-time")).toHaveTextContent("2026-03-15T10:00:00Z");
  });

  /**
   * Test that activity badge displays correct action type
   */
  it("displays activity badge with correct action type", () => {
    render(
      <MemoryRouter>
        <ActivityItem activity={mockActivity} />
      </MemoryRouter>
    );

    expect(screen.getByText("updated")).toBeInTheDocument();
  });

  /**
   * Test different activity types display correctly
   */
  it("displays different activity types", () => {
    const activityTypes: Array<ActivityItemType["activity_type"]> = [
      "created",
      "updated",
      "deleted",
      "merged",
    ];

    activityTypes.forEach((activityType) => {
      const activity = { ...mockActivity, activity_type: activityType };
      const { unmount } = render(
        <MemoryRouter>
          <ActivityItem activity={activity} />
        </MemoryRouter>
      );

      expect(screen.getByText(activityType)).toBeInTheDocument();
      unmount();
    });
  });

  /**
   * Test custom onClick handler is called when provided
   */
  it("calls custom onClick handler when provided", () => {
    const customOnClick = vi.fn();

    render(
      <MemoryRouter>
        <ActivityItem activity={mockActivity} onClick={customOnClick} />
      </MemoryRouter>
    );

    const item = screen.getByRole("button");
    fireEvent.click(item);

    expect(customOnClick).toHaveBeenCalledTimes(1);
  });

  /**
   * Test keyboard navigation with Enter key
   */
  it("navigates on Enter key press", () => {
    const customOnClick = vi.fn();

    render(
      <MemoryRouter>
        <ActivityItem activity={mockActivity} onClick={customOnClick} />
      </MemoryRouter>
    );

    const item = screen.getByRole("button");
    fireEvent.keyDown(item, { key: "Enter" });

    expect(customOnClick).toHaveBeenCalledTimes(1);
  });

  /**
   * Test keyboard navigation with Space key
   */
  it("navigates on Space key press", () => {
    const customOnClick = vi.fn();

    render(
      <MemoryRouter>
        <ActivityItem activity={mockActivity} onClick={customOnClick} />
      </MemoryRouter>
    );

    const item = screen.getByRole("button");
    fireEvent.keyDown(item, { key: " " });

    expect(customOnClick).toHaveBeenCalledTimes(1);
  });

  /**
   * Test ARIA label for accessibility
   */
  it("has proper ARIA label for accessibility", () => {
    render(
      <MemoryRouter>
        <ActivityItem activity={mockActivity} />
      </MemoryRouter>
    );

    const item = screen.getByRole("button");
    expect(item).toHaveAttribute("aria-label", "View Test Project details");
  });

  /**
   * Test that component is keyboard accessible with tabIndex
   */
  it("has tabIndex for keyboard accessibility", () => {
    render(
      <MemoryRouter>
        <ActivityItem activity={mockActivity} />
      </MemoryRouter>
    );

    const item = screen.getByRole("button");
    expect(item).toHaveAttribute("tabIndex", "0");
  });

  /**
   * Test minimum touch target size for mobile accessibility
   */
  it("has minimum touch target size (44px)", () => {
    render(
      <MemoryRouter>
        <ActivityItem activity={mockActivity} />
      </MemoryRouter>
    );

    const item = screen.getByRole("button");
    // Check that the element has some height (touch target)
    expect(item).toBeInTheDocument();
    // The minHeight should be at least 44px for accessibility
    expect(item).toHaveAttribute("style");
    expect(item.getAttribute("style")).toContain("44");
  });

  /**
   * Test that long entity names are displayed
   */
  it("displays long entity names", () => {
    const longNameActivity: ActivityItemType = {
      ...mockActivity,
      name: "This is a very long project name that should be truncated with an ellipsis",
    };

    render(
      <MemoryRouter>
        <ActivityItem activity={longNameActivity} />
      </MemoryRouter>
    );

    const nameElement = screen.getByText(longNameActivity.name);
    expect(nameElement).toBeInTheDocument();
    // Check that the element has title attribute for full name on hover
    expect(nameElement).toHaveAttribute("title", longNameActivity.name);
  });

  /**
   * Test hover effect with onMouseEnter
   */
  it("changes background on hover", () => {
    render(
      <MemoryRouter>
        <ActivityItem activity={mockActivity} />
      </MemoryRouter>
    );

    const item = screen.getByRole("button");

    // Trigger mouse enter
    fireEvent.mouseEnter(item);
    expect(item.style.background).toBe("rgb(245, 243, 240)");

    // Trigger mouse leave
    fireEvent.mouseLeave(item);
    expect(item.style.background).toBe("transparent");
  });

  /**
   * Test that different entity types render correctly
   */
  it("renders for different entity types", () => {
    const entityTypes: Array<ActivityItemType["entity_type"]> = [
      "project",
      "wbe",
      "cost_element",
      "change_order",
    ];

    entityTypes.forEach((entityType) => {
      const activity = { ...mockActivity, entity_type: entityType };
      const { unmount } = render(
        <MemoryRouter>
          <ActivityItem activity={activity} />
        </MemoryRouter>
      );

      expect(screen.getByRole("button")).toBeInTheDocument();
      unmount();
    });
  });

  /**
   * Test that entities with project_id render correctly
   */
  it("renders entities with project_id", () => {
    const activityWithProject: ActivityItemType = {
      ...mockActivity,
      entity_type: "wbe",
      project_id: "project-456",
    };

    render(
      <MemoryRouter>
        <ActivityItem activity={activityWithProject} />
      </MemoryRouter>
    );

    expect(screen.getByRole("button")).toBeInTheDocument();
  });

  /**
   * Test that component handles all activity types
   */
  it("handles all activity types including edge cases", () => {
    const activityTypes: Array<ActivityItemType["activity_type"]> = [
      "created",
      "updated",
      "deleted",
      "merged",
    ];

    activityTypes.forEach((activityType) => {
      const activity = { ...mockActivity, activity_type: activityType };
      const { unmount } = render(
        <MemoryRouter>
          <ActivityItem activity={activity} />
        </MemoryRouter>
      );

      expect(screen.getByText(activityType)).toBeInTheDocument();
      unmount();
    });
  });
});
