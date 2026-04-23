/**
 * RBAC Permission Metadata
 *
 * Static metadata map for all RBAC permissions, providing human-readable
 * topic groupings and descriptions for the permission selector UI.
 *
 * Update this file when new permissions are added to rbac.json.
 */

/** Metadata for a single permission. */
export interface PermissionMeta {
  /** Display group / section heading. */
  topic: string;
  /** Short human-readable description of what the permission allows. */
  description: string;
}

/** A topic with its grouped permissions. */
export interface PermissionTopic {
  /** Display name of the topic section. */
  name: string;
  /** All permission keys belonging to this topic, in display order. */
  permissions: string[];
}

/**
 * Complete permission metadata map.
 * Key = permission string as it appears in rbac.json.
 */
export const PERMISSION_METADATA: Record<string, PermissionMeta> = {
  // User Management
  "user-read": { topic: "User Management", description: "View user profiles and list" },
  "user-create": { topic: "User Management", description: "Create new users" },
  "user-update": { topic: "User Management", description: "Edit existing users" },
  "user-delete": { topic: "User Management", description: "Remove users" },

  // Department
  "department-read": { topic: "Department", description: "View departments" },
  "department-create": { topic: "Department", description: "Create departments" },
  "department-update": { topic: "Department", description: "Edit departments" },
  "department-delete": { topic: "Department", description: "Remove departments" },

  // Project
  "project-read": { topic: "Project", description: "View projects" },
  "project-create": { topic: "Project", description: "Create projects" },
  "project-update": { topic: "Project", description: "Edit projects" },
  "project-delete": { topic: "Project", description: "Remove projects" },

  // Work Breakdown
  "wbe-read": { topic: "Work Breakdown", description: "View work breakdown elements" },
  "wbe-create": { topic: "Work Breakdown", description: "Create work breakdown elements" },
  "wbe-update": { topic: "Work Breakdown", description: "Edit work breakdown elements" },
  "wbe-delete": { topic: "Work Breakdown", description: "Remove work breakdown elements" },

  // Cost Element Type
  "cost-element-type-read": { topic: "Cost Element Type", description: "View cost element types" },
  "cost-element-type-create": { topic: "Cost Element Type", description: "Create cost element types" },
  "cost-element-type-update": { topic: "Cost Element Type", description: "Edit cost element types" },
  "cost-element-type-delete": { topic: "Cost Element Type", description: "Remove cost element types" },

  // Cost Element
  "cost-element-read": { topic: "Cost Element", description: "View cost elements" },
  "cost-element-create": { topic: "Cost Element", description: "Create cost elements" },
  "cost-element-update": { topic: "Cost Element", description: "Edit cost elements" },
  "cost-element-delete": { topic: "Cost Element", description: "Remove cost elements" },

  // Cost Registration
  "cost-registration-read": { topic: "Cost Registration", description: "View cost registrations" },
  "cost-registration-create": { topic: "Cost Registration", description: "Create cost registrations" },
  "cost-registration-update": { topic: "Cost Registration", description: "Edit cost registrations" },
  "cost-registration-delete": { topic: "Cost Registration", description: "Remove cost registrations" },

  // Change Order
  "change-order-read": { topic: "Change Order", description: "View change orders" },
  "change-order-create": { topic: "Change Order", description: "Create change orders" },
  "change-order-update": { topic: "Change Order", description: "Edit change orders" },
  "change-order-delete": { topic: "Change Order", description: "Remove change orders" },
  "change-order-submit": { topic: "Change Order", description: "Submit change orders for approval" },
  "change-order-approve": { topic: "Change Order", description: "Approve change orders" },
  "change-order-implement": { topic: "Change Order", description: "Implement approved change orders" },
  "change-order-recover": { topic: "Change Order", description: "Recover cancelled change orders" },

  // Forecast
  "forecast-read": { topic: "Forecast", description: "View forecasts" },
  "forecast-create": { topic: "Forecast", description: "Create forecasts" },
  "forecast-update": { topic: "Forecast", description: "Edit forecasts" },
  "forecast-delete": { topic: "Forecast", description: "Remove forecasts" },

  // Schedule Baseline
  "schedule-baseline-read": { topic: "Schedule Baseline", description: "View schedule baselines" },
  "schedule-baseline-create": { topic: "Schedule Baseline", description: "Create schedule baselines" },
  "schedule-baseline-update": { topic: "Schedule Baseline", description: "Edit schedule baselines" },
  "schedule-baseline-delete": { topic: "Schedule Baseline", description: "Remove schedule baselines" },

  // Progress Entry
  "progress-entry-read": { topic: "Progress Entry", description: "View progress entries" },
  "progress-entry-create": { topic: "Progress Entry", description: "Create progress entries" },
  "progress-entry-update": { topic: "Progress Entry", description: "Edit progress entries" },
  "progress-entry-delete": { topic: "Progress Entry", description: "Remove progress entries" },

  // Quality Event
  "quality-event-read": { topic: "Quality Event", description: "View quality events" },
  "quality-event-create": { topic: "Quality Event", description: "Create quality events" },
  "quality-event-update": { topic: "Quality Event", description: "Edit quality events" },
  "quality-event-delete": { topic: "Quality Event", description: "Remove quality events" },
  "quality-event-write": { topic: "Quality Event", description: "Record quality event data" },

  // EVM
  "evm-read": { topic: "EVM", description: "View earned value metrics" },
  "evm-create": { topic: "EVM", description: "Create EVM snapshots" },
  "evm-update": { topic: "EVM", description: "Edit EVM data" },
  "evm-delete": { topic: "EVM", description: "Remove EVM snapshots" },

  // AI Configuration
  "ai-config-read": { topic: "AI Configuration", description: "View AI assistant configs" },
  "ai-config-create": { topic: "AI Configuration", description: "Create AI assistant configs" },
  "ai-config-update": { topic: "AI Configuration", description: "Edit AI assistant configs" },
  "ai-config-delete": { topic: "AI Configuration", description: "Remove AI assistant configs" },
  "ai-chat": { topic: "AI Configuration", description: "Use AI chat features" },

  // Dashboard
  "dashboard-template-update": { topic: "Dashboard", description: "Manage dashboard templates" },

  // Budget Settings
  "project-budget-settings-read": { topic: "Budget Settings", description: "View project budget settings" },
  "project-budget-settings-write": { topic: "Budget Settings", description: "Edit project budget settings" },
};

