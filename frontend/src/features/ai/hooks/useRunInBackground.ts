/**
 * useRunInBackground Hook
 *
 * Custom hook for managing the "Run in background" composer toggle with
 * localStorage persistence. The value is sticky per-send: it is read at
 * send time so users can fire off background agent runs without re-checking
 * the toggle each time.
 */

import { useState, useEffect } from "react";

const LOCAL_STORAGE_KEY = "ai_run_in_background";
const DEFAULT_VALUE = false;

/**
 * Hook to manage the background-execution toggle with localStorage persistence.
 *
 * @returns A `[value, setValue]` tuple matching the shape of other AI hooks.
 *
 * @example
 * ```tsx
 * const [runInBackground, setRunInBackground] = useRunInBackground();
 *
 * return (
 *   <Switch checked={runInBackground} onChange={setRunInBackground} />
 * );
 * ```
 */
export const useRunInBackground = (): [boolean, (value: boolean) => void] => {
  // Initialize state from localStorage or default (SSR-safe)
  const [value, setValueState] = useState<boolean>(() => {
    if (typeof window === "undefined") {
      return DEFAULT_VALUE;
    }

    try {
      const stored = localStorage.getItem(LOCAL_STORAGE_KEY);
      if (stored === "true") {
        return true;
      }
      if (stored === "false") {
        return false;
      }
    } catch (error) {
      console.error("Error reading run-in-background from localStorage:", error);
    }

    return DEFAULT_VALUE;
  });

  // Persist to localStorage whenever the value changes
  useEffect(() => {
    if (typeof window === "undefined") {
      return;
    }

    try {
      localStorage.setItem(LOCAL_STORAGE_KEY, String(value));
    } catch (error) {
      console.error("Error saving run-in-background to localStorage:", error);
    }
  }, [value]);

  const setValue = (next: boolean) => {
    setValueState(next);
  };

  return [value, setValue];
};
