import { create } from "zustand";
import { persist } from "zustand/middleware";
import { immer } from "zustand/middleware/immer";

/**
 * Branch mode for list operations
 * - "merged": Combine current branch with main (current branch takes precedence)
 * - "isolated": Only return entities from current branch
 */
export type BranchMode = "merged" | "isolated";

/**
 * Project-specific time machine settings stored in localStorage
 */
interface ProjectTimeMachineSettings {
  /** Selected time as ISO string, null means "now" (current) */
  selectedTime: string | null;
  /** Selected branch name */
  selectedBranch: string;
  /** Branch mode for list operations */
  viewMode: BranchMode;
}

/**
 * Time Machine state for project time-travel navigation.
 *
 * Manages:
 * - Current project context
 * - Selected point in time (null = "now")
 * - Selected branch
 * - Per-project settings persistence
 * - Expanded/collapsed UI state
 */
interface TimeMachineState {
  /** Currently selected project ID */
  currentProjectId: string | null;

  /** Whether the timeline panel is expanded */
  isExpanded: boolean;

  /** Per-project settings (persisted to localStorage) */
  projectSettings: Record<string, ProjectTimeMachineSettings>;

  // Computed getters (derived from state + currentProjectId)
  /** Get selected time for current project (null = "now") */
  getSelectedTime: () => string | null;
  /** Get selected branch for current project */
  getSelectedBranch: () => string;
  /** Get view mode for current project */
  getViewMode: () => BranchMode;

  // Actions
  /** Set current project context and optionally initialize with project start date */
  setCurrentProject: (
    projectId: string | null,
    projectStartDate?: Date | null
  ) => void;

  /** Toggle timeline panel expanded state */
  toggleExpanded: () => void;

  /** Select a specific point in time */
  selectTime: (time: Date | null) => void;

  /** Select a branch */
  selectBranch: (branch: string) => void;

  /** Select view mode */
  selectViewMode: (viewMode: BranchMode) => void;

  /** Reset to current time (now) */
  resetToNow: () => void;

  /** Clear all settings for a project */
  clearProjectSettings: (projectId: string) => void;
}

/** Default settings for new projects */
const DEFAULT_PROJECT_SETTINGS: ProjectTimeMachineSettings = {
  selectedTime: null,
  selectedBranch: "main",
  viewMode: "merged",
};

/**
 * Time Machine store for project time-travel navigation.
 *
 * Uses immer for immutable updates and persist for localStorage.
 *
 * @example
 * ```tsx
 * const { getSelectedTime, selectTime, selectBranch } = useTimeMachineStore();
 *
 * // Get current selection
 * const asOf = getSelectedTime(); // null for "now", or ISO string
 *
 * // Select a date
 * selectTime(new Date('2026-01-15'));
 *
 * // Switch branch
 * selectBranch('co-001');
 * ```
 */
