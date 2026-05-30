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

  // Organizational Unit
  "organizational-unit-read": { topic: "Organizational Unit", description: "View organizational units" },
  "organizational-unit-create": { topic: "Organizational Unit", description: "Create organizational units" },
  "organizational-unit-update": { topic: "Organizational Unit", description: "Edit organizational units" },
  "organizational-unit-delete": { topic: "Organizational Unit", description: "Remove organizational units" },

  // Project
  "project-read": { topic: "Project", description: "View projects" },
  "project-create": { topic: "Project", description: "Create projects" },
  "project-update": { topic: "Project", description: "Edit projects" },
  "project-delete": { topic: "Project", description: "Remove projects" },

  // WBS Element
  "wbs-element-read": { topic: "WBS Element", description: "View work breakdown structure elements" },
  "wbs-element-create": { topic: "WBS Element", description: "Create work breakdown structure elements" },
  "wbs-element-update": { topic: "WBS Element", description: "Edit work breakdown structure elements" },
  "wbs-element-delete": { topic: "WBS Element", description: "Remove work breakdown structure elements" },

  // Control Account
  "control-account-read": { topic: "Control Account", description: "View control accounts" },
  "control-account-create": { topic: "Control Account", description: "Create control accounts" },
  "control-account-update": { topic: "Control Account", description: "Edit control accounts" },
  "control-account-delete": { topic: "Control Account", description: "Remove control accounts" },

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

  // Cost Event
  "cost-event-read": { topic: "Cost Event", description: "View cost events" },
  "cost-event-create": { topic: "Cost Event", description: "Create cost events" },
  "cost-event-update": { topic: "Cost Event", description: "Edit cost events" },
  "cost-event-delete": { topic: "Cost Event", description: "Remove cost events" },

  // Cost Event Type
  "cost-event-type-read": { topic: "Cost Event Type", description: "View cost event types" },
  "cost-event-type-create": { topic: "Cost Event Type", description: "Create cost event types" },
  "cost-event-type-update": { topic: "Cost Event Type", description: "Edit cost event types" },
  "cost-event-type-delete": { topic: "Cost Event Type", description: "Remove cost event types" },

  // Change Order
  "change-order-read": { topic: "Change Order", description: "View change orders" },
  "change-order-create": { topic: "Change Order", description: "Create change orders" },
  "change-order-update": { topic: "Change Order", description: "Edit change orders" },
  "change-order-delete": { topic: "Change Order", description: "Remove change orders" },
  "change-order-submit": { topic: "Change Order", description: "Submit change orders for approval" },
  "change-order-approve": { topic: "Change Order", description: "Approve change orders" },
  "change-order-implement": { topic: "Change Order", description: "Implement approved change orders" },
  "change-order-recover": { topic: "Change Order", description: "Recover cancelled change orders" },
  "change-order-escalate": { topic: "Change Order", description: "Escalate change orders" },
  "change-order-workflow-config-manage": { topic: "Change Order", description: "Manage change order workflow configuration" },
  "change-order-workflow-config-override": { topic: "Change Order", description: "Override change order workflow rules" },

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
  "progress-entry-update": { topic: "Progress Entry", description: "Update progress entries" },
  "progress-entry-delete": { topic: "Progress Entry", description: "Delete progress entries" },

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

  // Project Documents
  "project-documents-read": { topic: "Project Documents", description: "View project documents" },
  "project-documents-write": { topic: "Project Documents", description: "Upload and edit project documents" },
  "project-documents-delete": { topic: "Project Documents", description: "Remove project documents" },

  // MCP Server
  "mcp-server-read": { topic: "MCP Server", description: "View MCP server configs" },
  "mcp-server-create": { topic: "MCP Server", description: "Create MCP server configs" },
  "mcp-server-update": { topic: "MCP Server", description: "Edit MCP server configs" },
  "mcp-server-delete": { topic: "MCP Server", description: "Remove MCP server configs" },
  "mcp-tool-execute": { topic: "MCP Server", description: "Execute MCP tools" },

  // Work Package
  "work-package-read": { topic: "Work Package", description: "View work packages" },
  "work-package-create": { topic: "Work Package", description: "Create work packages" },
  "work-package-update": { topic: "Work Package", description: "Edit work packages" },
  "work-package-delete": { topic: "Work Package", description: "Remove work packages" },
};

/** Ordered topic names for consistent display. */
const TOPIC_ORDER: string[] = [
  "User Management",
  "Organizational Unit",
  "Project",
  "WBS Element",
  "Control Account",
  "Work Package",
  "Cost Element Type",
  "Cost Element",
  "Cost Registration",
  "Cost Event",
  "Cost Event Type",
  "Change Order",
  "Forecast",
  "Schedule Baseline",
  "Progress Entry",
  "EVM",
  "AI Configuration",
  "Dashboard",
  "Budget Settings",
  "Project Documents",
  "MCP Server",
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
    "change-order-workflow-config-manage": "Manage",
    "change-order-workflow-config-override": "Override",
    "mcp-tool-execute": "Execute",
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
