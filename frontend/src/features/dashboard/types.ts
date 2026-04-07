/**
 * Dashboard Types
 *
 * Matches the backend API response from /api/v1/dashboard/recent-activity.
 */

export type ActivityType = "created" | "updated" | "deleted" | "merged";

export type EntityType = "project" | "wbe" | "cost_element" | "change_order";

// ============================================================================
// BACKEND API RESPONSE TYPES
// ============================================================================

/** Matches DashboardActivity schema from backend */
export interface DashboardActivityAPI {
  entity_id: string;
  entity_name: string;
  entity_type: string;
  action: string;
  timestamp: string;
  actor_id?: string | null;
  actor_name?: string | null;
  /** Parent project ID (for child entities) */
  project_id?: string | null;
  /** Parent project name (for child entities) */
  project_name?: string | null;
  branch: string;
}

/** Matches ProjectMetrics schema from backend */
export interface ProjectMetricsAPI {
  total_budget: number;
  total_wbes: number;
  total_cost_elements: number;
  active_change_orders: number;
  /** on_track, at_risk, behind */
  ev_status?: string | null;
}

/** Matches ProjectSpotlight schema from backend */
export interface ProjectSpotlightAPI {
  project_id: string;
  project_name: string;
  project_code: string;
  last_activity: string;
  metrics: ProjectMetricsAPI;
  branch: string;
}

/** Matches DashboardData schema from backend */
export interface DashboardDataAPI {
  last_edited_project: ProjectSpotlightAPI | null;
  recent_activity: Record<string, DashboardActivityAPI[]>;
}

// ============================================================================
// FRONTEND UI TYPES
// ============================================================================

export interface ActivityItem {
  id: string;
  name: string;
  activity_type: ActivityType;
  timestamp: string;
  entity_type: EntityType;
  /** Parent project ID (for WBEs and Change Orders) */
  project_id?: string | null;
}

export interface RecentActivity {
  projects: ActivityItem[];
  wbes: ActivityItem[];
  cost_elements: ActivityItem[];
  change_orders: ActivityItem[];
}

export interface ProjectSpotlight {
  id: string;
  name: string;
  /** Formatted currency string */
  budget: string;
  evm_status: string;
  active_changes: number;
  last_activity: string;
  code: string;
}

export interface DashboardData {
  spotlight: ProjectSpotlight | null;
  recent_activity: RecentActivity;
}

// ============================================================================
// TRANSFORMERS
// ============================================================================

export function transformActivityItem(apiItem: DashboardActivityAPI): ActivityItem {
  return {
    id: apiItem.entity_id,
    name: apiItem.entity_name,
    activity_type: apiItem.action as ActivityType,
    timestamp: apiItem.timestamp,
    entity_type: apiItem.entity_type as EntityType,
    project_id: apiItem.project_id,
  };
}

const currencyFormatter = new Intl.NumberFormat("en-US", {
  style: "currency",
  currency: "USD",
  minimumFractionDigits: 0,
  maximumFractionDigits: 0,
});

export function transformProjectSpotlight(apiSpotlight: ProjectSpotlightAPI): ProjectSpotlight {
  return {
    id: apiSpotlight.project_id,
    name: apiSpotlight.project_name,
    code: apiSpotlight.project_code,
    budget: currencyFormatter.format(apiSpotlight.metrics.total_budget),
    evm_status: apiSpotlight.metrics.ev_status || "N/A",
    active_changes: apiSpotlight.metrics.active_change_orders,
    last_activity: apiSpotlight.last_activity,
  };
}

export function transformDashboardData(apiData: DashboardDataAPI): DashboardData {
  const recentActivity: RecentActivity = {
    projects: (apiData.recent_activity.projects || []).map(transformActivityItem),
    wbes: (apiData.recent_activity.wbes || []).map(transformActivityItem),
    cost_elements: (apiData.recent_activity.cost_elements || []).map(transformActivityItem),
    change_orders: (apiData.recent_activity.change_orders || []).map(transformActivityItem),
  };

  return {
    spotlight: apiData.last_edited_project ? transformProjectSpotlight(apiData.last_edited_project) : null,
    recent_activity: recentActivity,
  };
}

// ============================================================================
// COMPONENT PROPS
// ============================================================================

export interface BaseActivityItemProps {
  activity: ActivityItem;
  onClick?: () => void;
}

export interface ActivitySectionProps {
  title: string;
  icon: React.ReactNode;
  entityType: EntityType;
  activities: ActivityItem[];
  maxItems?: number;
  viewAllUrl?: string;
}

export interface ProjectSpotlightProps {
  project: ProjectSpotlight;
}
