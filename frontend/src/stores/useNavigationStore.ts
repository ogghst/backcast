import { create } from "zustand";
import { persist } from "zustand/middleware";
import { immer } from "zustand/middleware/immer";

/**
 * Content section shown in the rail-mode inline flyout (desktop), or null.
 * `mobileOpen` and `flyout` are transient UI state; only `expanded` persists.
 */
export type NavFlyout = "account" | "entity" | "admin" | null;

interface NavigationState {
  /** Desktop sidebar expanded (true) or collapsed rail (false). Persisted. */
  expanded: boolean;
  /** Mobile off-canvas drawer open (true) / closed (false). Transient. */
  mobileOpen: boolean;
  /** Active rail flyout content section, or null. Transient. */
  flyout: NavFlyout;

  /** Toggle the desktop sidebar between rail and expanded. */
  toggleExpanded: () => void;
  /** Open/close the mobile off-canvas drawer. */
  setMobileOpen: (open: boolean) => void;
  /** Set the active rail flyout section (null to close). */
  setFlyout: (f: NavFlyout) => void;
}

/**
 * Navigation UI state for the unified sidebar.
 *
 * Uses immer for immutable updates and persist for localStorage. Only
 * `expanded` (the user's rail/expand preference) is persisted — `mobileOpen`
 * and `flyout` are per-session ephemeral UI and must not survive a reload.
 *
 * Storage key: `backcast-nav`.
 */
export const useNavigationStore = create<NavigationState>()(
  immer(
    persist(
      (set) => ({
        expanded: false,
        mobileOpen: false,
        flyout: null,

        toggleExpanded: () =>
          set((state) => {
            state.expanded = !state.expanded;
          }),

        setMobileOpen: (open) =>
          set((state) => {
            state.mobileOpen = open;
          }),

        setFlyout: (f) =>
          set((state) => {
            state.flyout = f;
          }),
      }),
      {
        name: "backcast-nav",
        // Only the user's expand preference survives a reload. The mobile
        // drawer and rail flyout are transient and always reset on mount.
        partialize: (state) => ({ expanded: state.expanded }),
      },
    ),
  ),
);
