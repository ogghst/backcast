/**
 * Tests for AskUserModal component
 *
 * Verifies the client-side countdown (driven by `expiresAt`):
 * - renders the progress bar / countdown text when a deadline is in the near future
 * - auto-calls onCancel when the deadline is in the past or elapses
 * - renders normally (no countdown UI) when `expiresAt` is absent
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, fireEvent, act } from "@testing-library/react";
import { AskUserModal } from "../ChatInterface";

describe("AskUserModal", () => {
  beforeEach(() => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date("2026-03-22T12:00:00Z"));
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  describe("Rendering", () => {
    it("renders the question when open without a deadline", () => {
      render(
        <AskUserModal
          open={true}
          request={{
            question: "What is the project name?",
            askId: "ask-1",
          }}
          onSubmit={vi.fn()}
          onCancel={vi.fn()}
        />,
      );

      expect(screen.getByText("What is the project name?")).toBeVisible();
      // No countdown UI without expiresAt
      expect(screen.queryByText(/auto-expiring in/i)).not.toBeInTheDocument();
    });

    it("renders countdown text and progress bar when expiresAt is in the near future", () => {
      // 30s in the future, 60s window
      const expiresAt = new Date(Date.now() + 30_000).toISOString();
      render(
        <AskUserModal
          open={true}
          request={{
            question: "Pick an option",
            askId: "ask-2",
            expiresAt,
            timeoutSeconds: 60,
          }}
          onSubmit={vi.fn()}
          onCancel={vi.fn()}
        />,
      );

      expect(screen.getByText(/auto-expiring in 30s/i)).toBeVisible();
    });

    it("renders option buttons", () => {
      const expiresAt = new Date(Date.now() + 60_000).toISOString();
      render(
        <AskUserModal
          open={true}
          request={{
            question: "Choose",
            askId: "ask-3",
            options: ["Red", "Blue"],
            expiresAt,
            timeoutSeconds: 60,
          }}
          onSubmit={vi.fn()}
          onCancel={vi.fn()}
        />,
      );

      expect(screen.getByText("Red")).toBeVisible();
      expect(screen.getByText("Blue")).toBeVisible();
    });
  });

  describe("Countdown behavior", () => {
    it("auto-calls onCancel when the deadline is already in the past", () => {
      const onCancel = vi.fn();
      // 10s in the past
      const expiresAt = new Date(Date.now() - 10_000).toISOString();
      render(
        <AskUserModal
          open={true}
          request={{
            question: "Expired prompt",
            askId: "ask-4",
            expiresAt,
            timeoutSeconds: 60,
          }}
          onSubmit={vi.fn()}
          onCancel={onCancel}
        />,
      );

      // The auto-cancel effect runs after the first state settle.
      expect(onCancel).toHaveBeenCalled();
    });

    it("auto-calls onCancel when the deadline elapses during display", async () => {
      const onCancel = vi.fn();
      // 2s in the future, 60s window
      const expiresAt = new Date(Date.now() + 2_000).toISOString();
      render(
        <AskUserModal
          open={true}
          request={{
            question: "Soon to expire",
            askId: "ask-5",
            expiresAt,
            timeoutSeconds: 60,
          }}
          onSubmit={vi.fn()}
          onCancel={onCancel}
        />,
      );

      expect(onCancel).not.toHaveBeenCalled();

      // Advance past the deadline and flush the resulting state update.
      await act(async () => {
        vi.advanceTimersByTime(3_000);
      });

      expect(onCancel).toHaveBeenCalledTimes(1);
    });

    it("fires onCancel only once", async () => {
      const onCancel = vi.fn();
      const expiresAt = new Date(Date.now() - 1_000).toISOString();
      render(
        <AskUserModal
          open={true}
          request={{
            question: "Expired",
            askId: "ask-6",
            expiresAt,
            timeoutSeconds: 60,
          }}
          onSubmit={vi.fn()}
          onCancel={onCancel}
        />,
      );

      // Several interval ticks after expiry should not produce extra calls.
      await act(async () => {
        vi.advanceTimersByTime(5_000);
      });

      expect(onCancel).toHaveBeenCalledTimes(1);
    });
  });

  describe("User interactions", () => {
    it("calls onSubmit with the option when an option button is clicked", () => {
      const onSubmit = vi.fn();
      render(
        <AskUserModal
          open={true}
          request={{
            question: "Choose",
            askId: "ask-7",
            options: ["Yes", "No"],
          }}
          onSubmit={onSubmit}
          onCancel={vi.fn()}
        />,
      );

      fireEvent.click(screen.getByText("Yes"));

      expect(onSubmit).toHaveBeenCalledWith("Yes");
    });

    it("calls onCancel when Cancel button is clicked", () => {
      const onCancel = vi.fn();
      render(
        <AskUserModal
          open={true}
          request={{
            question: "Q",
            askId: "ask-8",
          }}
          onSubmit={vi.fn()}
          onCancel={onCancel}
        />,
      );

      fireEvent.click(screen.getByRole("button", { name: /cancel/i }));

      expect(onCancel).toHaveBeenCalledTimes(1);
    });
  });
});
