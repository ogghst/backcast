/**
 * Dashboard Types
 *
 * TypeScript interfaces for dashboard data structures.
 * Matches the backend API response from /api/v1/dashboard/recent-activity.
 */

/**
 * Activity type enum representing the type of change that occurred
 */
export type ActivityType = "created" | "updated" | "deleted" | "merged";

/**
 * Entity type enum for different entity categories
 */
export type EntityType = "project" | "wbe" | "cost_element" | "change_order";

// ============================================================================
// BACKEND API RESPONSE TYPES (from backend/app/models/schemas/dashboard.py)
// ============================================================================

/**
 * Backend API response for a single dashboard activity item
 * Matches DashboardActivity schema from backend
 */
export interface DashboardActivityAPI {
  /** Entity identifier (UUID) */
  entity_id: string;
  /** Entity name/code */
  entity_name: string;
  /** Entity type (project, wbe, cost_element, change_order) */
  entity_type: string;
  /** Action performed (created, updated, deleted, merged) */
  action: string;
  /** When the action occurred (ISO 8601 datetime) */
  timestamp: string;
  /** User who performed the action (UUID) */
  actor_id?: string | null;
  /** Name of user who performed action */
  actor_name?: string | null;
  /** Parent project ID (for child entities) */
  project_id?: string | null;
  /** Parent project name (for child entities) */
  project_name?: string | null;
  /** Branch where action occurred */
  branch: string;
}

/**
 * Backend API response for project metrics
 * Matches ProjectMetrics schema from backend
 */
export interface ProjectMetricsAPI {
  /** Total project budget */
  total_budget: number;
  /** Total number of WBEs */
  total_wbes: number;
  /** Total number of cost elements */
  total_cost_elements: number;
  /** Number of active change orders */
  active_change_orders: number;
  /** Earned Value status (on_track, at_risk, behind) */
  ev_status?: string | null;
}

/**
 * Backend API response for project spotlight
 * Matches ProjectSpotlight schema from backend
 */
export interface ProjectSpotlightAPI {
  /** Project identifier (UUID) */
  project_id: string;
  /** Project name */
  project_name: string;
  /** Project code */
  project_code: string;
  /** Timestamp of most recent activity (ISO 8601 datetime) */
  last_activity: string;
  /** Project metrics */
  metrics: ProjectMetricsAPI;
  /** Branch of last activity */
  branch: string;
}

/**
 * Backend API response for complete dashboard data
 * Matches DashboardData schema from backend
 */
export interface DashboardDataAPI {
  /** Most recently edited project with metrics */
  last_edited_project: ProjectSpotlightAPI | null;
  /** Recent activity grouped by entity type */
  recent_activity: Record<string, DashboardActivityAPI[]>;
}

// ============================================================================
// FRONTEND UI TYPES (transformed for component consumption)
// ============================================================================

/**
 * Single activity item representing a recent change to an entity
 * Frontend UI format after transformation from backend response
 */
export interface ActivityItem {
  /** Unique identifier for the entity */
  id: string;
  /** Name of the entity */
  name: string;
  /** Type of activity that occurred */
  activity_type: ActivityType;
  /** Timestamp when the activity occurred (ISO 8601) */
  timestamp: string;
  /** Type of entity */
  entity_type: EntityType;
  /** Parent project ID (for WBEs and Change Orders) */
  project_id?: string | null;
}

/**
 * Recent activity grouped by entity type
 */
export interface RecentActivity {
  /** List of recent project activities */
  projects: ActivityItem[];
  /** List of recent WBE activities */
  wbes: ActivityItem[];
  /** List of recent cost element activities */
  cost_elements: ActivityItem[];
  /** List of recent change order activities */
  change_orders: ActivityItem[];
}

/**
 * Project spotlight showing the last edited project
 * Frontend UI format after transformation from backend response
 */
export interface ProjectSpotlight {
  /** Unique identifier for the project */
  id: string;
  /** Name of the project */
  name: string;
  /** Total budget formatted as currency string */
  budget: string;
  /** EVM status indicator */
  evm_status: string;
  /** Number of active change orders */
  active_changes: number;
  /** Timestamp of last activity (ISO 8601) */
  last_activity: string;
  /** Project code */
  code: string;
}

/**
 * Complete dashboard data response from the API
 * Frontend UI format after transformation from backend response
 */
export interface DashboardData {
  /** Spotlight section with last edited project */
  spotlight: ProjectSpotlight | null;
  /** Recent activity grouped by entity type */
  recent_activity: RecentActivity;
}

// ============================================================================
// TRANSFORMER UTILITIES
// ============================================================================

/**
 * Transform backend DashboardActivityAPI to frontend ActivityItem
 */
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

/**
 * Transform backend ProjectSpotlightAPI to frontend ProjectSpotlight
 */
export function transformProjectSpotlight(apiSpotlight: ProjectSpotlightAPI): ProjectSpotlight {
  return {
    id: apiSpotlight.project_id,
    name: apiSpotlight.project_name,
    code: apiSpotlight.project_code,
    budget: new Intl.NumberFormat("en-US", {
      style: "currency",
      currency: "USD",
      minimumFractionDigits: 0,
      maximumFractionDigits: 0,
    }).format(apiSpotlight.metrics.total_budget),
    evm_status: apiSpotlight.metrics.ev_status || "N/A",
    active_changes: apiSpotlight.metrics.active_change_orders,
    last_activity: apiSpotlight.last_activity,
  };
}

/**
 * Transform backend DashboardDataAPI to frontend DashboardData
 */
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

/**
 * Props for activity item components
 */
export interface BaseActivityItemProps {
  /** The activity item to display */
  activity: ActivityItem;
  /** Click handler for navigation */
  onClick?: () => void;
}

/**
 * Props for activity section components
 */
export interface ActivitySectionProps {
  /** Title of the section */
  title: string;
  /** Icon for the section */
  icon: React.ReactNode;
  /** Entity type for this section */
  entityType: EntityType;
  /** List of activities to display */
  activities: ActivityItem[];
  /** Maximum number of items to display (default: 5) */
  maxItems?: number;
  /** "View All" link URL */
  viewAllUrl?: string;
}

/**
 * Props for project spotlight component
 */
export interface ProjectSpotlightProps {
  /** Project spotlight data */
  project: ProjectSpotlight;
}
