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
import { useTimeMachineStore } from "@/stores/useTimeMachineStore";
import type {
  WSChatRequest,
  WSServerMessage,
  WSApprovalRequestMessage,
  WSApprovalResponseMessage,
} from "../types";
import {
  WSConnectionState,
  isTokenMessage,
  isToolCallMessage,
  isToolResultMessage,
  isCompleteMessage,
  isErrorMessage,
  isPermissionDeniedMessage,
  isApprovalRequestMessage,
  isPlanningMessage,
  isSubagentMessage,
  isThinkingMessage,
  type WSPermissionDeniedMessage,
} from "../types";

/**
 * Configuration for the streaming chat hook
 */
export interface UseStreamingChatConfig {
  /** Optional existing session ID (resumes session if provided) */
  sessionId?: string;
  /** The assistant configuration ID to use for the chat */
  assistantId: string;
  /** Optional project ID to scope chat to a specific project */
  projectId?: string;
  /** Callback invoked when a token is received */
  onToken: (token: string, sessionId: string) => void;
  /** Callback invoked when the complete response is received */
  onComplete: (sessionId: string, messageId: string) => void;
  /** Callback invoked when an error occurs */
  onError: (error: string) => void;
  /** Optional callback invoked when a tool is called */
  onToolCall?: (tool: string, args: Record<string, unknown>) => void;
  /** Optional callback invoked when a tool result is received */
  onToolResult?: (tool: string, result?: unknown) => void;
  /** Optional callback invoked when an approval request is received */
  onApprovalRequest?: (request: WSApprovalRequestMessage) => void;
  /** Optional callback invoked when agent is planning */
  onPlanning?: (plan?: string, steps?: Array<{ text: string; done: boolean }>) => void;
  /** Optional callback invoked when agent delegates to subagent */
  onSubagent?: (subagent: string, message?: string) => void;
  /** Optional callback invoked when agent is thinking */
  onThinking?: () => void;
}

/**
 * Return value for the streaming chat hook
 */
