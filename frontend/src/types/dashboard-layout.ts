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

/**
 * Schema for reading dashboard layout data (API response).
 *
 * `role` / `scope` are seeder-only attributes on templates, exposed read-only so
 * the FE can resolve a user's role-tagged default template. They are never on
 * Create/Update (see backend schemas/dashboard_layout.py).
 */
export interface DashboardLayoutRead {
  id: string;
  name: string;
  description: string | null;
  user_id: string;
  project_id: string | null;
  is_template: boolean;
  is_default: boolean;
  widgets: WidgetConfig[];
  /** Template-only role tag (e.g. "cost-controller"); null = generic fallback. */
  role?: string | null;
  /** Template-only scope tag ("project" | "portfolio"); null when not a template. */
  scope?: string | null;
  created_at: string;
  updated_at: string;
}

/** Schema for cloning a template layout. */
export interface CloneTemplateRequest {
  project_id?: string | null;
  name?: string | null;
  /**
   * Whether the clone is the user's default for its scope (clearing any prior
   * default first). Used by the global dashboard's first-visit role-default
   * clone. See backend `clone_template(is_default=)`.
   */
  is_default?: boolean;
}
