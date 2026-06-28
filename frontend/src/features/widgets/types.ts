import type { ReactNode, FC } from "react";
import type { ConfigFormProps } from "./components/config-forms/ConfigFormProps";
import type { Permission } from "@/types/auth";

// ============================================================================
// Branded Type for Widget Type IDs
// ============================================================================

declare const __widgetTypeId: unique symbol;

/**
 * Branded string type for widget type identifiers.
 * Use `widgetTypeId()` helper to create values.
 *
 * @example
 * ```ts
 * const MY_WIDGET = widgetTypeId("my-widget");
 * registerWidget({ typeId: MY_WIDGET, ... });
 * ```
 */
export type WidgetTypeId = string & { readonly [__widgetTypeId]: unique symbol };

/**
 * Create a branded WidgetTypeId from a plain string.
 *
 * @param id - Unique identifier for the widget type (e.g., "evm-summary")
 */
export function widgetTypeId(id: string): WidgetTypeId {
  return id as WidgetTypeId;
}

// ============================================================================
// Widget Category
// ============================================================================

/**
 * Category for grouping widgets in the palette.
 *
 * - **summary**: At-a-glance KPI cards (budget status, project health)
 * - **trend**: Time-series visualizations (EVM trend, CPI/SPI charts)
 * - **diagnostic**: Variance analysis, root-cause views
 * - **breakdown**: Structured drilldowns (WBS tree, cost element grids)
 * - **action**: Action-oriented lists (pending approvals, recent entries)
 * - **settings**: Configuration widgets for project-specific settings
 */
export type WidgetCategory =
  | "summary"
  | "trend"
  | "diagnostic"
  | "breakdown"
  | "action"
  | "settings";

/**
 * Dashboard scope this widget is valid on.
 *
 * - **project**: project-scoped dashboards only
 * - **portfolio**: portfolio (cross-project) dashboards only
 * - **any** (default): valid on both project and portfolio dashboards
 */
export type WidgetScope = "project" | "portfolio" | "any";

// ============================================================================
// Widget Size Constraints
// ============================================================================

/**
 * Size constraints for a widget type in the 12-column grid.
 * All values are in grid units (columns x row-height blocks).
 */
export interface WidgetSizeConstraints {
  /** Minimum width in grid columns */
  minW: number;
  /** Minimum height in grid rows */
  minH: number;
  /** Maximum width in grid columns (optional, defaults to 12) */
  maxW?: number;
  /** Maximum height in grid rows (optional, no limit if omitted) */
  maxH?: number;
  /** Default width when first placed */
  defaultW: number;
  /** Default height when first placed */
  defaultH: number;
}

// ============================================================================
// Widget Component Props
// ============================================================================

/**
 * Props passed to every widget's render component.
 *
 * @typeparam TConfig - Widget-specific configuration shape
 *
 * Future phases will extend this with data hooks, context bus values,
 * and cross-widget communication capabilities.
 */
export interface WidgetComponentProps<
  TConfig = Record<string, unknown>,
> {
  /** Widget-specific configuration */
  config: TConfig;
  /** Unique instance identifier */
  instanceId: string;
  /** Whether the dashboard is in edit mode */
  isEditing: boolean;
  /** Called when the user confirms widget removal */
  onRemove: () => void;
  /** Called when the user clicks the settings gear icon */
  onConfigure?: () => void;
  /** Called when the user clicks the fullscreen expand button */
  onFullscreen?: () => void;
  /** Widget type identifier for export filenames */
  widgetType?: string;
  /** Dashboard name for export filenames */
  dashboardName?: string;
  /** Provide an ECharts-compatible instance for PNG export */
  getChartInstance?: (() => {
    getDataURL: (opts: {
      type: string;
      pixelRatio: number;
      backgroundColor: string;
    }) => string;
  } | null) | undefined;
  /** Provide table data for CSV export */
  getTableData?:
    | (() => { columns: string[]; rows: string[][] })
    | undefined;
  /** Provide raw data for JSON export */
  getRawData?: (() => unknown) | undefined;
  /** Whether the widget data is stale (exceeded refresh interval) */
  isStale?: boolean;
}

// ============================================================================
// Widget Definition
// ============================================================================

/**
 * Registry entry defining a widget type.
 *
 * @typeparam TConfig - Widget-specific configuration shape
 *
 * Each widget type registers exactly one definition.
 * The registry holds definitions indexed by `typeId`.
 */
export interface WidgetDefinition<
  TConfig = Record<string, unknown>,
> {
  /** Unique type identifier */
  typeId: WidgetTypeId;
  /** Human-readable name shown in the palette */
  displayName: string;
  /** Short description shown in the palette */
  description: string;
  /** Category for palette grouping */
  category: WidgetCategory;
  /** Icon rendered in the palette and widget header */
  icon: ReactNode;
  /** Grid size constraints */
  sizeConstraints: WidgetSizeConstraints;
  /** React component that renders the widget content */
  component: FC<WidgetComponentProps<TConfig>>;
  /** Default configuration applied when the widget is first placed */
  defaultConfig: TConfig;
  /** Optional configuration form component for the WidgetConfigDrawer */
  configFormComponent?: FC<ConfigFormProps<TConfig>>;
  /** Whether this widget requires a project context to function */
  requiresProjectContext?: boolean;
  /** Dashboard scope this widget is valid on. "any" (default) = project + portfolio dashboards. Portfolio widgets set "portfolio"; project widgets may set "project". */
  scope?: WidgetScope;
  /** Existing domain read-permission(s) this widget's data needs. When set, the palette hides the widget from users lacking the perm and the grid renders a locked placeholder. Omit for any-authenticated-user baseline. Multi-perm widgets (e.g. one needing project-read AND cost-registration-read) use the array form, gated via hasAllPermissions. */
  requiredPermission?: Permission | Permission[];
}

// ============================================================================
// Widget Instance
// ============================================================================

/**
 * A placed widget on a dashboard.
 *
 * `instanceId` is a UUID v4 generated at add-time via `crypto.randomUUID()`.
 * `layout` uses the 12-column grid coordinate system.
 */
export interface WidgetInstance {
  /** Unique instance identifier (UUID v4) */
  instanceId: string;
  /** Widget type identifier */
  typeId: WidgetTypeId;
  /** Optional title override (falls back to definition's displayName) */
  title?: string;
  /** Widget-specific configuration */
  config: Record<string, unknown>;
  /** Grid position and size */
  layout: {
    x: number;
    y: number;
    w: number;
    h: number;
  };
}

// ============================================================================
// Dashboard
// ============================================================================

/**
 * A named dashboard containing a set of widget instances.
 *
 * Phase 1: stored in Zustand only (in-memory, lost on refresh).
 * Phase 2: persisted via backend API.
 */
export interface Dashboard {
  /** Dashboard identifier (UUID) */
  id: string;
  /** User-visible dashboard name */
  name: string;
  /** Project this dashboard belongs to */
  projectId: string;
  /** Widget instances placed on this dashboard */
  widgets: WidgetInstance[];
  /** Whether this is the default dashboard for the project */
  isDefault: boolean;
}