export interface UseStreamingChatReturn {
  /** Send a message to start/restart streaming */
  sendMessage: (message: string, title?: string, executionMode?: "safe" | "standard" | "expert") => void;
  /** Send an approval response for a critical tool execution */
  sendApprovalResponse: (approvalId: string, approved: boolean) => void;
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
 * Formats a permission denied error message with helpful context
 *
 * @param message - Permission denied error message
 * @returns User-friendly error message
 */
function formatPermissionDeniedError(
  message: WSPermissionDeniedMessage
): string {
  const { project_id, required_permission, message: baseMessage } = message;

  if (project_id && required_permission) {
    return `Permission denied: You need '${required_permission}' permission for project ${project_id}. ${baseMessage}`;
  }

  if (project_id) {
    return `Permission denied: You do not have access to project ${project_id}. ${baseMessage}`;
  }

  if (required_permission) {
    return `Permission denied: Required permission: ${required_permission}. ${baseMessage}`;
  }

  return baseMessage;
}

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
    projectId,
    onToken,
    onComplete,
    onError,
    onToolCall,
    onToolResult,
    onApprovalRequest,
    onPlanning,
    onSubagent,
    onThinking,
  } = config;

  // Get JWT token from auth store
  const token = useAuthStore((state): string | null => state.token);

  // Get temporal context from Time Machine store
  const getSelectedTime = useTimeMachineStore((state) => state.getSelectedTime);
  const getSelectedBranch = useTimeMachineStore((state) => state.getSelectedBranch);
  const getViewMode = useTimeMachineStore((state) => state.getViewMode);

  // Store projectId in a ref for the connection lifetime
  const projectIdRef = useRef(projectId);

  // Keep projectIdRef updated when config.projectId changes
  useEffect(() => {
    projectIdRef.current = projectId;
  }, [projectId]);

  // WebSocket reference (not in state to avoid re-renders)
  const wsRef = useRef<WebSocket | null>(null);

  // Track if we've intentionally cancelled (to prevent reconnection)
  const cancelledRef = useRef(false);

  // Reconnection attempt counter
  const reconnectAttemptsRef = useRef(0);

  // Timeout reference for reconnection delays
  const reconnectTimeoutRef = useRef<number | null>(null);

  // Store callbacks in refs to avoid useEffect re-running when they change
  const callbacksRef = useRef({
    onToken,
    onComplete,
    onError,
    onToolCall,
    onToolResult,
    onApprovalRequest,
    onPlanning,
    onSubagent,
    onThinking,
  });

  // Keep callbacks ref updated
  useEffect(() => {
    callbacksRef.current = {
      onToken,
      onComplete,
      onError,
      onToolCall,
      onToolResult,
      onApprovalRequest,
      onPlanning,
      onSubagent,
      onThinking,
    };
  });

  // Track if this is the first mount to handle React Strict Mode
  // In Strict Mode, effects run twice: mount -> unmount -> mount
  // We use this ref to prevent creating duplicate connections during remount
  const isFirstMountRef = useRef(true);

  // Reset first mount ref when token or assistantId changes
  useEffect(() => {
    isFirstMountRef.current = true;
  }, [token, assistantId]);

  // Connection state
  const [connectionState, setConnectionState] =
    useState<WSConnectionState>(WSConnectionState.CLOSED);

  // Error state
  const [error, setError] = useState<Error | null>(null);

  /**
   * Handles incoming WebSocket messages
   * Uses ref to access latest callbacks without triggering reconnection
   */
  const handleMessage = useCallback((event: MessageEvent) => {
    const callbacks = callbacksRef.current;

    try {
      const message = JSON.parse(event.data);

      // Handle approval request messages (custom type, not in WSServerMessage union)
      if (isApprovalRequestMessage(message)) {
        callbacks.onApprovalRequest?.(message);
        return;
      }

      const serverMessage: WSServerMessage = message;

      // Handle token messages
      if (isTokenMessage(serverMessage)) {
        callbacks.onToken(serverMessage.content, serverMessage.session_id);
        return;
      }

      // Handle tool call messages
      if (isToolCallMessage(serverMessage)) {
        callbacks.onToolCall?.(serverMessage.tool, serverMessage.args);
        return;
      }

      // Handle tool result messages
      if (isToolResultMessage(serverMessage)) {
        callbacks.onToolResult?.(serverMessage.tool, serverMessage.result);
        return;
      }

      // Handle planning messages (Deep Agent creating a plan)
      if (isPlanningMessage(serverMessage)) {
        callbacks.onPlanning?.(serverMessage.plan, serverMessage.steps);
        return;
      }

      // Handle subagent messages (Deep Agent delegating to subagent)
      if (isSubagentMessage(serverMessage)) {
        callbacks.onSubagent?.(serverMessage.subagent, serverMessage.message);
        return;
      }

      // Handle thinking messages (agent is processing)
      if (isThinkingMessage(serverMessage)) {
        callbacks.onThinking?.();
        return;
      }

      // Handle completion messages
      if (isCompleteMessage(serverMessage)) {
        callbacks.onComplete(serverMessage.session_id, serverMessage.message_id);
        // Keep connection alive — do NOT close here.
        // The connection will be closed when the component unmounts
        // or the user explicitly cancels (via the cancel() function).
        return;
      }

      // Handle error messages
      if (isErrorMessage(serverMessage)) {
        // Handle permission denied errors (403) with user-friendly message
        if (isPermissionDeniedMessage(serverMessage)) {
          const permissionMsg = formatPermissionDeniedError(serverMessage);
          callbacks.onError(permissionMsg);
          setError(new Error(permissionMsg));
          setConnectionState(WSConnectionState.ERROR);
          return;
        }

        // Handle generic errors
        const errorMsg = serverMessage.code
          ? `Error ${serverMessage.code}: ${serverMessage.message}`
          : serverMessage.message;
        callbacks.onError(errorMsg);
        setError(new Error(errorMsg));
        setConnectionState(WSConnectionState.ERROR);
        return;
      }

      // Unknown message type - log for debugging
      console.warn("Unknown WebSocket message type:", serverMessage);
    } catch (err) {
      console.error("Error parsing WebSocket message:", err);
      callbacks.onError("Failed to parse server message");
      setError(new Error("Failed to parse server message"));
    }
  }, []); // No dependencies - uses ref for callbacks

  /**
   * Send a message to start streaming
   */
  const sendMessage = useCallback(
    (message: string, title?: string, executionMode?: "safe" | "standard" | "expert") => {
      const ws = wsRef.current;

      if (!ws || ws.readyState !== WebSocket.OPEN) {
        const errorMsg = "WebSocket is not connected";
        onError(errorMsg);
        setError(new Error(errorMsg));
        return;
      }

      // Validate execution mode is provided
      if (!executionMode) {
        const errorMsg = "executionMode is required but was not provided";
        console.error(errorMsg);
        onError(errorMsg);
        setError(new Error(errorMsg));
        return;
      }

      // Reset cancelled state when sending a new message
      cancelledRef.current = false;
      reconnectAttemptsRef.current = 0;

      // Read temporal context from Time Machine store
      const asOf = getSelectedTime();
      const branchName = getSelectedBranch();
      const branchMode = getViewMode();

      // Send chat request with temporal params and execution mode
      const request: WSChatRequest = {
        type: "chat",
        message,
        session_id: sessionId ?? null,
        assistant_config_id: assistantId,
        title, // Pass title for new sessions
        as_of: asOf ?? null, // Convert undefined to null for "now"
        branch_name: branchName,
        branch_mode: branchMode,
        project_id: projectIdRef.current, // Include project_id if provided
        execution_mode: executionMode, // No default fallback - must be provided
      };

      console.log("Sending chat request with execution_mode:", executionMode);

      try {
        ws.send(JSON.stringify(request));
      } catch (err) {
        const errorMsg =
          err instanceof Error ? err.message : "Failed to send message";
        onError(errorMsg);
        setError(new Error(errorMsg));
      }
    },
    [sessionId, assistantId, onError, getSelectedTime, getSelectedBranch, getViewMode]
  );

  /**
   * Send an approval response for a critical tool execution
   */
  const sendApprovalResponse = useCallback(
    (approvalId: string, approved: boolean) => {
      const ws = wsRef.current;

      if (!ws || ws.readyState !== WebSocket.OPEN) {
        const errorMsg = "WebSocket is not connected";
        onError(errorMsg);
        setError(new Error(errorMsg));
        return;
      }

      // Get user ID from auth store
      const userId = useAuthStore.getState().user?.id;
      if (!userId) {
        const errorMsg = "User ID not found - cannot send approval response";
        onError(errorMsg);
        setError(new Error(errorMsg));
        return;
      }

      // Create approval response message
      const response: WSApprovalResponseMessage = {
        type: "approval_response",
        approval_id: approvalId,
        approved,
        user_id: userId,
        timestamp: new Date().toISOString(),
      };

      try {
        ws.send(JSON.stringify(response));
      } catch (err) {
        const errorMsg =
          err instanceof Error ? err.message : "Failed to send approval response";
        onError(errorMsg);
        setError(new Error(errorMsg));
      }
    },
    [onError]
  );

  /**
   * Cancel the current request and close the connection
   * NOTE: This is intentionally NOT memoized with useCallback to avoid
   * being in the useEffect dependency array, which would cause reconnection.
   * The cleanup function directly closes the connection without using cancel().
   */
  const cancel = () => {
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
  };

  // Establish connection and set up lifecycle
  useEffect(() => {
    // Only connect if we have a token and an assistant has been selected
    if (!token || !assistantId) {
      return;
    }

    // Handle React Strict Mode: In development, effects run twice (mount-unmount-mount)
    // We only create a connection on the first mount to avoid duplicates
    if (!isFirstMountRef.current) {
      return;
    }

    // Mark as mounted to prevent duplicate connections in Strict Mode
    isFirstMountRef.current = false;

    // Reset cancelled state on mount
    cancelledRef.current = false;

    /**
     * Schedules a reconnection attempt with exponential backoff
     */
    const scheduleReconnect = () => {
      const callbacks = callbacksRef.current;

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
        callbacks.onError(errorMsg);
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
          const callbacks = callbacksRef.current;
          if (cancelledRef.current) return;

          setConnectionState(WSConnectionState.ERROR);
          const errorMsg = "WebSocket connection error";
          callbacks.onError(errorMsg);
          setError(new Error(errorMsg));
        });
      } catch (err) {
        const callbacks = callbacksRef.current;
        const errorMsg =
          err instanceof Error
            ? err.message
            : "Failed to create WebSocket connection";
        callbacks.onError(errorMsg);
        setError(new Error(errorMsg));
        setConnectionState(WSConnectionState.ERROR);
      }
    };

    // Initial connection
    connect();

    // Cleanup on unmount - directly close connection without using cancel()
    return () => {
      // Reset first mount ref to allow reconnection if component remounts
      // with different token/assistantId
      isFirstMountRef.current = true;

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
    };
  }, [token, assistantId, handleMessage]); // Only reconnect when token or assistantId changes

  return {
    sendMessage,
    sendApprovalResponse,
    cancel,
    connectionState,
    error,
  };
};
