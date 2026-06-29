/**
 * Centralized Query Key Factory for TanStack Query
 *
 * Provides type-safe query key generation and consistent cache management.
 * Follows the pattern recommended by TanStack Query documentation.
 *
 * @example
 * ```tsx
 * // Use in queries
 * useQuery({
 *   queryKey: queryKeys.projects.list(params),
 *   queryFn: () => fetchProjects(params),
 * })
 *
 * // Use for invalidation
 * queryClient.invalidateQueries({
 *   queryKey: queryKeys.projects.all,
 * })
 *
 * // Use for partial invalidation
 * queryClient.invalidateQueries({
 *   queryKey: queryKeys.projects.detail(projectId),
 * })
 * ```
 */

import { QueryKey } from "@tanstack/react-query";

/**
 * Simple helper to create typed query keys
 * This provides type safety for the query key factory pattern
 */
function createQueryKeys<T extends Record<string, unknown>>(
  _prefix: string,
  keys: T,
) {
  return keys;
}
import type { ProjectListParams } from "@/features/projects/api/useProjects";

/**
 * Hierarchical query key structure for type safety and autocomplete
 */
export const queryKeys = createQueryKeys("backcast-evs", {
  // Time Machine
  timeMachine: {
    context: null as unknown as QueryKey,
    params: (asOf?: string, branch?: string, mode?: string) =>
      ["time-machine", { asOf, branch, mode }] as const,
  },

  // Dashboard
  dashboard: {
    all: ["dashboard"] as const,
    recentActivity: (params?: { asOf?: string; branch?: string }) =>
      ["dashboard", "recent-activity", params] as const,
  },

  // Projects
  projects: {
    all: ["projects"] as const,
    lists: () => ["projects", "list"] as const,
    list: (params: ProjectListParams) => ["projects", "list", params] as const,
    details: () => ["projects", "detail"] as const,
    detail: (id: string) => ["projects", "detail", id] as const,
    branches: (projectId: string, context?: unknown) =>
      ["projects", projectId, "branches", context] as const,
    history: (projectId: string) => ["projects", projectId, "history"] as const,
  },

  // WBS Elements (was: wbes)
  wbsElements: {
    all: ["wbs-elements"] as const,
    lists: () => ["wbs-elements", "list"] as const,
    list: (projectId: string, params?: unknown) =>
      ["wbs-elements", "list", projectId, params] as const,
    details: () => ["wbs-elements", "detail"] as const,
    detail: (id: string) => ["wbs-elements", "detail", id] as const,
    history: (wbsElementId: string) => ["wbs-elements", wbsElementId, "history"] as const,
    tree: (projectId: string) => ["wbs-elements", "tree", projectId] as const,
    breadcrumb: (wbsElementId: string, context?: unknown) =>
      ["wbs-elements", wbsElementId, "breadcrumb", context] as const,
  },

  // Organizational Units (was: departments)
  organizationalUnits: {
    all: ["organizational-units"] as const,
    list: ["organizational-units", "list"] as const,
    tree: ["organizational-units", "tree"] as const,
    detail: (id: string) => ["organizational-units", "detail", id] as const,
  },

  // Work Packages — PMI budget holder (was: cost-elements old role)
  workPackages: {
    all: ["work-packages"] as const,
    lists: () => ["work-packages", "list"] as const,
    list: (controlAccountId?: string, params?: unknown) =>
      ["work-packages", "list", controlAccountId, params] as const,
    details: () => ["work-packages", "detail"] as const,
    detail: (id: string, context?: unknown) =>
      ["work-packages", "detail", id, context] as const,
    history: (id: string) => ["work-packages", "history", id] as const,
    breadcrumb: (workPackageId: string) =>
      ["work-packages", "breadcrumb", workPackageId] as const,
    budgetStatus: (workPackageId: string, context?: unknown) =>
      ["work-packages", "budget-status", workPackageId, context] as const,
    evmMetrics: (workPackageId: string, context?: unknown) =>
      ["work-packages", "evm", workPackageId, context] as const,
  },

  // Cost Elements — EOC line items under WorkPackage
  costElements: {
    all: ["cost-elements"] as const,
    lists: () => ["cost-elements", "list"] as const,
    list: (workPackageId?: string, params?: unknown) =>
      ["cost-elements", "list", workPackageId, params] as const,
    details: () => ["cost-elements", "detail"] as const,
    detail: (id: string, context?: unknown) =>
      ["cost-elements", "detail", id, context] as const,
    breadcrumb: (costElementId: string) =>
      ["cost-elements", "breadcrumb", costElementId] as const,
  },

  // Cost Events (was: work-packages old role)
  costEvents: {
    all: ["cost-events"] as const,
    lists: () => ["cost-events", "list"] as const,
    list: (projectId: string, params?: unknown) =>
      ["cost-events", "list", projectId, params] as const,
    details: () => ["cost-events", "detail"] as const,
    detail: (id: string, context?: unknown) =>
      ["cost-events", "detail", id, context] as const,
    history: (id: string) => ["cost-events", "history", id] as const,
    summary: (projectId: string) =>
      ["cost-events", "summary", projectId] as const,
    allocations: (id: string) =>
      ["cost-events", "allocations", id] as const,
    coqMetrics: (projectId: string) =>
      ["cost-events", "coqMetrics", projectId] as const,
    coqTrend: (projectId: string, granularity?: string) =>
      ["cost-events", "coqTrend", projectId, granularity] as const,
  },

  // Cost Event Types (was: package-types)
  costEventTypes: {
    all: ["cost-event-types"] as const,
    list: ["cost-event-types", "list"] as const,
  },

  // Control Accounts (new)
  controlAccounts: {
    all: ["control-accounts"] as const,
    lists: () => ["control-accounts", "list"] as const,
    list: (params?: unknown) =>
      ["control-accounts", "list", params] as const,
    details: () => ["control-accounts", "detail"] as const,
    detail: (id: string, context?: unknown) =>
      ["control-accounts", "detail", id, context] as const,
    history: (id: string) => ["control-accounts", "history", id] as const,
  },

  // Cost Element Types
  costElementTypes: {
    all: ["cost-element-types"] as const,
    list: ["cost-element-types", "list"] as const,
    detail: (id: string) => ["cost-element-types", "detail", id] as const,
  },

  // Custom Entity Templates
  customEntityTemplates: {
    all: ["custom-entity-templates"] as const,
    list: ["custom-entity-templates", "list"] as const,
    detail: (id: string) => ["custom-entity-templates", "detail", id] as const,
    history: (id: string) =>
      ["custom-entity-templates", "history", id] as const,
  },

  // Cost Registrations
  costRegistrations: {
    all: ["cost-registrations"] as const,
    lists: () => ["cost-registrations", "list"] as const,
    list: (costElementId: string, params?: unknown) =>
      ["cost-registrations", "list", costElementId, params] as const,
    details: () => ["cost-registrations", "detail"] as const,
    detail: (id: string) => ["cost-registrations", "detail", id] as const,
    history: (id: string) => ["cost-registrations", "history", id] as const,
    budgetStatus: (costElementId: string, context?: unknown) =>
      ["budget-status", costElementId, context] as const,
    aggregated: (entityType: string, entityId: string, params?: unknown) =>
      [...queryKeys.costRegistrations.all, "aggregated", entityType, entityId, params] as const,
    cumulative: (entityType: string, entityId: string, params?: unknown) =>
      [...queryKeys.costRegistrations.all, "cumulative", entityType, entityId, params] as const,
    attachments: (costRegistrationId: string) =>
      [...queryKeys.costRegistrations.all, "attachments", costRegistrationId] as const,
  },

  // Progress Entries
  progressEntries: {
    all: ["progress-entries"] as const,
    lists: () => ["progress-entries", "list"] as const,
    list: (costElementId: string, context?: unknown) =>
      ["progress-entries", "list", costElementId, context] as const,
    details: () => ["progress-entries", "detail"] as const,
    detail: (id: string, context?: unknown) =>
      ["progress-entries", "detail", id, context] as const,
    history: (costElementId: string) =>
      ["progress-entries", "history", costElementId] as const,
    latest: (costElementId: string, context?: unknown) =>
      ["progress-entries", "latest", costElementId, context] as const,
  },

  // Change Orders
  changeOrders: {
    all: ["change-orders"] as const,
    lists: () => ["change-orders", "list"] as const,
    listsInProject: (projectId: string) =>
      ["change-orders", "list", projectId] as const,
    list: (projectId: string, params?: unknown) =>
      ["change-orders", "list", projectId, params] as const,
    details: () => ["change-orders", "detail"] as const,
    detail: (id: string, context?: unknown) =>
      ["change-orders", "detail", id, context] as const,
    nextCode: (projectId: string, year?: number) =>
      ["change-orders", "next-code", projectId, year] as const,
    impact: (id: string, branchName?: string, mode?: string, context?: unknown) =>
      ["change-orders", id, "impact", branchName, mode, context] as const,
    mergeConflicts: (
      changeOrderId: string,
      sourceBranch: string,
      targetBranch: string,
    ) =>
      [
        "change-orders",
        "merge-conflicts",
        changeOrderId,
        sourceBranch,
        targetBranch,
      ] as const,
    branches: ["change-orders", "branches"] as const,
    approvalInfo: (id: string, context?: unknown) =>
      ["change-orders", id, "approval-info", context] as const,
    pendingApprovals: (params?: unknown) =>
      ["pending-approvals", params] as const,
    stats: (projectId: string, context?: unknown) =>
      ["change-orders", "stats", projectId, context] as const,
  },

  // Forecasts
  forecasts: {
    all: ["forecasts"] as const,
    list: (costElementId?: string, context?: unknown) =>
      ["forecasts", "list", costElementId, context] as const,
    detail: (id: string, context?: unknown) =>
      ["forecasts", "detail", id, context] as const,
    comparison: (id: string, branch?: string, context?: unknown) =>
      ["forecast_comparison", id, branch, context] as const,
    byWorkPackage: (workPackageId: string, branch?: string, context?: unknown) =>
      ["work-package-forecast", workPackageId, branch, context] as const,
  },

  // Schedule Baselines
  scheduleBaselines: {
    all: ["schedule-baselines"] as const,
    list: (projectId: string, params?: unknown) =>
      ["schedule-baselines", "list", projectId, params] as const,
    detail: (id: string, context?: unknown) =>
      ["schedule-baselines", "detail", id, context] as const,
    byWorkPackage: (workPackageId: string, context?: unknown) =>
      ["schedule-baselines", "work-package", workPackageId, context] as const,
    history: (id: string) => ["schedule-baselines", "history", id] as const,
    pv: (id: string, params: unknown) =>
      ["schedule-baselines", "pv", id, params] as const,
  },

  // Schedule Dependencies
  scheduleDependencies: {
    all: ["schedule-dependencies"] as const,
    list: (projectId: string, branch?: string) =>
      ["schedule-dependencies", "list", projectId, branch] as const,
    detail: (id: string) =>
      ["schedule-dependencies", "detail", id] as const,
  },

  // AI Configuration
  ai: {
    all: ["ai"] as const,
    providers: {
      all: ["ai", "providers"] as const,
      lists: () => ["ai", "providers", "list"] as const,
      list: (includeInactive?: boolean) =>
        ["ai", "providers", "list", includeInactive] as const,
      detail: (id: string) => ["ai", "providers", "detail", id] as const,
    },
    providerConfigs: {
      list: (providerId: string) =>
        ["ai", "providers", providerId, "configs"] as const,
    },
    models: {
      list: (providerId: string, includeInactive?: boolean) =>
        ["ai", "providers", providerId, "models", includeInactive] as const,
      detail: (id: string) => ["ai", "models", "detail", id] as const,
    },
    assistants: {
      all: ["ai", "assistants"] as const,
      lists: () => ["ai", "assistants", "list"] as const,
      list: (includeInactive?: boolean, agentType?: string) =>
        ["ai", "assistants", "list", includeInactive, agentType] as const,
      detail: (id: string) => ["ai", "assistants", "detail", id] as const,
    },
    chat: {
      all: ["ai", "chat"] as const,
      sessions: () => ["ai", "chat", "sessions"] as const,
      sessionsPaginated: (skip: number, limit: number, contextType?: string, contextId?: string) =>
        ["ai", "chat", "sessions", "paginated", skip, limit, contextType, contextId] as const,
      session: (id: string) => ["ai", "chat", "sessions", id] as const,
      messages: (sessionId: string) =>
        ["ai", "chat", "sessions", sessionId, "messages"] as const,
      executions: {
        all: ["ai", "executions"] as const,
        list: (params?: {
          status?: string;
          scheduleId?: string;
          startedFrom?: string;
          startedTo?: string;
        }) =>
          [
            "ai",
            "executions",
            "list",
            {
              status: params?.status ?? "all",
              scheduleId: params?.scheduleId,
              startedFrom: params?.startedFrom,
              startedTo: params?.startedTo,
            },
          ] as const,
        runningCount: () => ["ai", "executions", "running-count"] as const,
      },
    },
    tools: {
      all: ["ai", "tools"] as const,
      lists: () => ["ai", "tools", "list"] as const,
    },
    mcpServers: {
      all: ["ai", "mcp-servers"] as const,
      lists: () => ["ai", "mcp-servers", "list"] as const,
      list: (includeInactive?: boolean) =>
        ["ai", "mcp-servers", "list", includeInactive] as const,
      detail: (id: string) => ["ai", "mcp-servers", "detail", id] as const,
      tools: (serverId: string) =>
        ["ai", "mcp-servers", serverId, "tools"] as const,
    },
    agentSchedules: {
      all: ["ai", "agent-schedules"] as const,
      lists: () => ["ai", "agent-schedules", "list"] as const,
      list: (params?: { isActive?: boolean; assistantConfigId?: string; ownerUserId?: string }) =>
        ["ai", "agent-schedules", "list", params] as const,
      details: () => ["ai", "agent-schedules", "detail"] as const,
      detail: (id: string) => ["ai", "agent-schedules", "detail", id] as const,
    },
  },

  // Users
  users: {
    all: ["users"] as const,
    lists: () => ["users", "list"] as const,
    list: (params?: { page?: number; per_page?: number }) =>
      ["users", "list", params] as const,
    details: () => ["users", "detail"] as const,
    detail: (id: string) => ["users", "detail", id] as const,
    me: ["users", "me"] as const,
  },

  // Test Resource (for testing useVersionedCrud factory)
  testResource: {
    all: ["test-resource"] as const,
    lists: () => ["test-resource", "list"] as const,
    list: (params?: unknown) => ["test-resource", "list", params] as const,
    details: () => ["test-resource", "detail"] as const,
    detail: (id: string, context?: unknown) =>
      ["test-resource", "detail", id, context] as const,
  },

  // EVM (Earned Value Management)
  evm: {
    all: ["evm"] as const,
    metrics: (entityType: string, entityId: string, context?: unknown) =>
      ["evm", "metrics", entityType, entityId, context] as const,
    timeSeries: (entityType: string, entityId: string, context?: unknown) =>
      ["evm", "timeseries", entityType, entityId, context] as const,
    batch: (entityType: string, entityIds: string[], context?: unknown) =>
      ["evm", "batch", entityType, entityIds, context] as const,
  },

  // Portfolio (cross-project EVM roll-up + change-order pipeline)
  portfolio: {
    all: ["portfolio"] as const,
    evm: (
      params?: {
        controlDate?: string | null;
        branch?: string;
        branchMode?: string;
      },
    ) => ["portfolio", "evm", params] as const,
    changeOrders: (
      params?: {
        asOf?: string | null;
        branch?: string;
        agingThresholdDays?: number;
      },
    ) => ["portfolio", "change-orders", params] as const,
  },

  // Gantt Chart
  gantt: {
    all: ["gantt"] as const,
    project: (projectId: string, context?: unknown) =>
      ["gantt", "project", projectId, context] as const,
  },

  // Dashboard Layouts (widget composition)
  dashboardLayouts: {
    all: ["dashboard-layouts"] as const,
    lists: () => ["dashboard-layouts", "list"] as const,
    list: (projectId?: string) =>
      ["dashboard-layouts", "list", projectId] as const,
    // G13-FE: scope in the cache key so project vs portfolio template lists
    // don't alias. The ["dashboard-layouts"] prefix (above) still covers all
    // sub-keys for the mutation invalidations, so no onSettled change is needed.
    templates: (scope?: "project" | "portfolio") =>
      ["dashboard-layouts", "templates", scope] as const,
    details: () => ["dashboard-layouts", "detail"] as const,
    detail: (id: string) => ["dashboard-layouts", "detail", id] as const,
  },

  // Search
  search: {
    global: (params: unknown, asOf?: string, branch?: string, mode?: string) =>
      ["search", "global", params, asOf, branch, mode] as const,
  },

  // Change Order Config
  changeOrderConfig: {
    all: ["change-order-config"] as const,
    global: ["change-order-config", "global"] as const,
    project: (projectId: string) => ["change-order-config", "project", projectId] as const,
  },

  // Admin RBAC
  adminRbac: {
    all: ["admin-rbac"] as const,
    roles: {
      all: ["admin-rbac", "roles"] as const,
      list: ["admin-rbac", "roles", "list"] as const,
      detail: (id: string) => ["admin-rbac", "roles", "detail", id] as const,
    },
    permissions: ["admin-rbac", "permissions"] as const,
    providerStatus: ["admin-rbac", "provider-status"] as const,
  },

  // Role Assignments
  roleAssignments: {
    all: ["role-assignments"] as const,
    lists: () => ["role-assignments", "list"] as const,
    list: (params?: { userId?: string; scopeType?: string; scopeId?: string; roleId?: string }) =>
      ["role-assignments", "list", params] as const,
    details: () => ["role-assignments", "detail"] as const,
    detail: (id: string) => ["role-assignments", "detail", id] as const,
  },

  // Notifications
  notifications: {
    all: ["notifications"] as const,
    lists: () => ["notifications", "list"] as const,
    list: (params?: {
      page?: number;
      pageSize?: number;
      unreadOnly?: boolean;
      category?: string;
      severity?: string;
    }) => ["notifications", "list", params] as const,
    unreadCount: () => ["notifications", "unread-count"] as const,
    preferences: ["notifications", "preferences"] as const,
    telegramStatus: () => ["notifications", "telegram-status"] as const,
  },

  // Documents
  documents: {
    all: ["documents"] as const,
    lists: () => ["documents", "list"] as const,
    list: (projectId: string, params?: { folderId?: string; skip?: number; limit?: number }) =>
      ["documents", "list", projectId, params] as const,
    details: () => ["documents", "detail"] as const,
    detail: (projectId: string, documentId: string) =>
      ["documents", "detail", projectId, documentId] as const,
    search: (projectId: string, query: string) =>
      ["documents", "search", projectId, query] as const,
    versions: (projectId: string, documentId: string) =>
      ["documents", "versions", projectId, documentId] as const,
    folders: (projectId: string) =>
      ["documents", "folders", projectId] as const,
    stats: (projectId: string) =>
      ["documents", "stats", projectId] as const,
    links: (projectId: string, documentId: string) =>
      ["documents", "links", projectId, documentId] as const,
    linkedDocuments: (projectId: string, entityType: string, entityId: string) =>
      ["documents", "linked", projectId, entityType, entityId] as const,
    previewUrl: (projectId: string, documentId: string) =>
      ["documents", "preview-url", projectId, documentId] as const,
  },
});

/**
 * Helper type for extracting query key types
 */
export type QueryKeyType = typeof queryKeys;
