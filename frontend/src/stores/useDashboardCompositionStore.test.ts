import { describe, it, expect, beforeEach } from "vitest";
import { useDashboardCompositionStore } from "./useDashboardCompositionStore";
import { widgetTypeId } from "@/features/widgets/types";
import { registerWidget } from "@/features/widgets/registry";
import type { DashboardLayoutRead } from "@/types/dashboard-layout";

// Register a test widget so addWidget can resolve its definition
const TEST_WIDGET_TYPE = widgetTypeId("store-test-widget");

beforeEach(() => {
  registerWidget({
    typeId: TEST_WIDGET_TYPE,
    displayName: "Store Test Widget",
    description: "Widget for store tests",
    category: "summary",
    icon: null,
    sizeConstraints: {
      minW: 2,
      minH: 2,
      defaultW: 4,
      defaultH: 3,
    },
    component: () => null,
    defaultConfig: { testKey: "testValue" },
  });

  // Reset store state before each test
  useDashboardCompositionStore.setState({
    isEditing: false,
    activeDashboard: null,
    isDirty: false,
    selectedWidgetId: null,
    backendId: null,
    projectId: "",
  });
});

describe("useDashboardCompositionStore", () => {
  describe("initial state", () => {
    it("starts with no active dashboard", () => {
      const state = useDashboardCompositionStore.getState();
      expect(state.activeDashboard).toBeNull();
      expect(state.isEditing).toBe(false);
      expect(state.isDirty).toBe(false);
      expect(state.selectedWidgetId).toBeNull();
      expect(state.backendId).toBeNull();
      expect(state.projectId).toBe("");
    });
  });

  describe("setEditing", () => {
    it("toggles editing mode", () => {
      useDashboardCompositionStore.getState().setEditing(true);
      expect(useDashboardCompositionStore.getState().isEditing).toBe(true);

      useDashboardCompositionStore.getState().setEditing(false);
      expect(useDashboardCompositionStore.getState().isEditing).toBe(false);
    });
  });

  describe("setProjectId", () => {
    it("sets the project ID", () => {
      useDashboardCompositionStore.getState().setProjectId("proj-123");
      expect(useDashboardCompositionStore.getState().projectId).toBe(
        "proj-123",
      );
    });
  });

  describe("addWidget", () => {
    it("creates a dashboard if none exists", () => {
      useDashboardCompositionStore.getState().addWidget(TEST_WIDGET_TYPE);

      const state = useDashboardCompositionStore.getState();
      expect(state.activeDashboard).not.toBeNull();
      expect(state.activeDashboard!.widgets).toHaveLength(1);
      expect(state.isDirty).toBe(true);
    });

    it("uses projectId from store when creating dashboard", () => {
      useDashboardCompositionStore.getState().setProjectId("proj-456");
      useDashboardCompositionStore.getState().addWidget(TEST_WIDGET_TYPE);

      const state = useDashboardCompositionStore.getState();
      expect(state.activeDashboard!.projectId).toBe("proj-456");
    });

    it("adds widget with default size from definition", () => {
      useDashboardCompositionStore.getState().addWidget(TEST_WIDGET_TYPE);

      const widget =
        useDashboardCompositionStore.getState().activeDashboard!.widgets[0];
      expect(widget.layout.w).toBe(4);
      expect(widget.layout.h).toBe(3);
      expect(widget.config).toEqual({ testKey: "testValue" });
    });

    it("generates a UUID instanceId", () => {
      useDashboardCompositionStore.getState().addWidget(TEST_WIDGET_TYPE);

      const widget =
        useDashboardCompositionStore.getState().activeDashboard!.widgets[0];
      expect(widget.instanceId).toMatch(
        /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i,
      );
    });

    it("places subsequent widgets below existing ones", () => {
      const store = useDashboardCompositionStore.getState();
      store.addWidget(TEST_WIDGET_TYPE);
      store.addWidget(TEST_WIDGET_TYPE);

      const widgets =
        useDashboardCompositionStore.getState().activeDashboard!.widgets;
      expect(widgets[1].layout.y).toBeGreaterThanOrEqual(
        widgets[0].layout.y + widgets[0].layout.h,
      );
    });

    it("uses provided position", () => {
      useDashboardCompositionStore
        .getState()
        .addWidget(TEST_WIDGET_TYPE, { x: 6, y: 0 });

      const widget =
        useDashboardCompositionStore.getState().activeDashboard!.widgets[0];
      expect(widget.layout.x).toBe(6);
      expect(widget.layout.y).toBe(0);
    });
  });

  describe("removeWidget", () => {
    it("removes a widget by instanceId", () => {
      const store = useDashboardCompositionStore.getState();
      store.addWidget(TEST_WIDGET_TYPE);

      const instanceId =
        useDashboardCompositionStore.getState().activeDashboard!.widgets[0]
          .instanceId;

      useDashboardCompositionStore.getState().removeWidget(instanceId);

      expect(
        useDashboardCompositionStore.getState().activeDashboard!.widgets,
      ).toHaveLength(0);
    });

    it("clears selectedWidgetId if the removed widget was selected", () => {
      const store = useDashboardCompositionStore.getState();
      store.addWidget(TEST_WIDGET_TYPE);

      const instanceId =
        useDashboardCompositionStore.getState().activeDashboard!.widgets[0]
          .instanceId;

      useDashboardCompositionStore.getState().selectWidget(instanceId);
      useDashboardCompositionStore.getState().removeWidget(instanceId);

      expect(useDashboardCompositionStore.getState().selectedWidgetId).toBeNull();
    });
  });

  describe("updateWidgetLayout", () => {
    it("updates a widget's position and size", () => {
      useDashboardCompositionStore.getState().addWidget(TEST_WIDGET_TYPE);

      const instanceId =
        useDashboardCompositionStore.getState().activeDashboard!.widgets[0]
          .instanceId;

      useDashboardCompositionStore
        .getState()
        .updateWidgetLayout(instanceId, { x: 2, y: 3, w: 6, h: 4 });

      const widget =
        useDashboardCompositionStore.getState().activeDashboard!.widgets[0];
      expect(widget.layout).toEqual({ x: 2, y: 3, w: 6, h: 4 });
    });
  });

  describe("updateWidgetConfig", () => {
    it("updates a widget's configuration", () => {
      useDashboardCompositionStore.getState().addWidget(TEST_WIDGET_TYPE);

      const instanceId =
        useDashboardCompositionStore.getState().activeDashboard!.widgets[0]
          .instanceId;

      useDashboardCompositionStore
        .getState()
        .updateWidgetConfig(instanceId, { newKey: "newValue" });

      const widget =
        useDashboardCompositionStore.getState().activeDashboard!.widgets[0];
      expect(widget.config).toEqual({ newKey: "newValue" });
    });
  });

  describe("updateDashboardLayout", () => {
    it("batch updates all widget layouts", () => {
      const store = useDashboardCompositionStore.getState();
      store.addWidget(TEST_WIDGET_TYPE);
      store.addWidget(TEST_WIDGET_TYPE);

      const widgets =
        useDashboardCompositionStore.getState().activeDashboard!.widgets;

      useDashboardCompositionStore.getState().updateDashboardLayout([
        { i: widgets[0].instanceId, x: 0, y: 0, w: 6, h: 3 },
        { i: widgets[1].instanceId, x: 6, y: 0, w: 6, h: 3 },
      ]);

      const updated =
        useDashboardCompositionStore.getState().activeDashboard!.widgets;
      expect(updated[0].layout).toEqual({ x: 0, y: 0, w: 6, h: 3 });
      expect(updated[1].layout).toEqual({ x: 6, y: 0, w: 6, h: 3 });
    });
  });

  describe("selectWidget", () => {
    it("sets the selected widget", () => {
      useDashboardCompositionStore.getState().selectWidget("some-id");
      expect(useDashboardCompositionStore.getState().selectedWidgetId).toBe(
        "some-id",
      );

      useDashboardCompositionStore.getState().selectWidget(null);
      expect(useDashboardCompositionStore.getState().selectedWidgetId).toBeNull();
    });
  });

  describe("resetDashboard", () => {
    it("resets all state to defaults", () => {
      const store = useDashboardCompositionStore.getState();
      store.addWidget(TEST_WIDGET_TYPE);
      store.setEditing(true);
      store.selectWidget("test");

      useDashboardCompositionStore.getState().resetDashboard();

      const state = useDashboardCompositionStore.getState();
      expect(state.activeDashboard).toBeNull();
      expect(state.isEditing).toBe(false);
      expect(state.isDirty).toBe(false);
      expect(state.selectedWidgetId).toBeNull();
      expect(state.backendId).toBeNull();
    });
  });

  describe("loadFromBackend", () => {
    it("loads dashboard from a backend DashboardLayoutRead", () => {
      const backendLayout: DashboardLayoutRead = {
        id: "backend-uuid-123",
        name: "Project Dashboard",
        description: null,
        user_id: "user-1",
        project_id: "proj-789",
        is_template: false,
        is_default: true,
        widgets: [
          {
            instanceId: "widget-1",
            typeId: "store-test-widget",
            config: { testKey: "loaded" },
            layout: { x: 0, y: 0, w: 6, h: 3 },
          },
        ],
        created_at: "2026-01-01T00:00:00Z",
        updated_at: "2026-01-01T00:00:00Z",
      };

      useDashboardCompositionStore.getState().loadFromBackend(backendLayout);

      const state = useDashboardCompositionStore.getState();
      expect(state.backendId).toBe("backend-uuid-123");
      expect(state.isDirty).toBe(false);
      expect(state.activeDashboard).not.toBeNull();
      expect(state.activeDashboard!.name).toBe("Project Dashboard");
      expect(state.activeDashboard!.projectId).toBe("proj-789");
      expect(state.activeDashboard!.isDefault).toBe(true);
      expect(state.activeDashboard!.widgets).toHaveLength(1);
      expect(state.activeDashboard!.widgets[0].instanceId).toBe("widget-1");
    });

    it("falls back to stored projectId when backend has null project_id", () => {
      useDashboardCompositionStore.getState().setProjectId("proj-fallback");

      const backendLayout: DashboardLayoutRead = {
        id: "backend-uuid-456",
        name: "No Project",
        description: null,
        user_id: "user-1",
        project_id: null,
        is_template: false,
        is_default: false,
        widgets: [],
        created_at: "2026-01-01T00:00:00Z",
        updated_at: "2026-01-01T00:00:00Z",
      };

      useDashboardCompositionStore.getState().loadFromBackend(backendLayout);

      const state = useDashboardCompositionStore.getState();
      expect(state.activeDashboard!.projectId).toBe("proj-fallback");
    });
  });

  describe("markSaved", () => {
    it("stores backend ID and clears dirty flag", () => {
      useDashboardCompositionStore.getState().addWidget(TEST_WIDGET_TYPE);
      expect(useDashboardCompositionStore.getState().isDirty).toBe(true);

      useDashboardCompositionStore.getState().markSaved("saved-uuid-999");

      const state = useDashboardCompositionStore.getState();
      expect(state.backendId).toBe("saved-uuid-999");
      expect(state.isDirty).toBe(false);
    });
  });
});
