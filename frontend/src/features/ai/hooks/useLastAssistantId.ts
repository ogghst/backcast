/**
 * useLastAssistantId Hook
 *
 * Custom hook for managing the last selected AI assistant with localStorage persistence.
 * Provides assistant ID state and setter with automatic persistence.
 */

import { useState, useEffect } from "react";

const LOCAL_STORAGE_KEY = "ai_last_selected_assistant";

/**
 * Hook to manage last selected assistant ID with localStorage persistence
 *
 * @returns Object with lastAssistantId state and setLastAssistantId function
 */
export const useLastAssistantId = () => {
  // Initialize state from localStorage (undefined if not found)
  const [lastAssistantId, setLastAssistantIdState] = useState<string | undefined>(() => {
    if (typeof window === "undefined") {
      return undefined;
    }

    try {
      const stored = localStorage.getItem(LOCAL_STORAGE_KEY);
      if (stored) {
        return stored;
      }
    } catch (error) {
      console.error("Error reading last assistant ID from localStorage:", error);
    }

    return undefined;
  });

  // Update localStorage when assistant ID changes
  useEffect(() => {
    if (typeof window === "undefined") {
      return;
    }

    try {
      if (lastAssistantId) {
        localStorage.setItem(LOCAL_STORAGE_KEY, lastAssistantId);
      } else {
        localStorage.removeItem(LOCAL_STORAGE_KEY);
      }
    } catch (error) {
      console.error("Error saving last assistant ID to localStorage:", error);
    }
  }, [lastAssistantId]);

  // Wrapper function to set assistant ID and trigger localStorage update
  const setLastAssistantId = (id: string | undefined) => {
    setLastAssistantIdState(id);
  };

  return {
    lastAssistantId,
    setLastAssistantId,
  };
};
