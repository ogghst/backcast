/**
 * WebSocket Chat Hook
 *
 * Manages WebSocket connection for streaming AI chat responses.
 * Handles connection lifecycle, message parsing, reconnection logic,
 * and cleanup.
 *
 * Protocol specification:
 * backend/app/api/v1/endpoints/ws/chat.py
 */

import { useCallback, useEffect, useRef, useState } from "react";
import { useAuthStore } from "@/stores/useAuthStore";
import type {
  WSChatRequest,
  WSServerMessage,
} from "../types";
import {
  WSConnectionState,
  isTokenMessage,
  isToolCallMessage,
  isToolResultMessage,
  isCompleteMessage,
  isErrorMessage,
} from "../types";

/**
 * Configuration for the streaming chat hook
 */
export interface UseStreamingChatConfig {
  /** Optional existing session ID (resumes session if provided) */
  sessionId?: string;
  /** The assistant configuration ID to use for the chat */
  assistantId: string;
  /** Callback invoked when a token is received */
  onToken: (token: string, sessionId: string) => void;
  /** Callback invoked when the complete response is received */
  onComplete: (sessionId: string, messageId: string) => void;
  /** Callback invoked when an error occurs */
  onError: (error: string) => void;
  /** Optional callback invoked when a tool is called */
  onToolCall?: (tool: string, args: Record<string, unknown>) => void;
  /** Optional callback invoked when a tool result is received */
  onToolResult?: (tool: string, result: unknown) => void;
}

/**
 * Return value for the streaming chat hook
 */
export interface UseStreamingChatReturn {
  /** Send a message to start/restart streaming */
  sendMessage: (message: string) => void;
  /** Cancel the current request and close the connection */
  cancel: () => void;
  /** Current WebSocket connection state */
  connectionState: WSConnectionState;
  /** Error if one occurred */
  error: Error | null;
}

/**
 * Maximum number of reconnection attempts before giving up
 */
const MAX_RECONNECT_ATTEMPTS = 5;

/**
 * Base delay for exponential backoff (in milliseconds)
 */
const BASE_RECONNECT_DELAY = 1000;

/**
 * Constructs the WebSocket URL with authentication token
 *
 * @param token - JWT auth token
 * @returns WebSocket URL
 */
function getWebSocketUrl(token: string): string {
  // Use the API URL from environment variable for WebSocket connection
  // This ensures we connect directly to the backend server
  const apiUrl = import.meta.env.VITE_API_URL || window.location.origin;
  const url = new URL(apiUrl);

  // Convert HTTP/HTTPS to WS/WSS protocol
  const protocol = url.protocol === "https:" ? "wss:" : "ws:";
  const host = url.host;

  return `${protocol}//${host}/api/v1/ai/chat/stream?token=${token}`;
}

/**
 * Hook to manage WebSocket connection for streaming AI chat
 *
 * @param config - Configuration object with callbacks and settings
 * @returns Object with sendMessage, cancel, connectionState, and error
 *
 * @example
 * ```tsx
 * const { sendMessage, cancel, connectionState, error } = useStreamingChat({
 *   assistantId: "assistant-123",
 *   onToken: (token, sessionId) => console.log("Token:", token),
 *   onComplete: (sessionId, messageId) => console.log("Complete:", sessionId, messageId),
 *   onError: (error) => console.error("Error:", error),
 * });
 * ```
 */
