import { create } from "zustand";
import { immer } from "zustand/middleware/immer";
import type {
  DashboardLayoutRead,
  WidgetConfig,
} from "@/types/dashboard-layout";
import type {
  Dashboard,
  WidgetInstance,
  WidgetTypeId,
} from "@/features/widgets/types";
import { getWidgetDefinition } from "@/features/widgets/registry";

/** Generate a UUID v4 without requiring a secure context (crypto.randomUUID needs HTTPS/localhost). */
function uuid(): string {
  if (typeof crypto !== "undefined" && typeof crypto.randomUUID === "function") {
    return crypto.randomUUID();
  }
  return "xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx".replace(/[xy]/g, (c) => {
    const r = (Math.random() * 16) | 0;
    const v = c === "x" ? r : (r & 0x3) | 0x8;
    return v.toString(16);
  });
}

/** State and actions for the widget dashboard composition */
interface DashboardCompositionState {
  /** Whether the dashboard is in edit mode */
  isEditing: boolean;
  /** The currently active dashboard (null = no dashboard) */
  activeDashboard: Dashboard | null;
  /** Whether the dashboard has unsaved layout changes */
  isDirty: boolean;
  /** Currently selected widget instance (for settings panel) */
  selectedWidgetId: string | null;
  /** Backend layout UUID (null = not yet persisted) */
  backendId: string | null;
  /** Project ID set from the page route */
  projectId: string;
  /** Whether the widget palette modal is open */
  paletteOpen: boolean;
  /**
   * JSON-serialized snapshot of activeDashboard taken when entering edit mode.
   * Used by discardChanges() to restore the pre-edit state.
   */
  _lastSavedSnapshot: string | null;
  /** Undo stack of JSON-serialized dashboard snapshots (max 20) */
  _undoStack: string[];
  /** Redo stack of JSON-serialized dashboard snapshots (max 20) */
  _redoStack: string[];
  /** Toggle the widget palette modal */
  setPaletteOpen: (open: boolean) => void;

  /** Toggle dashboard edit mode (takes snapshot on enter) */
  setEditing: (editing: boolean) => void;
  /** Set the project ID from the route */
  setProjectId: (projectId: string) => void;
  /** Update the dashboard name */
  updateDashboardName: (name: string) => void;
  /** Add a new widget to the dashboard */
  addWidget: (
    typeId: WidgetTypeId,
    position?: { x: number; y: number },
  ) => void;
  /** Remove a widget by its instance ID */
  removeWidget: (instanceId: string) => void;
  /** Update a single widget's layout position/size */
  updateWidgetLayout: (
    instanceId: string,
    layout: { x: number; y: number; w: number; h: number },
  ) => void;
  /** Update a widget's configuration */
  updateWidgetConfig: (
    instanceId: string,
    config: Record<string, unknown>,
  ) => void;
  /** Batch-update all widget layouts (from react-grid-layout onLayoutChange) */
  updateDashboardLayout: (
    layouts: Array<{
      i: string;
      x: number;
      y: number;
      w: number;
      h: number;
    }>,
  ) => void;
  /** Select a widget instance (or deselect with null) */
  selectWidget: (instanceId: string | null) => void;
  /** Reset the dashboard to initial empty state */
  resetDashboard: () => void;
  /** Load dashboard state from a backend response */
  loadFromBackend: (layout: DashboardLayoutRead) => void;
  /** Mark the dashboard as saved, storing the backend layout ID */
  markSaved: (backendId: string) => void;
  /** Restore dashboard to snapshot taken at edit-mode entry, then exit edit mode */
  discardChanges: () => void;
  /** Exit edit mode after a successful save (clears snapshot, deselects widget) */
  confirmChanges: () => void;
  /** Undo the last composition change */
  undo: () => void;
  /** Redo the last undone composition change */
  redo: () => void;
}

const MAX_UNDO = 20;

/**
 * Push a snapshot onto a stack, capping at MAX_UNDO entries.
 */
function pushToStack(stack: string[], snapshot: string): string[] {
  const next = [...stack, snapshot];
  return next.length > MAX_UNDO ? next.slice(-MAX_UNDO) : next;
}

/**
 * Compute the next available Y position below all existing widgets.
 * Places the new widget at y=0 if no widgets exist.
 */
function computeNextY(widgets: WidgetInstance[]): number {
  if (widgets.length === 0) return 0;
  return Math.max(...widgets.map((w) => w.layout.y + w.layout.h));
}

/**
 * Convert backend WidgetConfig[] to frontend WidgetInstance[].
 *
 * The shapes are structurally identical (instanceId, typeId, config, layout),
 * so a direct cast is safe.
 */
function widgetConfigsToInstances(
  widgets: WidgetConfig[],
): WidgetInstance[] {
  return widgets as unknown as WidgetInstance[];
}

