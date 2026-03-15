/**
 * Dashboard Feature
 *
 * Main dashboard components and hooks exported from the index.
 */

// Components
export { DashboardHeader } from "./components/DashboardHeader";
export { ProjectSpotlight } from "./components/ProjectSpotlight";
export { ActivityGrid } from "./components/ActivityGrid";
export { ActivitySection } from "./components/ActivitySection";
export { ActivityItem } from "./components/ActivityItem";
export { RelativeTime } from "./components/RelativeTime";
export { DashboardSkeleton } from "./components/DashboardSkeleton";
export { ErrorState } from "./components/ErrorState";
export { EmptyState } from "./components/EmptyState";

// Hooks
export { useDashboardData } from "./hooks/useDashboardData";

// Types
export type {
  ActivityType,
  EntityType,
  ActivityItem,
  RecentActivity,
  ProjectSpotlight as ProjectSpotlightType,
  DashboardData,
  BaseActivityItemProps,
  ActivitySectionProps,
  ProjectSpotlightProps,
} from "./types";
