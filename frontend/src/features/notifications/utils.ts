/**
 * Shared notification helpers (formatting + resource navigation).
 *
 * Used by both the NotificationBell popover and the Notifications page.
 */
import type { NotificationSeverity } from "./api/useNotifications";

/** Severity -> Ant Design Tag color. */
export const SEVERITY_TAG_COLOR: Record<NotificationSeverity, string> = {
  info: "default",
  notice: "blue",
  warning: "gold",
  urgent: "red",
};

/** Format an ISO date string as a human-readable relative time. */
export function timeAgo(dateStr: string): string {
  const now = Date.now();
  const then = new Date(dateStr).getTime();
  const diffSeconds = Math.max(0, Math.floor((now - then) / 1000));

  if (diffSeconds < 60) return "just now";
  const diffMinutes = Math.floor(diffSeconds / 60);
  if (diffMinutes < 60) return `${diffMinutes}m ago`;
  const diffHours = Math.floor(diffMinutes / 60);
  if (diffHours < 24) return `${diffHours}h ago`;
  const diffDays = Math.floor(diffHours / 24);
  if (diffDays < 30) return `${diffDays}d ago`;
  return new Date(dateStr).toLocaleDateString();
}

/**
 * Resolve a resource_type/resource_id pair to an app route, or null if none.
 * agent_execution opens the Agents History page (we don't deep-link a run
 * without its session id); project/document/change_order route directly.
 */
export function resolveResourceRoute(
  resourceType: string | null,
  resourceId: string | null,
): string | null {
  if (!resourceType || !resourceId) return null;
  switch (resourceType) {
    case "change_order":
      return `/change-orders/${resourceId}`;
    case "agent_execution":
      return `/agents-history`;
    case "project":
      return `/projects/${resourceId}`;
    case "document":
      // Documents are project-scoped; without the project_id we land on the
      // generic projects list rather than guessing a project.
      return `/projects`;
    default:
      return null;
  }
}
