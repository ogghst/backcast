/**
 * useNotificationStream
 *
 * Opens a single WebSocket connection to the unified notification stream,
 * authenticated via the existing JWT (same scheme as the chat WS). Mounted
 * once in AppLayout. Drives the notification badge + list through the TanStack
 * Query cache (and surfaces toasts for new notifications).
 *
 * Server frames:
 *   { type: "badge_update", unread_count: number }  — authoritative count
 *   { type: "notification", notification: {...} }     — new-notification ping
 *
 * Reconnect uses exponential backoff mirroring useStreamingChat. On close
 * code 4008 (token expired) we do NOT auto-reconnect — the token-refresh
 * timer will rotate the token and the next consumer mount reconnects.
 */
import { useEffect, useRef } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { useAuthStore } from "@/stores/useAuthStore";
import { queryKeys } from "@/api/queryKeys";
import type {
  NotificationSeverity,
} from "./useNotifications";

/** Maximum reconnection attempts before giving up. */
const MAX_RECONNECT_ATTEMPTS = 5;
/** Base delay (ms) for exponential backoff. */
const BASE_RECONNECT_DELAY = 1000;
/** Close code indicating an expired/invalid token — do not auto-reconnect. */
const TOKEN_EXPIRED_CLOSE_CODE = 4008;

/**
 * Lightweight payload of a `notification` frame. May lack id/created_at — it
 * is treated as a *signal* to refetch + toast, not a complete row.
 */
interface WSNotificationPing {
  event_type?: string;
  title?: string;
  message?: string;
  severity?: NotificationSeverity;
  category?: string;
  resource_type?: string | null;
  resource_id?: string | null;
}

interface WSBadgeUpdate {
  type: "badge_update";
  unread_count: number;
}

interface WSNotificationFrame {
  type: "notification";
  notification: WSNotificationPing;
}

type WSServerFrame = WSBadgeUpdate | WSNotificationFrame;

/**
 * Build the notification stream WebSocket URL from the same API base as the
 * chat WS, attaching the JWT as a query param. Mirrors useStreamingChat.
 */
function getNotificationStreamUrl(token: string): string {
  const apiUrl = import.meta.env.VITE_API_URL || window.location.origin;
  const url = new URL(apiUrl);
  const protocol = url.protocol === "https:" ? "wss:" : "ws:";
  return `${protocol}//${url.host}/api/v1/notifications/stream?token=${token}`;
}

/** Map a severity to a Sonner toast method. */
function fireToast(n: WSNotificationPing): void {
  const title = n.title ?? "New notification";
  const description = n.message;
  switch (n.severity) {
    case "urgent":
      toast.error(title, description ? { description } : undefined);
      break;
    case "warning":
      toast.warning(title, description ? { description } : undefined);
      break;
    case "notice":
      toast.info(title, description ? { description } : undefined);
      break;
    default:
      toast(title, description ? { description } : undefined);
  }
}

/**
 * Hook (mount once, e.g. in AppLayout). Opens the notification WS, keeps the
 * unread-count + list cache in sync, and shows toasts for new notifications.
 */
export function useNotificationStream(): void {
  const queryClient = useQueryClient();

  // Read the token reactively so a login/logout reconnects the effect.
  const token = useAuthStore((state) => state.token);

  const wsRef = useRef<WebSocket | null>(null);
  const cancelledRef = useRef(false);
  const reconnectAttemptsRef = useRef(0);
  const reconnectTimeoutRef = useRef<number | null>(null);

  useEffect(() => {
    if (!token) {
      return;
    }

    cancelledRef.current = false;

    const scheduleReconnect = () => {
      if (
        !cancelledRef.current &&
        reconnectAttemptsRef.current < MAX_RECONNECT_ATTEMPTS
      ) {
        reconnectAttemptsRef.current += 1;
        const delay =
          BASE_RECONNECT_DELAY *
          Math.pow(2, reconnectAttemptsRef.current - 1);
        reconnectTimeoutRef.current = window.setTimeout(() => {
          connect();
        }, delay);
      }
    };

    const connect = () => {
      if (cancelledRef.current) return;
      if (reconnectTimeoutRef.current !== null) {
        window.clearTimeout(reconnectTimeoutRef.current);
        reconnectTimeoutRef.current = null;
      }

      let ws: WebSocket;
      try {
        ws = new WebSocket(getNotificationStreamUrl(token));
      } catch {
        scheduleReconnect();
        return;
      }
      wsRef.current = ws;

      ws.addEventListener("open", () => {
        reconnectAttemptsRef.current = 0;
      });

      ws.addEventListener("message", (event: MessageEvent) => {
        let frame: WSServerFrame;
        try {
          frame = JSON.parse(event.data) as WSServerFrame;
        } catch {
          return;
        }

        if (frame.type === "badge_update") {
          // Authoritative server count — write straight to the cache.
          queryClient.setQueryData<{ count: number }>(
            queryKeys.notifications.unreadCount(),
            { count: frame.unread_count },
          );
          return;
        }

        if (frame.type === "notification") {
          const n = frame.notification ?? {};
          fireToast(n);
          // Refetch the list so the new row appears.
          queryClient.invalidateQueries({
            queryKey: queryKeys.notifications.lists(),
          });
          // Optimistically bump the unread count until the next badge_update.
          queryClient.setQueryData<{ count: number }>(
            queryKeys.notifications.unreadCount(),
            (prev) => ({ count: (prev?.count ?? 0) + 1 }),
          );
        }
      });

      ws.addEventListener("close", (event: CloseEvent) => {
        wsRef.current = null;
        // Token expired / invalid — do not auto-reconnect; the token-refresh
        // timer or re-login must rotate the credential first.
        if (event.code === TOKEN_EXPIRED_CLOSE_CODE) {
          return;
        }
        scheduleReconnect();
      });

      // On error, let the close handler drive reconnection.
      ws.addEventListener("error", () => {
        /* no-op — close follows */
      });
    };

    // Reconnect when the browser tab becomes visible after being hidden
    // (backgrounded tabs may have their sockets silently killed by the OS).
    const handleVisibilityChange = () => {
      if (document.visibilityState !== "visible") return;
      if (cancelledRef.current) return;
      const ws = wsRef.current;
      if (ws === null || ws.readyState !== WebSocket.OPEN) {
        if (ws && ws.readyState !== WebSocket.CONNECTING) {
          try {
            ws.close();
          } catch {
            /* ignore */
          }
          wsRef.current = null;
        }
        reconnectAttemptsRef.current = 0;
        connect();
      }
    };
    document.addEventListener("visibilitychange", handleVisibilityChange);

    connect();

    return () => {
      cancelledRef.current = true;
      document.removeEventListener("visibilitychange", handleVisibilityChange);
      if (reconnectTimeoutRef.current !== null) {
        window.clearTimeout(reconnectTimeoutRef.current);
        reconnectTimeoutRef.current = null;
      }
      if (wsRef.current) {
        try {
          wsRef.current.close();
        } catch {
          /* ignore */
        }
        wsRef.current = null;
      }
    };
  }, [token, queryClient]);
}
