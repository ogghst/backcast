import { useEffect } from "react";
import { useDashboardCompositionStore } from "@/stores/useDashboardCompositionStore";

/**
 * Registers global keyboard listeners for undo/redo in edit mode.
 * Ctrl+Z / Cmd+Z = undo, Ctrl+Shift+Z / Cmd+Shift+Z / Ctrl+Y = redo.
 * Only active when the dashboard is in edit mode.
 */
export function useUndoRedoKeyboard(): void {
  const isEditing = useDashboardCompositionStore((s) => s.isEditing);
  const undo = useDashboardCompositionStore((s) => s.undo);
  const redo = useDashboardCompositionStore((s) => s.redo);

  useEffect(() => {
    if (!isEditing) return;

    const handler = (e: KeyboardEvent) => {
      const mod = e.metaKey || e.ctrlKey;
      if (!mod) return;

      if (e.key === "z" && !e.shiftKey) {
        e.preventDefault();
        undo();
      } else if (
        (e.key === "z" && e.shiftKey) ||
        e.key === "y"
      ) {
        e.preventDefault();
        redo();
      }
    };

    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [isEditing, undo, redo]);
}
