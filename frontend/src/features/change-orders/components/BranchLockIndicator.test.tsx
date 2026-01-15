import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import { BranchLockIndicator } from "./BranchLockIndicator";

describe("BranchLockIndicator", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe("locked state", () => {
    it("should render lock icon when locked", () => {
      render(<BranchLockIndicator locked />);
      const lockIcon = document.querySelector(".anticon-lock");
      expect(lockIcon).toBeInTheDocument();
    });

    it("should display text when provided and locked", () => {
      render(<BranchLockIndicator locked text="Branch Locked" />);
      expect(screen.getByText("Branch Locked")).toBeInTheDocument();
    });

    it("should not display text when not provided", () => {
      render(<BranchLockIndicator locked />);
      // Should only show icon
      const lockIcon = document.querySelector(".anticon-lock");
      expect(lockIcon).toBeInTheDocument();
      // Text should not be present
      expect(screen.queryByText("Branch Locked")).not.toBeInTheDocument();
    });

    it("should have locked icon color in inline style", () => {
      const { container } = render(<BranchLockIndicator locked />);
      // Check for lock icon (the span containing the icon)
      const iconSpan = container.querySelector(".anticon-lock");
      expect(iconSpan).toBeInTheDocument();
      // The parent span should have inline style with red color (converted to rgb)
      const styledSpan = container.querySelector("span");
      expect(styledSpan?.getAttribute("style")).toContain("rgb(255, 77, 79)");
    });
  });

  describe("unlocked state", () => {
    it("should render unlock icon when unlocked", () => {
      render(<BranchLockIndicator locked={false} />);
      const unlockIcon = document.querySelector(".anticon-unlock");
      expect(unlockIcon).toBeInTheDocument();
    });

    it("should display text when provided and unlocked", () => {
      render(<BranchLockIndicator locked={false} text="Branch Unlocked" />);
      expect(screen.getByText("Branch Unlocked")).toBeInTheDocument();
    });

    it("should have unlocked icon color in inline style", () => {
      const { container } = render(<BranchLockIndicator locked={false} />);
      // Check for unlock icon (the span containing the icon)
      const iconSpan = container.querySelector(".anticon-unlock");
      expect(iconSpan).toBeInTheDocument();
      // The parent span should have inline style with green color (converted to rgb)
      const styledSpan = container.querySelector("span");
      expect(styledSpan?.getAttribute("style")).toContain("rgb(82, 196, 26)");
    });
  });

  describe("position variant", () => {
    it("should render inline position by default", () => {
      const { container } = render(<BranchLockIndicator locked />);
      // Should not have the standalone div wrapper
      const standaloneDiv = container.querySelector("div[style*='inline-flex']");
      expect(standaloneDiv).not.toBeInTheDocument();
    });

    it("should render standalone position when specified", () => {
      const { container } = render(<BranchLockIndicator locked position="standalone" />);
      // Should have the standalone div wrapper
      const standaloneDiv = container.querySelector("div[style*='inline-flex']");
      expect(standaloneDiv).toBeInTheDocument();
    });
  });
});
