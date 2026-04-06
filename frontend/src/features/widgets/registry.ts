import type {
  WidgetTypeId,
  WidgetCategory,
  WidgetDefinition,
} from "./types";

/** Internal registry storage. Type-erased to hold heterogeneous definitions. */
const registry = new Map<WidgetTypeId, WidgetDefinition>();

/**
 * Register a widget definition in the global registry.
 *
 * If a widget with the same `typeId` already exists, a warning is logged
 * and the definition is overwritten.
 *
 * @param definition - The widget definition to register
 *
 * @example
 * ```ts
 * registerWidget({
 *   typeId: widgetTypeId("evm-summary"),
 *   displayName: "EVM Summary",
 *   description: "Core EVM performance metrics",
 *   category: "summary",
 *   icon: <DashboardOutlined />,
 *   sizeConstraints: { minW: 3, minH: 2, defaultW: 6, defaultH: 4 },
 *   component: EVMSummaryWidget,
 *   defaultConfig: {},
 * });
 * ```
 */
export function registerWidget<TConfig>(
  definition: WidgetDefinition<TConfig>,
): void {
  if (registry.has(definition.typeId)) {
    console.warn(
      `Widget "${definition.typeId}" is already registered. Overwriting.`,
    );
  }
  registry.set(
    definition.typeId,
    definition as WidgetDefinition<Record<string, unknown>>,
  );
}

/**
 * Look up a widget definition by its type identifier.
 *
 * @param typeId - The widget type to find
 * @returns The definition, or `undefined` if not registered
 */
export function getWidgetDefinition(
  typeId: WidgetTypeId,
): WidgetDefinition | undefined {
  return registry.get(typeId);
}

/**
 * Get all registered widget definitions in a given category.
 *
 * @param category - The category to filter by
 * @returns Array of matching definitions (empty if none found)
 */
export function getWidgetsByCategory(
  category: WidgetCategory,
): WidgetDefinition[] {
  return Array.from(registry.values()).filter(
    (def) => def.category === category,
  );
}

/**
 * Get all registered widget definitions.
 *
 * @returns Array of all definitions
 */
export function getAllWidgetDefinitions(): WidgetDefinition[] {
  return Array.from(registry.values());
}
