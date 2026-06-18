/**
 * Tests for useRunInBackground hook
 *
 * Verifies localStorage-backed sticky per-send background toggle.
 */

import { renderHook, act } from "@testing-library/react";
import { describe, it, expect, beforeEach, afterEach } from "vitest";
import { useRunInBackground } from "../useRunInBackground";

describe("useRunInBackground", () => {
  const LOCAL_STORAGE_KEY = "ai_run_in_background";

  beforeEach(() => {
    localStorage.clear();
  });

  afterEach(() => {
    localStorage.clear();
  });

  it("defaults to false when no value in localStorage", () => {
    const { result } = renderHook(() => useRunInBackground());

    const [value] = result.current;
    expect(value).toBe(false);
  });

  it("loads true from localStorage", () => {
    localStorage.setItem(LOCAL_STORAGE_KEY, "true");

    const { result } = renderHook(() => useRunInBackground());

    const [value] = result.current;
    expect(value).toBe(true);
  });

  it("loads false from localStorage", () => {
    localStorage.setItem(LOCAL_STORAGE_KEY, "false");

    const { result } = renderHook(() => useRunInBackground());

    const [value] = result.current;
    expect(value).toBe(false);
  });

  it("saves the new value to localStorage when changed", () => {
    const { result } = renderHook(() => useRunInBackground());

    act(() => {
      const [, setValue] = result.current;
      setValue(true);
    });

    expect(localStorage.getItem(LOCAL_STORAGE_KEY)).toBe("true");
    const [value] = result.current;
    expect(value).toBe(true);
  });

  it("persists value changes across hook re-renders", () => {
    const { result, rerender } = renderHook(() => useRunInBackground());

    act(() => {
      const [, setValue] = result.current;
      setValue(true);
    });

    rerender();

    const [value] = result.current;
    expect(value).toBe(true);
  });

  it("defaults to false when localStorage has an invalid value", () => {
    localStorage.setItem(LOCAL_STORAGE_KEY, "maybe");

    const { result } = renderHook(() => useRunInBackground());

    const [value] = result.current;
    expect(value).toBe(false);
  });
});
