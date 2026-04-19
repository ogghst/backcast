import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook } from "@testing-library/react";

import { useSearchShortcut } from "../useSearchShortcut";

describe("useSearchShortcut", () => {
  const mockOnOpen = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("calls onOpen on Cmd+K", () => {
    renderHook(() => useSearchShortcut(mockOnOpen));

    const event = new KeyboardEvent("keydown", {
      key: "k",
      metaKey: true,
      bubbles: true,
    });
    window.dispatchEvent(event);

    expect(mockOnOpen).toHaveBeenCalledOnce();
  });

  it("calls onOpen on Ctrl+K", () => {
    renderHook(() => useSearchShortcut(mockOnOpen));

    const event = new KeyboardEvent("keydown", {
      key: "k",
      ctrlKey: true,
      bubbles: true,
    });
    window.dispatchEvent(event);

    expect(mockOnOpen).toHaveBeenCalledOnce();
  });

  it("does not call onOpen on regular K", () => {
    renderHook(() => useSearchShortcut(mockOnOpen));

    const event = new KeyboardEvent("keydown", {
      key: "k",
      bubbles: true,
    });
    window.dispatchEvent(event);

    expect(mockOnOpen).not.toHaveBeenCalled();
  });

  it("cleans up listener on unmount", () => {
    const addSpy = vi.spyOn(window, "addEventListener");
    const removeSpy = vi.spyOn(window, "removeEventListener");

    const { unmount } = renderHook(() => useSearchShortcut(mockOnOpen));

    expect(addSpy).toHaveBeenCalledWith("keydown", expect.any(Function));

    unmount();

    expect(removeSpy).toHaveBeenCalledWith("keydown", expect.any(Function));

    // After unmount, Cmd+K should not trigger the callback
    const event = new KeyboardEvent("keydown", {
      key: "k",
      metaKey: true,
      bubbles: true,
    });
    window.dispatchEvent(event);

    // onOpen was never called (the unmount cleaned it up before we dispatched)
    expect(mockOnOpen).not.toHaveBeenCalled();

    addSpy.mockRestore();
    removeSpy.mockRestore();
  });
});
