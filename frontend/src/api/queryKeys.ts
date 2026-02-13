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
function createQueryKeys<T extends Record<string, any>>(
  prefix: string,
  keys: T,
) {
  return keys;
}
import type {
  ProjectListParams,
  PaginatedResponse,
  ProjectRead,
} from "@/types";

/**
 * Hierarchical query key structure for type safety and autocomplete
 */
export const queryKeys = createQueryKeys("backcast-evs", {
  // Time Machine
  timeMachine: {
    context: null as QueryKey,
    params: (asOf?: string, branch?: string, mode?: string) =>
      ["time-machine", { asOf, branch, mode }] as const,
  },

  // Projects
  projects: {
    all: ["projects"] as const,
    lists: () => ["projects", "list"] as const,
    list: (params: ProjectListParams) => ["projects", "list", params] as const,
    details: () => ["projects", "detail"] as const,
    detail: (id: string) => ["projects", "detail", id] as const,
    branches: (projectId: string, context?: any) =>
      ["projects", projectId, "branches", context] as const,
    history: (projectId: string) => ["projects", projectId, "history"] as const,
  },

  // Work Breakdown Elements
  wbes: {
    all: ["wbes"] as const,
    lists: () => ["wbes", "list"] as const,
    list: (projectId: string, params?: any) =>
      ["wbes", "list", projectId, params] as const,
    details: () => ["wbes", "detail"] as const,
    detail: (id: string) => ["wbes", "detail", id] as const,
    history: (wbeId: string) => ["wbes", wbeId, "history"] as const,
    tree: (projectId: string) => ["wbes", "tree", projectId] as const,
    breadcrumb: (wbeId: string, context?: any) =>
      ["wbes", wbeId, "breadcrumb", context] as const,
  },

  // Cost Elements
  costElements: {
    all: ["cost-elements"] as const,
    lists: () => ["cost-elements", "list"] as const,
    list: (params?: any) => ["cost-elements", "list", params] as const,
    details: () => ["cost-elements", "detail"] as const,
    detail: (id: string, context?: any) =>
      ["cost-elements", "detail", id, context] as const,
    breadcrumb: (costElementId: string) =>
      ["cost_element_breadcrumb", costElementId] as const,
    evmMetrics: (costElementId: string, context?: any) =>
      ["cost-elements", "evm", costElementId, context] as const,
  },

  // Cost Registrations
  costRegistrations: {
    all: ["cost-registrations"] as const,
    lists: () => ["cost-registrations", "list"] as const,
    list: (costElementId: string, params?: any) =>
      ["cost-registrations", "list", costElementId, params] as const,
    details: () => ["cost-registrations", "detail"] as const,
    detail: (id: string) => ["cost-registrations", "detail", id] as const,
    history: (id: string) => ["cost-registrations", "history", id] as const,
    budgetStatus: (costElementId: string, context?: any) =>
      ["budget-status", costElementId, context] as const,
  },

  // Progress Entries
  progressEntries: {
    all: ["progress-entries"] as const,
    lists: () => ["progress-entries", "list"] as const,
    list: (costElementId: string, context?: any) =>
      ["progress-entries", "list", costElementId, context] as const,
    details: () => ["progress-entries", "detail"] as const,
    detail: (id: string, context?: any) =>
      ["progress-entries", "detail", id, context] as const,
    history: (costElementId: string) =>
      ["progress-entries", "history", costElementId] as const,
    latest: (costElementId: string, context?: any) =>
      ["progress-entries", "latest", costElementId, context] as const,
  },

  // Change Orders
  changeOrders: {
    all: ["change-orders"] as const,
    lists: () => ["change-orders", "list"] as const,
    listsInProject: (projectId: string) =>
      ["change-orders", "list", projectId] as const,
    list: (projectId: string, params?: any) =>
      ["change-orders", "list", projectId, params] as const,
    details: () => ["change-orders", "detail"] as const,
    detail: (id: string, context?: any) =>
      ["change-orders", "detail", id, context] as const,
    impact: (id: string, branchName?: string, mode?: string) =>
      ["change-orders", id, "impact", branchName, mode] as const,
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
    approvalInfo: (id: string) =>
      ["change-orders", id, "approval-info"] as const,
    pendingApprovals: (params?: any) =>
      ["pending-approvals", params] as const,
  },

  // Forecasts
  forecasts: {
    all: ["forecasts"] as const,
    list: (costElementId?: string, context?: any) =>
      ["forecasts", "list", costElementId, context] as const,
    detail: (id: string, context?: any) =>
      ["forecasts", "detail", id, context] as const,
    comparison: (id: string, branch?: string, context?: any) =>
      ["forecast_comparison", id, branch, context] as const,
    byCostElement: (costElementId: string, branch?: string, context?: any) =>
      ["cost-element-forecast", costElementId, branch, context] as const,
  },

  // Schedule Baselines
  scheduleBaselines: {
    all: ["schedule-baselines"] as const,
    list: (projectId: string, params?: any) =>
      ["schedule-baselines", "list", projectId, params] as const,
    detail: (id: string, context?: any) =>
      ["schedule-baselines", "detail", id, context] as const,
    byCostElement: (costElementId: string, context?: any) =>
      ["schedule-baselines", "cost-element", costElementId, context] as const,
    history: (id: string) => ["schedule-baselines", "history", id] as const,
    pv: (id: string, params: any) =>
      ["schedule-baselines", "pv", id, params] as const,
  },

  // Users
  users: {
    all: ["users"] as const,
    list: ["users", "list"] as const,
    detail: (id: string) => ["users", "detail", id] as const,
    me: ["users", "me"] as const,
  },

  // Departments
  departments: {
    all: ["departments"] as const,
    list: ["departments", "list"] as const,
    detail: (id: string) => ["departments", "detail", id] as const,
  },

  // Cost Element Types
  costElementTypes: {
    all: ["cost-element-types"] as const,
    list: ["cost-element-types", "list"] as const,
    detail: (id: string) => ["cost-element-types", "detail", id] as const,
  },

  // Test Resource (for testing useVersionedCrud factory)
  testResource: {
    all: ["test-resource"] as const,
    lists: () => ["test-resource", "list"] as const,
    list: (params?: any) => ["test-resource", "list", params] as const,
    details: () => ["test-resource", "detail"] as const,
    detail: (id: string, context?: any) =>
      ["test-resource", "detail", id, context] as const,
  },

  // EVM (Earned Value Management)
  evm: {
    all: ["evm"] as const,
    metrics: (entityType: string, entityId: string, context?: any) =>
      ["evm", "metrics", entityType, entityId, context] as const,
    timeSeries: (entityType: string, entityId: string, context?: any) =>
      ["evm", "timeseries", entityType, entityId, context] as const,
    batch: (entityType: string, entityIds: string[], context?: any) =>
      ["evm", "batch", entityType, entityIds, context] as const,
  },
});

/**
 * Helper type for extracting query key types
 */
export type QueryKeyType = typeof queryKeys;
