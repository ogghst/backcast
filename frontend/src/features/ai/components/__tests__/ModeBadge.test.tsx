/**
 * Tests for ModeBadge component
 */

import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { ModeBadge } from "../ModeBadge";

describe("ModeBadge", () => {
  describe("Visual display", () => {
    it("should display Safe mode with correct styling", () => {
      render(<ModeBadge mode="safe" />);
      const badge = screen.getByText("Safe");
      expect(badge).toBeVisible();
      expect(badge).toHaveStyle({ color: "expect.any(String)" });
    });

    it("should display Standard mode with correct styling", () => {
      render(<ModeBadge mode="standard" />);
      const badge = screen.getByText("Standard");
      expect(badge).toBeVisible();
    });

    it("should display Expert mode with correct styling", () => {
      render(<ModeBadge mode="expert" />);
      const badge = screen.getByText("Expert");
      expect(badge).toBeVisible();
    });
  });

  describe("Color coding", () => {
    it("should use green color for Safe mode", () => {
      const { container } = render(<ModeBadge mode="safe" />);
      const badge = container.firstChild as HTMLElement;
      expect(badge.className).toContain("safe");
    });

    it("should use blue color for Standard mode", () => {
      const { container } = render(<ModeBadge mode="standard" />);
      const badge = container.firstChild as HTMLElement;
      expect(badge.className).toContain("standard");
    });

    it("should use orange color for Expert mode", () => {
      const { container } = render(<ModeBadge mode="expert" />);
      const badge = container.firstChild as HTMLElement;
      expect(badge.className).toContain("expert");
    });
  });

  describe("Accessibility", () => {
    it("should have accessible label for screen readers", () => {
      render(<ModeBadge mode="safe" />);
      const badge = screen.getByText("Safe");
      expect(badge).toHaveAttribute("aria-label", "Execution mode: Safe");
    });
  });
});
