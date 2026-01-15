import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { CollapsibleCard } from "./CollapsibleCard";

/**
 * Test collapsible card component functionality.
 */

describe("CollapsibleCard", () => {
  /**
   * Test that card renders with title and content.
   */
  it("renders with title and content", () => {
    render(
      <CollapsibleCard title="Test Title" id="test">
        <div>Test Content</div>
      </CollapsibleCard>
    );

    expect(screen.getByText("Test Title")).toBeInTheDocument();
    expect(screen.getByText("Test Content")).toBeInTheDocument();
  });

  /**
   * Test that card content is visible by default.
   */
  it("content is visible by default", () => {
    render(
      <CollapsibleCard title="Test Title" id="test">
        <div>Test Content</div>
      </CollapsibleCard>
    );

    expect(screen.getByText("Test Content")).toBeVisible();
  });

  /**
   * Test that clicking header toggles content visibility.
   */
  it("toggles content on header click", () => {
    render(
      <CollapsibleCard title="Test Title" id="test">
        <div>Test Content</div>
      </CollapsibleCard>
    );

    const header = screen.getByText("Test Title");

    // Content should be visible initially
    expect(screen.getByText("Test Content")).toBeVisible();

    // Click to collapse - content should be removed from DOM
    fireEvent.click(header);
    expect(screen.queryByText("Test Content")).not.toBeInTheDocument();

    // Click to expand - content should be back in DOM
    fireEvent.click(header);
    expect(screen.getByText("Test Content")).toBeVisible();
  });

  /**
   * Test that collapsed prop sets initial state.
   */
  it("respects collapsed prop for initial state", () => {
    render(
      <CollapsibleCard title="Test Title" id="test" collapsed={true}>
        <div>Test Content</div>
      </CollapsibleCard>
    );

    // Content should not be in DOM when collapsed
    expect(screen.queryByText("Test Content")).not.toBeInTheDocument();
  });

  /**
   * Test that icon indicates collapsed state.
   */
  it("shows collapse icon that indicates state", () => {
    render(
      <CollapsibleCard title="Test Title" id="test">
        <div>Test Content</div>
      </CollapsibleCard>
    );

    const header = screen.getByText("Test Title");

    // Should have a collapse icon button
    const iconButton = screen.getByRole("button");
    expect(iconButton).toBeInTheDocument();

    // Click to collapse - icon should still be present
    fireEvent.click(header);
    expect(screen.getByRole("button")).toBeInTheDocument();
  });

  /**
   * Test that extra prop renders additional header content.
   */
  it("renders extra content in header", () => {
    render(
      <CollapsibleCard
        title="Test Title"
        id="test"
        extra={<span>Extra Content</span>}
      >
        <div>Test Content</div>
      </CollapsibleCard>
    );

    expect(screen.getByText("Extra Content")).toBeInTheDocument();
  });
});
