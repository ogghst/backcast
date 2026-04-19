import { useEffect } from "react";

/**
 * Registers a global Cmd+K / Ctrl+K keyboard shortcut.
 * Calls onOpen when the shortcut is triggered.
 */
export const useSearchShortcut = (onOpen: () => void) => {
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === "k") {
        e.preventDefault();
        onOpen();
      }
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [onOpen]);
};
