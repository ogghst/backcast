/**
 * useExecutionMode Hook
 *
 * Custom hook for managing AI tool execution mode with localStorage persistence.
 * Provides execution mode state and setter with automatic persistence.
 *
 * T-010: Mode persists across sessions
 */

import { useState, useEffect } from "react";
import type { ExecutionMode } from "../chat/types";

const LOCAL_STORAGE_KEY = "ai_execution_mode";
const DEFAULT_MODE: ExecutionMode = "standard";

/**
 * Validates if a value is a valid ExecutionMode
 */
function isValidExecutionMode(value: string): value is ExecutionMode {
  return ["safe", "standard", "expert"].includes(value);
}

/**
 * Hook to manage execution mode with localStorage persistence
 *
 * @returns Object with executionMode state and setExecutionMode function
 *
 * @example
 * ```tsx
 * const { executionMode, setExecutionMode } = useExecutionMode();
 *
 * return (
 *   <Select value={executionMode} onChange={setExecutionMode}>
 *     <Select.Option value="safe">Safe</Select.Option>
 *     <Select.Option value="standard">Standard</Select.Option>
 *     <Select.Option value="expert">Expert</Select.Option>
 *   </Select>
 * );
 * ```
 */
export const useExecutionMode = () => {
  // Initialize state from localStorage or default
  const [executionMode, setExecutionModeState] = useState<ExecutionMode>(() => {
    if (typeof window === "undefined") {
      return DEFAULT_MODE;
    }

    try {
      const stored = localStorage.getItem(LOCAL_STORAGE_KEY);
      if (stored && isValidExecutionMode(stored)) {
        return stored;
      }
    } catch (error) {
      console.error("Error reading execution mode from localStorage:", error);
    }

    return DEFAULT_MODE;
  });

  // Update localStorage when mode changes
  useEffect(() => {
    if (typeof window === "undefined") {
      return;
    }

    try {
      localStorage.setItem(LOCAL_STORAGE_KEY, executionMode);
    } catch (error) {
      console.error("Error saving execution mode to localStorage:", error);
    }
  }, [executionMode]);

  // Wrapper function to set mode and trigger localStorage update
  const setExecutionMode = (mode: ExecutionMode) => {
    setExecutionModeState(mode);
  };

  return {
    executionMode,
    setExecutionMode,
  };
};