export const useTimeMachineStore = create<TimeMachineState>()(
  immer(
    persist(
      (set, get) => ({
        currentProjectId: null,
        isExpanded: false,
        projectSettings: {},

        getSelectedTime: (): string | null => {
          const { currentProjectId, projectSettings } = get();
          if (!currentProjectId) return null;
          return (
            projectSettings[currentProjectId]?.selectedTime ??
            DEFAULT_PROJECT_SETTINGS.selectedTime
          );
        },

        getSelectedBranch: (): string => {
          const { currentProjectId, projectSettings } = get();
          if (!currentProjectId) return DEFAULT_PROJECT_SETTINGS.selectedBranch;
          return (
            projectSettings[currentProjectId]?.selectedBranch ??
            DEFAULT_PROJECT_SETTINGS.selectedBranch
          );
        },

        getViewMode: (): BranchMode => {
          const { currentProjectId, projectSettings } = get();
          if (!currentProjectId) return DEFAULT_PROJECT_SETTINGS.viewMode;
          return (
            projectSettings[currentProjectId]?.viewMode ??
            DEFAULT_PROJECT_SETTINGS.viewMode
          );
        },

        setCurrentProject: (projectId, projectStartDate) => {
          const state = useTimeMachineStore.getState();

          // Only update if actually switching projects
          if (state.currentProjectId === projectId) {
            // Still initializing settings if needed (only if they don't exist)
            if (projectId && !state.projectSettings[projectId]) {
              set((state) => {
                state.projectSettings[projectId] = {
                  ...DEFAULT_PROJECT_SETTINGS,
                  selectedTime: projectStartDate
                    ? projectStartDate.toISOString()
                    : null,
                };
              });
            }
            return;
          }

          // Actually switching projects - use set() to update state
          set((state) => {
            state.currentProjectId = projectId;

            // Initialize settings for new projects (preserve existing settings)
            if (projectId && !state.projectSettings[projectId]) {
              state.projectSettings[projectId] = {
                ...DEFAULT_PROJECT_SETTINGS,
                // Initialize with project start date instead of "now"
                selectedTime: projectStartDate
                  ? projectStartDate.toISOString()
                  : null,
              };
            }
          });
        },

        toggleExpanded: () =>
          set((state) => {
            state.isExpanded = !state.isExpanded;
          }),

        selectTime: (time) =>
          set((state) => {
            const { currentProjectId } = state;
            if (!currentProjectId) return;

            // Ensure project settings exist
            if (!state.projectSettings[currentProjectId]) {
              state.projectSettings[currentProjectId] = {
                ...DEFAULT_PROJECT_SETTINGS,
              };
            }

            // Store as ISO string or null
            state.projectSettings[currentProjectId].selectedTime = time
              ? time.toISOString()
              : null;
          }),

        selectBranch: (branch) =>
          set((state) => {
            const { currentProjectId } = state;
            if (!currentProjectId) return;

            // Ensure project settings exist
            if (!state.projectSettings[currentProjectId]) {
              state.projectSettings[currentProjectId] = {
                ...DEFAULT_PROJECT_SETTINGS,
              };
            }

            state.projectSettings[currentProjectId].selectedBranch = branch;
          }),

        selectViewMode: (viewMode) =>
          set((state) => {
            const { currentProjectId } = state;
            if (!currentProjectId) return;

            // Ensure project settings exist
            if (!state.projectSettings[currentProjectId]) {
              state.projectSettings[currentProjectId] = {
                ...DEFAULT_PROJECT_SETTINGS,
              };
            }

            state.projectSettings[currentProjectId].viewMode = viewMode;
          }),

        resetToNow: () =>
          set((state) => {
            const { currentProjectId } = state;
            if (!currentProjectId) return;

            if (state.projectSettings[currentProjectId]) {
              state.projectSettings[currentProjectId].selectedTime = null;
            }
          }),

        clearProjectSettings: (projectId) =>
          set((state) => {
            delete state.projectSettings[projectId];
          }),

        clearAll: () =>
          set((state) => {
            state.currentProjectId = null;
            state.isExpanded = false;
            state.projectSettings = {};
          }),
      }),
      {
        name: "time-machine-storage",
        partialize: (state) => ({
          // Only persist project settings, not UI state
          projectSettings: state.projectSettings,
        }),
        onRehydrateStorage: () => (state) => {
          // Reset transient state on rehydration
          if (state) {
            state.isExpanded = false;
            state.currentProjectId = null;
          }
        },
      }
    )
  )
);

/**
 * Hook to get the as_of parameter value for API calls.
 * Returns undefined when "now" is selected (default behavior).
 */
export function useAsOfParam(): string | undefined {
  const selectedTime = useTimeMachineStore((state) => {
    if (!state.currentProjectId) return null;
    return state.projectSettings[state.currentProjectId]?.selectedTime ?? null;
  });
  return selectedTime ?? undefined;
}

/**
 * Hook to get the branch parameter value for API calls.
 */
export function useBranchParam(): string {
  const selectedBranch = useTimeMachineStore((state) => {
    if (!state.currentProjectId) return DEFAULT_PROJECT_SETTINGS.selectedBranch;
    return (
      state.projectSettings[state.currentProjectId]?.selectedBranch ??
      DEFAULT_PROJECT_SETTINGS.selectedBranch
    );
  });
  return selectedBranch;
}

/**
 * Hook to get the mode parameter value for API calls.
 * Returns "merged" or "isolated" for branch mode filtering.
 */
export function useModeParam(): BranchMode {
  const viewMode = useTimeMachineStore((state) => {
    if (!state.currentProjectId) return DEFAULT_PROJECT_SETTINGS.viewMode;
    return (
      state.projectSettings[state.currentProjectId]?.viewMode ??
      DEFAULT_PROJECT_SETTINGS.viewMode
    );
  });
  return viewMode;
}