/** Ordered topic names for consistent display. */
const TOPIC_ORDER: string[] = [
  "User Management",
  "Department",
  "Project",
  "Work Breakdown",
  "Cost Element Type",
  "Cost Element",
  "Cost Registration",
  "Change Order",
  "Forecast",
  "Schedule Baseline",
  "Progress Entry",
  "Quality Event",
  "EVM",
  "AI Configuration",
  "Dashboard",
  "Budget Settings",
];

/**
 * Extract a short action label from a permission string.
 * e.g. "user-read" -> "Read", "change-order-submit" -> "Submit",
 *      "ai-chat" -> "Chat", "project-budget-settings-write" -> "Write"
 */
export function getActionLabel(permission: string): string {
  const meta = PERMISSION_METADATA[permission];
  if (!meta) {
    return permission;
  }

  // Handle special cases where the action is not a simple suffix
  const specialActions: Record<string, string> = {
    "ai-chat": "Chat",
    "dashboard-template-update": "Update",
    "project-budget-settings-read": "Read",
    "project-budget-settings-write": "Write",
    "quality-event-write": "Write",
  };

  const special = specialActions[permission];
  if (special) return special;

  // Generic: take the last hyphen-delimited segment and capitalize
  const parts = permission.split("-");
  const last = parts[parts.length - 1];
  return last.charAt(0).toUpperCase() + last.slice(1);
}

/**
 * Group a flat list of permission strings into topics, preserving TOPIC_ORDER.
 * Only permissions present in `available` are included.
 */
export function groupPermissionsByTopic(available: string[]): PermissionTopic[] {
  const grouped = new Map<string, string[]>();

  for (const perm of available) {
    const meta = PERMISSION_METADATA[perm];
    if (!meta) {
      // Unknown permissions go into an "Other" bucket
      const bucket = grouped.get("Other") ?? [];
      bucket.push(perm);
      grouped.set("Other", bucket);
      continue;
    }
    const bucket = grouped.get(meta.topic) ?? [];
    bucket.push(perm);
    grouped.set(meta.topic, bucket);
  }

  // Build result in declared topic order, then append "Other" if present
  const result: PermissionTopic[] = [];
  for (const topic of TOPIC_ORDER) {
    const perms = grouped.get(topic);
    if (perms) {
      result.push({ name: topic, permissions: perms });
    }
  }
  const other = grouped.get("Other");
  if (other) {
    result.push({ name: "Other", permissions: other });
  }

  return result;
}