export const useStreamingChat = (
  config: UseStreamingChatConfig
): UseStreamingChatReturn => {
  const {
    sessionId,
    assistantId,
    onToken,
    onComplete,
    onError,
    onToolCall,
    onToolResult,
  } = config;

  // Get JWT token from auth store
  const token = useAuthStore((state): string | null => state.token);

  // WebSocket reference (not in state to avoid re-renders)
  const wsRef = useRef<WebSocket | null>(null);

  // Track if we've intentionally cancelled (to prevent reconnection)
  const cancelledRef = useRef(false);

  // Reconnection attempt counter
  const reconnectAttemptsRef = useRef(0);

  // Timeout reference for reconnection delays
  const reconnectTimeoutRef = useRef<number | null>(null);

  // Connection state
  const [connectionState, setConnectionState] =
    useState<WSConnectionState>(WSConnectionState.CLOSED);

  // Error state
  const [error, setError] = useState<Error | null>(null);

  /**
   * Handles incoming WebSocket messages
   */
  const handleMessage = useCallback(
    (event: MessageEvent) => {
      try {
        const message: WSServerMessage = JSON.parse(event.data);

        // Handle token messages
        if (isTokenMessage(message)) {
          onToken(message.content, message.session_id);
          return;
        }

        // Handle tool call messages
        if (isToolCallMessage(message)) {
          onToolCall?.(message.tool, message.args);
          return;
        }

        // Handle tool result messages
        if (isToolResultMessage(message)) {
          onToolResult?.(message.tool, message.result);
          return;
        }

        // Handle completion messages
        if (isCompleteMessage(message)) {
          onComplete(message.session_id, message.message_id);
          // Keep connection alive — do NOT close here.
          // The connection will be closed when the component unmounts
          // or the user explicitly cancels (via the cancel() function).
          return;
        }

        // Handle error messages
        if (isErrorMessage(message)) {
          const errorMsg = message.code
            ? `Error ${message.code}: ${message.message}`
            : message.message;
          onError(errorMsg);
          setError(new Error(errorMsg));
          setConnectionState(WSConnectionState.ERROR);
          return;
        }

        // Unknown message type - log for debugging
        console.warn("Unknown WebSocket message type:", message);
      } catch (err) {
        console.error("Error parsing WebSocket message:", err);
        onError("Failed to parse server message");
        setError(new Error("Failed to parse server message"));
      }
    },
    [onToken, onComplete, onError, onToolCall, onToolResult]
  );

  /**
   * Send a message to start streaming
   */
  const sendMessage = useCallback(
    (message: string) => {
      const ws = wsRef.current;

      if (!ws || ws.readyState !== WebSocket.OPEN) {
        const errorMsg = "WebSocket is not connected";
        onError(errorMsg);
        setError(new Error(errorMsg));
        return;
      }

      // Reset cancelled state when sending a new message
      cancelledRef.current = false;
      reconnectAttemptsRef.current = 0;

      // Send chat request
      const request: WSChatRequest = {
        type: "chat",
        message,
        session_id: sessionId ?? null,
        assistant_config_id: assistantId,
      };

      try {
        ws.send(JSON.stringify(request));
      } catch (err) {
        const errorMsg =
          err instanceof Error ? err.message : "Failed to send message";
        onError(errorMsg);
        setError(new Error(errorMsg));
      }
    },
    [sessionId, assistantId, onError]
  );

  /**
   * Cancel the current request and close the connection
   */
  const cancel = useCallback(() => {
    cancelledRef.current = true;

    // Clear any pending reconnection timeout
    if (reconnectTimeoutRef.current !== null) {
      window.clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }

    // Close WebSocket if open
    if (wsRef.current) {
      setConnectionState(WSConnectionState.CLOSING);
      wsRef.current.close();
      wsRef.current = null;
    }
  }, []);

  // Establish connection and set up lifecycle
  useEffect(() => {
    // Only connect if we have a token and an assistant has been selected
    if (!token || !assistantId) {
      return;
    }

    // Reset cancelled state on mount to support React Strict Mode remounting
    cancelledRef.current = false;

    /**
     * Schedules a reconnection attempt with exponential backoff
     */
    const scheduleReconnect = () => {
      if (
        !cancelledRef.current &&
        reconnectAttemptsRef.current < MAX_RECONNECT_ATTEMPTS
      ) {
        reconnectAttemptsRef.current += 1;
        const delay =
          BASE_RECONNECT_DELAY *
          Math.pow(2, reconnectAttemptsRef.current - 1);

        console.log(
          `WebSocket closed, reconnecting in ${delay}ms (attempt ${reconnectAttemptsRef.current}/${MAX_RECONNECT_ATTEMPTS})...`
        );

        reconnectTimeoutRef.current = window.setTimeout(() => {
          // Recursively call connect to reconnect
          connect();
        }, delay);
      } else if (!cancelledRef.current) {
        const errorMsg = `Connection closed after ${MAX_RECONNECT_ATTEMPTS} reconnection attempts`;
        onError(errorMsg);
        setError(new Error(errorMsg));
      }
    };

    /**
     * Creates a new WebSocket connection and sets up event handlers
     */
    const connect = () => {
      // Clear any existing reconnection timeout
      if (reconnectTimeoutRef.current !== null) {
        window.clearTimeout(reconnectTimeoutRef.current);
        reconnectTimeoutRef.current = null;
      }

      // Don't reconnect if we've been cancelled
      if (cancelledRef.current) {
        return;
      }

      setConnectionState(WSConnectionState.CONNECTING);
      setError(null);

      try {
        const ws = new WebSocket(getWebSocketUrl(token));
        wsRef.current = ws;

        // Connection opened
        ws.addEventListener("open", () => {
          setConnectionState(WSConnectionState.OPEN);
          reconnectAttemptsRef.current = 0; // Reset reconnection counter
        });

        // Handle incoming messages
        ws.addEventListener("message", handleMessage);

        // Handle connection close
        ws.addEventListener("close", () => {
          setConnectionState(WSConnectionState.CLOSED);
          wsRef.current = null;
          scheduleReconnect();
        });

        // Handle errors
        ws.addEventListener("error", () => {
          if (cancelledRef.current) return;
          
          setConnectionState(WSConnectionState.ERROR);
          const errorMsg = "WebSocket connection error";
          onError(errorMsg);
          setError(new Error(errorMsg));
        });
      } catch (err) {
        const errorMsg =
          err instanceof Error
            ? err.message
            : "Failed to create WebSocket connection";
        onError(errorMsg);
        setError(new Error(errorMsg));
        setConnectionState(WSConnectionState.ERROR);
      }
    };

    // Initial connection
    connect();

    // Cleanup on unmount
    return () => {
      cancel();
    };
  }, [token, assistantId, handleMessage, onError, cancel]);

  return {
    sendMessage,
    cancel,
    connectionState,
    error,
  };
};
