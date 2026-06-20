/**
 * TanStack Query hooks for Notification Preferences and Telegram integration.
 *
 * Mirrors the style of useNotifications.ts: query/mutation + cache invalidation.
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
import type { NotificationChannel } from "./useNotifications";

// ---------------------------------------------------------------------------
// Types matching backend preferences + telegram schemas
// ---------------------------------------------------------------------------

export interface NotificationPreferenceEntry {
  event_type: string;
  channel: NotificationChannel;
  enabled: boolean;
}

export interface NotificationPreferenceCategory {
  category: string;
  label: string;
  entries: NotificationPreferenceEntry[];
}

export interface NotificationPreferencesResponse {
  categories: NotificationPreferenceCategory[];
}

export interface NotificationPreferenceChange {
  event_type: string;
  channel: NotificationChannel;
  enabled: boolean;
}

export interface UpdateNotificationPreferencesRequest {
  changes: NotificationPreferenceChange[];
}

export interface TelegramConnectResponse {
  bot_username: string;
  connect_url: string;
}

export interface TelegramStatusResponse {
  linked: boolean;
  verified: boolean;
  chat_id: string | null;
  /** Whether Telegram is configured and enabled on the server. */
  available: boolean;
}

// ---------------------------------------------------------------------------
// Preferences hooks
// ---------------------------------------------------------------------------

/**
 * Fetch the notification preference matrix (grouped by category).
 */
export function useNotificationPreferences(
  options?: Omit<
    UseQueryOptions<NotificationPreferencesResponse, Error>,
    "queryKey" | "queryFn"
  >,
) {
  return useQuery<NotificationPreferencesResponse, Error>({
    queryKey: queryKeys.notifications.preferences,
    queryFn: async () =>
      __request(OpenAPI, {
        method: "GET",
        url: "/api/v1/notifications/preferences",
      }) as Promise<NotificationPreferencesResponse>,
    ...options,
  });
}

/**
 * Apply preference changes (event_type/channel/enabled).
 * Invalidates the preferences query on success.
 */
export function useUpdateNotificationPreferences(
  mutationOptions?: Omit<
    UseMutationOptions<
      unknown,
      Error,
      NotificationPreferenceChange[]
    >,
    "mutationFn"
  >,
) {
  const queryClient = useQueryClient();

  return useMutation<unknown, Error, NotificationPreferenceChange[]>({
    mutationFn: (changes) =>
      __request(OpenAPI, {
        method: "PUT",
        url: "/api/v1/notifications/preferences",
        body: { changes },
      }),
    onSuccess: async (data, ...args) => {
      await queryClient.invalidateQueries({
        queryKey: queryKeys.notifications.preferences,
      });
      mutationOptions?.onSuccess?.(data, ...args);
    },
    onError: (error: Error, ...args) => {
      toast.error(`Failed to update preferences: ${error.message}`);
      mutationOptions?.onError?.(error, ...args);
    },
  });
}

// ---------------------------------------------------------------------------
// Telegram hooks
// ---------------------------------------------------------------------------

/**
 * Initiate a Telegram connection. Returns the bot username + authorize URL.
 */
export function useConnectTelegram(
  mutationOptions?: Omit<
    UseMutationOptions<TelegramConnectResponse, Error, void>,
    "mutationFn"
  >,
) {
  return useMutation<TelegramConnectResponse, Error, void>({
    mutationFn: () =>
      __request(OpenAPI, {
        method: "POST",
        url: "/api/v1/notifications/telegram/connect",
      }) as Promise<TelegramConnectResponse>,
    ...mutationOptions,
  });
}

/**
 * Poll Telegram linking status. Polls at `refetchInterval` while a connect is
 * pending (caller passes `enabled`/`refetchInterval`); stops once verified.
 */
export function useTelegramStatus(
  options?: Omit<
    UseQueryOptions<TelegramStatusResponse, Error>,
    "queryKey" | "queryFn"
  >,
) {
  return useQuery<TelegramStatusResponse, Error>({
    queryKey: queryKeys.notifications.telegramStatus(),
    queryFn: async () =>
      __request(OpenAPI, {
        method: "GET",
        url: "/api/v1/notifications/telegram/status",
      }) as Promise<TelegramStatusResponse>,
    ...options,
  });
}

/**
 * Disconnect Telegram. Invalidates status on success.
 */
export function useDisconnectTelegram(
  mutationOptions?: Omit<
    UseMutationOptions<void, Error, void>,
    "mutationFn"
  >,
) {
  const queryClient = useQueryClient();

  return useMutation<void, Error, void>({
    mutationFn: async () => {
      await __request(OpenAPI, {
        method: "DELETE",
        url: "/api/v1/notifications/telegram",
      });
    },
    onSuccess: async (data, ...args) => {
      await queryClient.invalidateQueries({
        queryKey: queryKeys.notifications.telegramStatus(),
      });
      toast.success("Telegram disconnected");
      mutationOptions?.onSuccess?.(data, ...args);
    },
    onError: (error: Error, ...args) => {
      toast.error(`Failed to disconnect Telegram: ${error.message}`);
      mutationOptions?.onError?.(error, ...args);
    },
  });
}
