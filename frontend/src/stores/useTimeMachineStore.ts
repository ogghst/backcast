import { create } from "zustand";
import { persist } from "zustand/middleware";
import { immer } from "zustand/middleware/immer";

/**
 * Project-specific time machine settings stored in localStorage
 */
interface ProjectTimeMachineSettings {
  /** Selected time as ISO string, null means "now" (current) */
  selectedTime: string | null;
  /** Selected branch name */
  selectedBranch: string;
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

  /** Reset to current time (now) */
  resetToNow: () => void;

  /** Clear all settings for a project */
  clearProjectSettings: (projectId: string) => void;
}

/** Default settings for new projects */
const DEFAULT_PROJECT_SETTINGS: ProjectTimeMachineSettings = {
  selectedTime: null,
  selectedBranch: "main",
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

        setCurrentProject: (projectId, projectStartDate) =>
          set((state) => {
            state.currentProjectId = projectId;
            // Initialize settings for new projects
            if (projectId && !state.projectSettings[projectId]) {
              state.projectSettings[projectId] = {
                ...DEFAULT_PROJECT_SETTINGS,
                // Initialize with project start date instead of "now"
                selectedTime: projectStartDate
                  ? projectStartDate.toISOString()
                  : null,
              };
            }
          }),

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
