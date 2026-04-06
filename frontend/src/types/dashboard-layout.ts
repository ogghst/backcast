/**
 * Dashboard Layout Types
 *
 * TypeScript interfaces matching the backend Pydantic schemas defined in:
 * backend/app/models/schemas/dashboard_layout.py
 *
 * Non-versioned entity -- no EVCS, no time-travel params needed.
 */

/** Widget instance stored in a layout's widgets array. */
export interface WidgetConfig {
  instanceId: string;
  typeId: string;
  title?: string;
  config: Record<string, unknown>;
  layout: {
    x: number;
    y: number;
    w: number;
    h: number;
  };
}

/** Schema for creating a new dashboard layout. */
export interface DashboardLayoutCreate {
  name: string;
  description?: string | null;
  project_id?: string | null;
  is_template?: boolean;
  is_default?: boolean;
  widgets?: WidgetConfig[];
}

/** Schema for updating an existing dashboard layout. All fields optional. */
export interface DashboardLayoutUpdate {
  name?: string | null;
  description?: string | null;
  is_template?: boolean | null;
  is_default?: boolean | null;
  widgets?: WidgetConfig[] | null;
}

/** Schema for reading dashboard layout data (API response). */
export interface DashboardLayoutRead {
  id: string;
  name: string;
  description: string | null;
  user_id: string;
  project_id: string | null;
  is_template: boolean;
  is_default: boolean;
  widgets: WidgetConfig[];
  created_at: string;
  updated_at: string;
}

/** Schema for cloning a template layout. */
export interface CloneTemplateRequest {
  project_id?: string | null;
}
