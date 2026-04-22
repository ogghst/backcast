import { useState, useEffect, useMemo } from "react";

export type ViewMode = "table" | "card" | "auto";
type ResolvedViewMode = "table" | "card";

const LOCAL_STORAGE_PREFIX = "layout_view_mode";
const DEFAULT_MODE: ViewMode = "auto";

const VALID_MODES: ViewMode[] = ["table", "card", "auto"];

function isValidViewMode(value: string): value is ViewMode {
  return VALID_MODES.includes(value as ViewMode);
}

function getStorageKey(scope?: string) {
  return scope ? `${LOCAL_STORAGE_PREFIX}_${scope}` : LOCAL_STORAGE_PREFIX;
}

export const useViewMode = (scope?: string, isMobile = false) => {
  const storageKey = getStorageKey(scope);

  const [viewMode, setViewModeState] = useState<ViewMode>(() => {
    if (typeof window === "undefined") return DEFAULT_MODE;
    try {
      const stored = localStorage.getItem(storageKey);
      if (stored && isValidViewMode(stored)) return stored;
    } catch { /* ignore */ }
    return DEFAULT_MODE;
  });

  useEffect(() => {
    if (typeof window === "undefined") return;
    try {
      localStorage.setItem(storageKey, viewMode);
    } catch { /* ignore */ }
  }, [viewMode, storageKey]);

  const setViewMode = (mode: ViewMode) => setViewModeState(mode);

  const cycleViewMode = () => {
    setViewModeState((prev) => {
      if (prev === "auto") return "table";
      if (prev === "table") return "card";
      return "auto";
    });
  };

  const resolvedMode: ResolvedViewMode = useMemo(
    () => (viewMode === "auto" ? (isMobile ? "card" : "table") : viewMode),
    [viewMode, isMobile],
  );

  return { viewMode, resolvedMode, setViewMode, cycleViewMode };
};
