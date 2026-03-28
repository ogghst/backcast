/**
 * Tests for useExecutionMode hook
 *
 * T-010: Mode persists across sessions
 */

import { renderHook, act } from "@testing-library/react";
import { useExecutionMode } from "../useExecutionMode";
import type { ExecutionMode } from "../../chat/types";

describe("useExecutionMode", () => {
  const LOCAL_STORAGE_KEY = "ai_execution_mode";

  beforeEach(() => {
    // Clear localStorage before each test
    localStorage.clear();
  });

  afterEach(() => {
    // Cleanup after each test
    localStorage.clear();
  });

  describe("T-010: Mode persistence", () => {
    it("should default to 'standard' when no value in localStorage", () => {
      const { result } = renderHook(() => useExecutionMode());

      expect(result.current.executionMode).toBe("standard");
    });

    it("should load existing mode from localStorage", () => {
      // Save mode to localStorage
      localStorage.setItem(LOCAL_STORAGE_KEY, "safe");

      const { result } = renderHook(() => useExecutionMode());

      expect(result.current.executionMode).toBe("safe");
    });

    it("should save mode to localStorage when changed", () => {
      const { result } = renderHook(() => useExecutionMode());

      // Change mode to expert
      act(() => {
        result.current.setExecutionMode("expert");
      });

      // Verify localStorage was updated
      expect(localStorage.getItem(LOCAL_STORAGE_KEY)).toBe("expert");
      expect(result.current.executionMode).toBe("expert");
    });

    it("should persist mode changes across hook re-renders", () => {
      const { result, rerender } = renderHook(() => useExecutionMode());

      // Change to safe mode
      act(() => {
        result.current.setExecutionMode("safe");
      });

      // Re-render hook
      rerender();

      // Mode should still be safe
      expect(result.current.executionMode).toBe("safe");
    });

    it("should handle all valid execution modes", () => {
      const modes: ExecutionMode[] = ["safe", "standard", "expert"];

      modes.forEach((mode) => {
        const { result } = renderHook(() => useExecutionMode());

        act(() => {
          result.current.setExecutionMode(mode);
        });

        expect(result.current.executionMode).toBe(mode);
        expect(localStorage.getItem(LOCAL_STORAGE_KEY)).toBe(mode);
      });
    });
  });

  describe("Invalid localStorage values", () => {
    it("should default to 'standard' when localStorage has invalid value", () => {
      // Save invalid value to localStorage
      localStorage.setItem(LOCAL_STORAGE_KEY, "invalid_mode");

      const { result } = renderHook(() => useExecutionMode());

      expect(result.current.executionMode).toBe("standard");
    });

    it("should default to 'standard' when localStorage has empty string", () => {
      localStorage.setItem(LOCAL_STORAGE_KEY, "");

      const { result } = renderHook(() => useExecutionMode());

      expect(result.current.executionMode).toBe("standard");
    });
  });
});