export const useDashboardCompositionStore =
  create<DashboardCompositionState>()(
    immer((set) => ({
      isEditing: false,
      activeDashboard: null,
      isDirty: false,
      selectedWidgetId: null,
      backendId: null,
      projectId: "",
      paletteOpen: false,
      _lastSavedSnapshot: null,
      _undoStack: [],
      _redoStack: [],

      setEditing: (editing) =>
        set((state) => {
          if (editing && state.activeDashboard) {
            // Take a snapshot of the current dashboard before entering edit mode
            state._lastSavedSnapshot = JSON.stringify(state.activeDashboard);
          }
          state.isEditing = editing;
          state.isDirty = false;
        }),

      setProjectId: (projectId) =>
        set((state) => {
          state.projectId = projectId;
        }),

      setPaletteOpen: (open) =>
        set((state) => {
          state.paletteOpen = open;
        }),

      updateDashboardName: (name) =>
        set((state) => {
          if (state.activeDashboard) {
            state.activeDashboard.name = name;
            state.isDirty = true;
          }
        }),

      addWidget: (typeId, position) =>
        set((state) => {
          if (state.activeDashboard) {
            state._undoStack = pushToStack(
              state._undoStack,
              JSON.stringify(state.activeDashboard),
            );
            state._redoStack = [];
          }
          const definition = getWidgetDefinition(typeId);
          if (!definition) return;

          // Create dashboard if none exists
          if (!state.activeDashboard) {
            state.activeDashboard = {
              id: uuid(),
              name: "My Dashboard",
              projectId: state.projectId,
              widgets: [],
              isDefault: false,
            };
          }

          const instance: WidgetInstance = {
            instanceId: uuid(),
            typeId,
            config: {
              ...definition.defaultConfig,
            },
            layout: {
              x: position?.x ?? 0,
              y: position?.y ?? computeNextY(state.activeDashboard.widgets),
              w: definition.sizeConstraints.defaultW,
              h: definition.sizeConstraints.defaultH,
            },
          };

          state.activeDashboard.widgets.push(instance);
          state.isDirty = true;
        }),

      removeWidget: (instanceId) =>
        set((state) => {
          if (!state.activeDashboard) return;
          state._undoStack = pushToStack(
            state._undoStack,
            JSON.stringify(state.activeDashboard),
          );
          state._redoStack = [];
          state.activeDashboard.widgets =
            state.activeDashboard.widgets.filter(
              (w) => w.instanceId !== instanceId,
            );
          if (state.selectedWidgetId === instanceId) {
            state.selectedWidgetId = null;
          }
          state.isDirty = true;
        }),

      updateWidgetLayout: (instanceId, layout) =>
        set((state) => {
          if (!state.activeDashboard) return;
          const widget = state.activeDashboard.widgets.find(
            (w) => w.instanceId === instanceId,
          );
          if (widget) {
            widget.layout = { ...layout };
            state.isDirty = true;
          }
        }),

      updateWidgetConfig: (instanceId, config) =>
        set((state) => {
          if (!state.activeDashboard) return;
          state._undoStack = pushToStack(
            state._undoStack,
            JSON.stringify(state.activeDashboard),
          );
          state._redoStack = [];
          const widget = state.activeDashboard.widgets.find(
            (w) => w.instanceId === instanceId,
          );
          if (widget) {
            widget.config = { ...config };
            state.isDirty = true;
          }
        }),

      updateDashboardLayout: (layouts) =>
        set((state) => {
          if (!state.activeDashboard) return;
          // Only push undo snapshot for layout changes during edit mode
          if (state.isEditing) {
            state._undoStack = pushToStack(
              state._undoStack,
              JSON.stringify(state.activeDashboard),
            );
            state._redoStack = [];
          }
          for (const layoutItem of layouts) {
            const widget = state.activeDashboard.widgets.find(
              (w) => w.instanceId === layoutItem.i,
            );
            if (widget) {
              widget.layout = {
                x: layoutItem.x,
                y: layoutItem.y,
                w: layoutItem.w,
                h: layoutItem.h,
              };
            }
          }
          state.isDirty = true;
        }),

      selectWidget: (instanceId) =>
        set((state) => {
          state.selectedWidgetId = instanceId;
        }),

      resetDashboard: () =>
        set((state) => {
          state.activeDashboard = null;
          state.isDirty = false;
          state.isEditing = false;
          state.selectedWidgetId = null;
          state.backendId = null;
        }),

      loadFromBackend: (layout) =>
        set((state) => {
          state.activeDashboard = {
            id: uuid(),
            name: layout.name,
            projectId: layout.project_id ?? state.projectId,
            widgets: widgetConfigsToInstances(layout.widgets),
            isDefault: layout.is_default,
          };
          state.backendId = layout.id;
          state.isDirty = false;
          state.selectedWidgetId = null;
        }),

      markSaved: (backendId) =>
        set((state) => {
          state.backendId = backendId;
          state.isDirty = false;
        }),

      discardChanges: () =>
        set((state) => {
          if (state._lastSavedSnapshot) {
            state.activeDashboard = JSON.parse(state._lastSavedSnapshot);
          }
          state._lastSavedSnapshot = null;
          state.isDirty = false;
          state.isEditing = false;
          state.selectedWidgetId = null;
          state._undoStack = [];
          state._redoStack = [];
        }),

      confirmChanges: () =>
        set((state) => {
          state._lastSavedSnapshot = null;
          state.isEditing = false;
          state.selectedWidgetId = null;
          state._undoStack = [];
          state._redoStack = [];
        }),

      undo: () =>
        set((state) => {
          if (state._undoStack.length === 0 || !state.activeDashboard) return;
          const current = JSON.stringify(state.activeDashboard);
          const prev = state._undoStack[state._undoStack.length - 1];
          state._undoStack = state._undoStack.slice(0, -1);
          state._redoStack = pushToStack(state._redoStack, current);
          state.activeDashboard = JSON.parse(prev);
          state.isDirty = true;
        }),

      redo: () =>
        set((state) => {
          if (state._redoStack.length === 0 || !state.activeDashboard) return;
          const current = JSON.stringify(state.activeDashboard);
          const next = state._redoStack[state._redoStack.length - 1];
          state._redoStack = state._redoStack.slice(0, -1);
          state._undoStack = pushToStack(state._undoStack, current);
          state.activeDashboard = JSON.parse(next);
          state.isDirty = true;
        }),
    })),
  );
