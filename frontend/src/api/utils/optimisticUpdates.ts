/**
 * Optimistic Update Utilities for TanStack Query
 *
 * Provides reusable patterns for optimistic updates with proper rollback on error.
 *
 * @example
 * ```tsx
 * const mutation = useMutation({
 *   mutationFn: updateProject,
 *   onMutate: async (newData) => {
 *     await handleOptimisticUpdate({
 *       queryClient,
 *       queryKey: queryKeys.projects.detail(newData.id),
 *       updateFn: (old) => ({ ...old, ...newData }),
 *     });
 *   },
 *   onError: (err, newData, context) => {
 *       rollbackQuery({ queryClient, context });
 *     },
 *   });
 * });
 * ```
 */

import { QueryClient, QueryKey } from "@tanstack/react-query";

interface OptimisticUpdateOptions<TData, TVariables> {
  queryClient: QueryClient;
  queryKey: QueryKey;
  updateFn: (oldData: TData | undefined, variables: TVariables) => TData;
}

interface RollbackOptions {
  queryClient: QueryClient;
  context?: { previousData?: unknown };
}

/**
 * Handles optimistic updates with proper cancellation of ongoing queries
 * and context preservation for rollback
 */
export async function handleOptimisticUpdate<TData, TVariables>({
  queryClient,
  queryKey,
  updateFn,
}: OptimisticUpdateOptions<TData, TVariables>) {
  // Cancel any outgoing refetches
  await queryClient.cancelQueries({ queryKey });

  // Snapshot the previous value
  const previousData = queryClient.getQueryData<TData>(queryKey);

  // Optimistically update to the new value
  queryClient.setQueryData<TData>(queryKey, (old) =>
    updateFn(old, undefined as unknown as TVariables)
  );

  // Return context with the previous value for rollback
  return { previousData };
}

/**
 * Rolls back a query to its previous state on error
 */
export function rollbackQuery<TData>({
  queryClient,
  context,
  queryKey,
}: RollbackOptions & { queryKey: QueryKey }) {
  if (context?.previousData) {
    queryClient.setQueryData<TData>(queryKey, context.previousData as TData);
  }
}

/**
 * Generic optimistic update handler for list items
 */
export async function handleListOptimisticUpdate<TData, TVariables>({
  queryClient,
  queryKey,
  updateFn,
  itemId,
}: OptimisticUpdateOptions<TData[], TVariables> & {
  itemId: string;
}) {
  await queryClient.cancelQueries({ queryKey });

  const previousData = queryClient.getQueryData<TData[]>(queryKey);

  queryClient.setQueryData<TData[]>(queryKey, (old = []) =>
    old.map((item) => {
      const id = (item as { id?: string; project_id?: string; wbe_id?: string }).id ||
                  (item as { id?: string; project_id?: string; wbe_id?: string }).project_id ||
                  (item as { id?: string; project_id?: string; wbe_id?: string }).wbe_id;
      return id === itemId ? updateFn(item, undefined as unknown as TVariables) : item;
    })
  );

  return { previousData };
}

/**
 * Generic optimistic delete handler for lists
 */
export async function handleOptimisticDelete<TData>({
  queryClient,
  queryKey,
  itemId,
}: {
  queryClient: QueryClient;
  queryKey: QueryKey;
  itemId: string;
}) {
  await queryClient.cancelQueries({ queryKey });

  const previousData = queryClient.getQueryData<TData[]>(queryKey);

  queryClient.setQueryData<TData[]>(queryKey, (old = []) =>
    old.filter((item) => {
      const id = (item as { id?: string; project_id?: string; wbe_id?: string }).id ||
                  (item as { id?: string; project_id?: string; wbe_id?: string }).project_id ||
                  (item as { id?: string; project_id?: string; wbe_id?: string }).wbe_id;
      return id !== itemId;
    })
  );

  return { previousData };
}

/**
 * Generic optimistic create handler for lists
 */
export async function handleOptimisticCreate<TData>({
  queryClient,
  queryKey,
  newItem,
}: {
  queryClient: QueryClient;
  queryKey: QueryKey;
  newItem: TData;
}) {
  await queryClient.cancelQueries({ queryKey });

  const previousData = queryClient.getQueryData<TData[]>(queryKey);

  queryClient.setQueryData<TData[]>(queryKey, (old = []) => [...old, newItem]);

  return { previousData };
}
