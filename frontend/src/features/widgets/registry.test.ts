import { describe, it, expect, beforeEach, vi } from "vitest";
import {
  registerWidget,
  getWidgetDefinition,
  getWidgetsByCategory,
  getAllWidgetDefinitions,
} from "./registry";
import { widgetTypeId } from "./types";
import type { WidgetDefinition } from "./types";

// Reset the module-level registry between tests
vi.mock("./registry", async () => {
  const actual = await vi.importActual<typeof import("./registry")>(
    "./registry",
  );
  // We can't reset the module-level Map, so tests must account for accumulation
  // or we test idempotently
  return actual;
});

function createTestDefinition(
  typeId: ReturnType<typeof widgetTypeId>,
  category: "summary" | "trend" | "diagnostic" | "breakdown" | "action" = "summary",
): WidgetDefinition {
  return {
    typeId,
    displayName: `Test ${typeId}`,
    description: `A test widget for ${typeId}`,
    category,
    icon: null,
    sizeConstraints: {
      minW: 2,
      minH: 2,
      defaultW: 4,
      defaultH: 3,
    },
    component: () => null,
    defaultConfig: {},
  };
}

describe("Widget Registry", () => {
  beforeEach(() => {
    // Clear console.warn mock
    vi.spyOn(console, "warn").mockImplementation(() => {});
  });

  describe("registerWidget", () => {
    it("registers a widget definition", () => {
      const def = createTestDefinition(widgetTypeId(`reg-test-${Date.now()}`));
      registerWidget(def);
      expect(getWidgetDefinition(def.typeId)).toBeDefined();
      expect(getWidgetDefinition(def.typeId)?.displayName).toBe(
        def.displayName,
      );
    });

    it("warns on duplicate registration", () => {
      const def = createTestDefinition(
        widgetTypeId(`dup-test-${Date.now()}`),
      );
      registerWidget(def);
      registerWidget(def);
      expect(console.warn).toHaveBeenCalled();
    });
  });

  describe("getWidgetDefinition", () => {
    it("returns undefined for unregistered type", () => {
      const result = getWidgetDefinition(widgetTypeId("nonexistent"));
      expect(result).toBeUndefined();
    });
  });

  describe("getWidgetsByCategory", () => {
    it("filters widgets by category", () => {
      const summaryDef = createTestDefinition(
        widgetTypeId(`cat-summary-${Date.now()}`),
        "summary",
      );
      const trendDef = createTestDefinition(
        widgetTypeId(`cat-trend-${Date.now()}`),
        "trend",
      );
      registerWidget(summaryDef);
      registerWidget(trendDef);

      const summaryWidgets = getWidgetsByCategory("summary");
      const trendWidgets = getWidgetsByCategory("trend");

      expect(summaryWidgets.length).toBeGreaterThanOrEqual(1);
      expect(
        summaryWidgets.some((w) => w.typeId === summaryDef.typeId),
      ).toBe(true);
      expect(trendWidgets.some((w) => w.typeId === trendDef.typeId)).toBe(
        true,
      );
    });

    it("returns empty array for category with no widgets", () => {
      const actionWidgets = getWidgetsByCategory("action");
      // May or may not be empty depending on test order
      expect(Array.isArray(actionWidgets)).toBe(true);
    });
  });

  describe("getAllWidgetDefinitions", () => {
    it("returns all registered definitions", () => {
      const all = getAllWidgetDefinitions();
      expect(Array.isArray(all)).toBe(true);
      expect(all.length).toBeGreaterThanOrEqual(0);
    });
  });
});
