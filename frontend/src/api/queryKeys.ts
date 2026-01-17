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

import { QueryKey, createQueryKeys } from "@tanstack/react-query";
import type {
  ProjectListParams,
  PaginatedResponse,
  ProjectRead,
} from "@/types";

/**
 * Hierarchical query key structure for type safety and autocomplete
 */
export const queryKeys = createQueryKeys('backcast-evs', {
  // Time Machine
  timeMachine: {
    context: null as QueryKey,
    params: (asOf?: string, branch?: string, mode?: string) =>
      ['time-machine', { asOf, branch, mode }] as const,
  },

  // Projects
  projects: {
    all: null as QueryKey,
    lists: () => ['projects', 'list'] as const,
    list: (params: ProjectListParams) =>
      ['projects', 'list', params] as const,
    details: () => ['projects', 'detail'] as const,
    detail: (id: string) =>
      ['projects', 'detail', id] as const,
    branches: (projectId: string) =>
      ['projects', projectId, 'branches'] as const,
    history: (projectId: string) =>
      ['projects', projectId, 'history'] as const,
  },

  // Work Breakdown Elements
  wbes: {
    all: null as QueryKey,
    lists: () => ['wbes', 'list'] as const,
    list: (projectId: string, params?: any) =>
      ['wbes', 'list', projectId, params] as const,
    details: () => ['wbes', 'detail'] as const,
    detail: (id: string) =>
      ['wbes', 'detail', id] as const,
    history: (wbeId: string) =>
      ['wbes', wbeId, 'history'] as const,
    tree: (projectId: string) =>
      ['wbes', 'tree', projectId] as const,
  },

  // Cost Elements
  costElements: {
    all: null as QueryKey,
    lists: () => ['cost-elements', 'list'] as const,
    list: (params?: any) =>
      ['cost-elements', 'list', params] as const,
    details: () => ['cost-elements', 'detail'] as const,
    detail: (id: string) =>
      ['cost-elements', 'detail', id] as const,
  },

  // Cost Registrations
  costRegistrations: {
    all: null as QueryKey,
    lists: () => ['cost-registrations', 'list'] as const,
    list: (costElementId: string, params?: any) =>
      ['cost-registrations', 'list', costElementId, params] as const,
    details: () => ['cost-registrations', 'detail'] as const,
    detail: (id: string) =>
      ['cost-registrations', 'detail', id] as const,
  },

  // Change Orders
  changeOrders: {
    all: null as QueryKey,
    lists: () => ['change-orders', 'list'] as const,
    list: (projectId: string) =>
      ['change-orders', 'list', projectId] as const,
    details: () => ['change-orders', 'detail'] as const,
    detail: (id: string) =>
      ['change-orders', 'detail', id] as const,
    impact: (id: string) =>
      ['change-orders', id, 'impact'] as const,
    branches: null as QueryKey,
  },

  // Forecasts
  forecasts: {
    all: null as QueryKey,
    list: (costElementId?: string) =>
      ['forecasts', 'list', costElementId] as const,
    detail: (id: string) =>
      ['forecasts', 'detail', id] as const,
  },

  // Schedule Baselines
  scheduleBaselines: {
    all: null as QueryKey,
    list: (projectId: string) =>
      ['schedule-baselines', 'list', projectId] as const,
    detail: (id: string) =>
      ['schedule-baselines', 'detail', id] as const,
  },

  // Users
  users: {
    all: null as QueryKey,
    list: null as QueryKey,
    detail: (id: string) =>
      ['users', 'detail', id] as const,
    me: null as QueryKey,
  },

  // Departments
  departments: {
    all: null as QueryKey,
    list: null as QueryKey,
    detail: (id: string) =>
      ['departments', 'detail', id] as const,
  },

  // Cost Element Types
  costElementTypes: {
    all: null as QueryKey,
    list: null as QueryKey,
    detail: (id: string) =>
      ['cost-element-types', 'detail', id] as const,
  },
});

/**
 * Helper type for extracting query key types
 */
export type QueryKeyType = typeof queryKeys;
