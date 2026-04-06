// Types
export type {
  WidgetTypeId,
  WidgetCategory,
  WidgetSizeConstraints,
  WidgetDefinition,
  WidgetInstance,
  Dashboard,
  WidgetComponentProps,
} from "./types";

export { widgetTypeId } from "./types";

// Registry
export {
  registerWidget,
  getWidgetDefinition,
  getWidgetsByCategory,
  getAllWidgetDefinitions,
} from "./registry";

// Components
export { WidgetShell } from "./components/WidgetShell";
export type { WidgetShellProps } from "./components/WidgetShell";

export { DashboardGrid } from "./components/DashboardGrid";

export { WidgetPalette } from "./components/WidgetPalette";

// Context
export { DashboardContextBus } from "./context/DashboardContextBus";
export type { DashboardContextValue } from "./context/DashboardContextBus";

export { useDashboardContext } from "./context/useDashboardContext";

// Definitions
export { registerAllWidgets } from "./definitions/registerAll";

// Pages
export { DashboardPage } from "./pages/DashboardPage";
