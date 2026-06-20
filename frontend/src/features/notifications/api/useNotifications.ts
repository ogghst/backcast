/**
 * TanStack Query hooks for Notifications API.
 *
 * Provides hooks for listing, reading, and tracking unread notification count.
 */
import {
  useQuery,
  useMutation,
  useQueryClient,
  type UseQueryOptions,
  type UseMutationOptions,
} from "@tanstack/react-query";
import { toast } from "sonner";
import { OpenAPI } from "@/api/generated/core/OpenAPI";
import { request as __request } from "@/api/generated/core/request";
import { queryKeys } from "@/api/queryKeys";

// ---------------------------------------------------------------------------
// Types matching backend Notification API schemas
// ---------------------------------------------------------------------------

export type NotificationSeverity = "info" | "notice" | "warning" | "urgent";

export type NotificationCategory =
  | "change_order"
  | "agent"
  | "project"
  | "document"
  | "branch"
  | "system";

export type NotificationChannel = "in_app" | "telegram";

export interface NotificationResponse {
  id: string;
  user_id: string;
  event_type: string;
  title: string;
  message: string;
  resource_type: string | null;
  resource_id: string | null;
  read_at: string | null;
  created_at: string;
  severity: NotificationSeverity;
  actor_type: string | null;
  actor_id: string | null;
  project_id: string | null;
  category: NotificationCategory;
}

export interface NotificationListResponse {
  items: NotificationResponse[];
  total: number;
  page: number;
  per_page: number;
}

export interface UnreadCountResponse {
  count: number;
}

export interface MarkReadResponse {
  updated_count: number;
}

export interface NotificationListParams {
  page?: number;
  pageSize?: number;
  unreadOnly?: boolean;
  category?: NotificationCategory;
  severity?: NotificationSeverity;
}

// ---------------------------------------------------------------------------
// Query hooks
// ---------------------------------------------------------------------------

/**
 * Fetch paginated list of notifications for the current user.
 */
export function useNotifications(
  params?: NotificationListParams,
  options?: Omit<
    UseQueryOptions<NotificationListResponse, Error>,
    "queryKey" | "queryFn"
  >,
) {
  return useQuery<NotificationListResponse, Error>({
    queryKey: queryKeys.notifications.list(params),
    queryFn: async () => {
      const searchParams = new URLSearchParams();
      if (params?.page) searchParams.set("page", String(params.page));
      if (params?.pageSize) searchParams.set("page_size", String(params.pageSize));
      if (params?.unreadOnly) searchParams.set("unread_only", "true");
      if (params?.category) searchParams.set("category", params.category);
      if (params?.severity) searchParams.set("severity", params.severity);
      const qs = searchParams.toString();
      const url = `/api/v1/notifications${qs ? `?${qs}` : ""}`;
      return __request(OpenAPI, { method: "GET", url }) as Promise<NotificationListResponse>;
    },
    ...options,
  });
}

/**
 * Fetch the unread notification count for the current user.
 * Used for badge display in the notification bell icon.
 */
export function useUnreadNotificationCount(
  options?: Omit<
    UseQueryOptions<UnreadCountResponse, Error>,
    "queryKey" | "queryFn"
  >,
) {
  return useQuery<UnreadCountResponse, Error>({
    queryKey: queryKeys.notifications.unreadCount(),
    queryFn: async () => {
      return __request(OpenAPI, {
        method: "GET",
        url: "/api/v1/notifications/unread-count",
      }) as Promise<UnreadCountResponse>;
    },
    ...options,
  });
}

// ---------------------------------------------------------------------------
// Mutation hooks
// ---------------------------------------------------------------------------

/**
 * Mark a single notification as read.
 * Invalidates notification list and unread count on success.
 */
export function useMarkNotificationRead(
  mutationOptions?: Omit<
    UseMutationOptions<MarkReadResponse, Error, string>,
    "mutationFn"
  >,
) {
  const queryClient = useQueryClient();

  return useMutation<MarkReadResponse, Error, string>({
    mutationFn: (notificationId: string) =>
      __request(OpenAPI, {
        method: "PUT",
        url: `/api/v1/notifications/${notificationId}/read`,
      }) as Promise<MarkReadResponse>,
    onSuccess: async (data, ...args) => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: queryKeys.notifications.all }),
      ]);
      mutationOptions?.onSuccess?.(data, ...args);
    },
    onError: (error: Error, ...args) => {
      toast.error(`Failed to mark notification as read: ${error.message}`);
      mutationOptions?.onError?.(error, ...args);
    },
  });
}

/**
 * Mark all unread notifications as read for the current user.
 * Invalidates notification list and unread count on success.
 */
export function useMarkAllNotificationsRead(
  mutationOptions?: Omit<
    UseMutationOptions<MarkReadResponse, Error, void>,
    "mutationFn"
  >,
) {
  const queryClient = useQueryClient();

  return useMutation<MarkReadResponse, Error, void>({
    mutationFn: () =>
      __request(OpenAPI, {
        method: "PUT",
        url: "/api/v1/notifications/read-all",
      }) as Promise<MarkReadResponse>,
    onSuccess: async (data, ...args) => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: queryKeys.notifications.all }),
      ]);
      toast.success("All notifications marked as read");
      mutationOptions?.onSuccess?.(data, ...args);
    },
    onError: (error: Error, ...args) => {
      toast.error(`Failed to mark all notifications as read: ${error.message}`);
      mutationOptions?.onError?.(error, ...args);
    },
  });
}
