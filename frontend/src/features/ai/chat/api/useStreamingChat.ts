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
  isTokenBatchMessage,
  isToolCallMessage,
  isToolResultMessage,
  isCompleteMessage,
  isErrorMessage,
  isPermissionDeniedMessage,
  isApprovalRequestMessage,
  isThinkingMessage,
  isPollingHeartbeatMessage,
  isContentResetMessage,
  isSubagentMessage,
  isSubagentResultMessage,
  isAgentCompleteMessage,
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
  onToken: (token: string, sessionId: string, source?: "main" | "subagent", subagentName?: string, invocationId?: string) => void;
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
  /** Optional callback invoked on each heartbeat with remaining seconds */
  onApprovalCountdown?: (remaining: number) => void;
  /** Optional callback invoked when approval polling times out */
  onApprovalTimeout?: () => void;
  /** Optional callback invoked when agent is thinking */
  onThinking?: () => void;
  /** Optional callback invoked when a subagent starts */
  onSubagentStart?: (subagent: string, invocationId: string, message?: string) => void;
  /** Optional callback invoked when a subagent completes */
  onSubagentComplete?: (invocationId: string) => void;
  /** Optional callback invoked when the main agent completes */
  onMainAgentComplete?: (invocationId: string) => void;
  /** Optional callback invoked when content is reset (e.g., after subagent completes) */
  onContentReset?: (reason: string) => void;
  /** Optional callback invoked with every raw WebSocket message (for debugging) */
  onRawMessage?: (message: unknown, direction: "in" | "out") => void;
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
    onApprovalCountdown,
    onApprovalTimeout,
    onThinking,
    onSubagentStart,
    onSubagentComplete,
    onMainAgentComplete,
    onContentReset,
    onRawMessage,
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
    onApprovalCountdown,
    onApprovalTimeout,
    onThinking,
    onSubagentStart,
    onSubagentComplete,
    onMainAgentComplete,
    onContentReset,
    onRawMessage,
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
      onApprovalCountdown,
      onApprovalTimeout,
      onThinking,
      onSubagentStart,
      onSubagentComplete,
      onMainAgentComplete,
      onContentReset,
      onRawMessage,
    };
  });

  // Track if this is the first mount to handle React Strict Mode
  // In Strict Mode, effects run twice: mount -> unmount -> mount
  // We use this ref to prevent creating duplicate connections during remount
  const isFirstMountRef = useRef(true);

  // Approval countdown tracking refs
  const pendingApprovalIdRef = useRef<string | null>(null);
  const remainingSecondsRef = useRef<number>(0);
  const maxRemainingRef = useRef<number>(0);
  const timeoutFiredRef = useRef(false);

  // Timeout for complete message (prevents stuck state)
  const completeTimeoutRef = useRef<number | null>(null);
  // Use a mutable object to track last message time (avoids purity issues)
  const lastMessageTimeRef = useRef({ current: 0 });

  // Initialize last message time on mount
  useEffect(() => {
    lastMessageTimeRef.current.current = Date.now();
  }, []);

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
   * Clears the complete message timeout
   */
  const clearCompleteTimeout = useCallback(() => {
    if (completeTimeoutRef.current !== null) {
      window.clearTimeout(completeTimeoutRef.current);
      completeTimeoutRef.current = null;
    }
  }, []);

  /**
   * Starts the complete message timeout. If no 'complete' message arrives
   * within the specified duration, triggers an error state.
   */
  const startCompleteTimeout = useCallback(() => {
    clearCompleteTimeout();

    // Timeout after 2 minutes of no complete message
    const TIMEOUT_MS = 120000;

    completeTimeoutRef.current = window.setTimeout(() => {
      const timeSinceLastMessage = Date.now() - lastMessageTimeRef.current.current;

      // Only trigger timeout if we haven't received any message recently
      // This prevents false positives during slow but valid streams
      if (timeSinceLastMessage > TIMEOUT_MS) {
        const errorMsg = "Response timeout: No complete message received. The stream may have been interrupted.";
        callbacksRef.current.onError?.(errorMsg);
        setError(new Error(errorMsg));
        setConnectionState(WSConnectionState.ERROR);
      }
    }, TIMEOUT_MS);
  }, [clearCompleteTimeout]);

  /**
   * Handles incoming WebSocket messages by parsing JSON and routing to the
   * appropriate callback based on the message type discriminator.
   *
   * Context: Attached as a listener to the WebSocket instance. Uses callbacksRef
   * to access the latest callback closures without triggering reconnection cycles.
   * Handles all message types defined in the WSServerMessage union plus the
   * out-of-band approval_request type.
   *
   * @param event - Raw MessageEvent from the WebSocket onmessage handler
   */
  const handleMessage = useCallback((event: MessageEvent) => {
    const callbacks = callbacksRef.current;
    const rawData = event.data;

    // Update last message time (for timeout detection)
    lastMessageTimeRef.current.current = Date.now();

    try {
      const message = JSON.parse(rawData);

      // Handle ping/pong keepalive — respond silently (before debug callback to prevent redraws).
      // No React state changes — ws.send() is a raw socket operation,
      // so this won't trigger redraws, debug panel updates, or chat scrolling.
      if (message.type === "ping") {
        const ws = wsRef.current;
        if (ws && ws.readyState === WebSocket.OPEN) {
          ws.send(JSON.stringify({ type: "pong" }));
        }
        return;
      }

      // Debug callback for raw incoming messages (before processing)
      callbacks.onRawMessage?.(message, "in");

      // Handle approval request messages (custom type, not in WSServerMessage union)
      if (isApprovalRequestMessage(message)) {
        // Reset countdown tracking for the new approval request
        pendingApprovalIdRef.current = message.approval_id;
        remainingSecondsRef.current = 0;
        maxRemainingRef.current = 0;
        timeoutFiredRef.current = false;
        callbacks.onApprovalRequest?.(message);
        return;
      }

      const serverMessage: WSServerMessage = message;

      // Handle batched token messages (new optimized path)
      if (isTokenBatchMessage(serverMessage)) {
        // Send pre-concatenated token string directly with invocation_id
        callbacks.onToken(
          serverMessage.tokens,
          serverMessage.session_id,
          serverMessage.source,
          serverMessage.subagent_name,
          serverMessage.invocation_id
        );
        return;
      }

      // Handle individual token messages (backward compatible)
      if (isTokenMessage(serverMessage)) {
        callbacks.onToken(
          serverMessage.content,
          serverMessage.session_id,
          serverMessage.source,
          serverMessage.subagent_name,
          serverMessage.invocation_id
        );
        return;
      }

      // Handle subagent delegation messages
      if (isSubagentMessage(serverMessage)) {
        callbacks.onSubagentStart?.(serverMessage.subagent, serverMessage.invocation_id, serverMessage.message);
        // Also call tool_call handler for activity panel
        callbacks.onToolCall?.("task", { subagent_type: serverMessage.subagent });
        return;
      }

      // Handle subagent result messages
      if (isSubagentResultMessage(serverMessage)) {
        callbacks.onSubagentComplete?.(serverMessage.invocation_id);
        // Also call tool_result handler for activity panel
        callbacks.onToolResult?.("task", serverMessage.content);
        return;
      }

      // Handle agent complete messages
      if (isAgentCompleteMessage(serverMessage)) {
        if (serverMessage.agent_type === "main") {
          callbacks.onMainAgentComplete?.(serverMessage.invocation_id);
        } else if (serverMessage.agent_type === "subagent") {
          callbacks.onSubagentComplete?.(serverMessage.invocation_id);
        }
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

      // Handle content reset messages (sent when subagent completes)
      if (isContentResetMessage(serverMessage)) {
        callbacks.onContentReset?.(serverMessage.reason);
        return;
      }

      // Handle thinking messages (agent is processing)
      if (isThinkingMessage(serverMessage)) {
        callbacks.onThinking?.();
        return;
      }

      // Handle polling heartbeat messages
      if (isPollingHeartbeatMessage(serverMessage)) {
        const remaining = serverMessage.remaining_seconds;

        // Track max remaining from first heartbeat to compute progress percentage
        if (maxRemainingRef.current === 0 || remaining > maxRemainingRef.current) {
          maxRemainingRef.current = remaining;
        }
        remainingSecondsRef.current = remaining;

        console.debug(
          `Polling heartbeat: approval_id=${serverMessage.approval_id}, ` +
          `elapsed=${serverMessage.elapsed_seconds.toFixed(1)}s, ` +
          `remaining=${remaining.toFixed(1)}s`
        );

        // Notify parent of countdown update
        callbacks.onApprovalCountdown?.(remaining);

        // Fire timeout callback exactly once when remaining reaches zero
        if (remaining <= 0 && pendingApprovalIdRef.current && !timeoutFiredRef.current) {
          timeoutFiredRef.current = true;
          pendingApprovalIdRef.current = null;
          callbacks.onApprovalTimeout?.();
        }

        return;
      }

      // Handle completion messages
      if (isCompleteMessage(serverMessage)) {
        clearCompleteTimeout(); // Clear timeout when complete arrives
        callbacks.onComplete(serverMessage.session_id, serverMessage.message_id);
        // Keep connection alive — do NOT close here.
        // The connection will be closed when the component unmounts
        // or the user explicitly cancels (via the cancel() function).
        return;
      }

      // Handle error messages
      if (isErrorMessage(serverMessage)) {
        clearCompleteTimeout(); // Clear timeout on error too
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
      // Enhanced error logging for debugging parse failures
      console.error("=== WebSocket Parse Error ===");
      console.error("Error:", err);
      console.error("Raw message type:", typeof rawData);
      console.error("Raw message length:", rawData?.length);
      console.error("Raw message preview:", rawData?.substring(0, 500));
      console.error("Full raw message:", rawData);

      // Try to identify what message type this might be from raw data
      if (typeof rawData === "string") {
        const typeMatch = rawData.match(/"type"\s*:\s*"([^"]+)"/);
        if (typeMatch) {
          console.error("Detected message type from regex:", typeMatch[1]);
        }
      }

      const errorMsg = `Failed to parse server message (type: ${typeof rawData}, length: ${rawData?.length}, detected_type: ${typeof rawData === "string" ? rawData.match(/"type"\s*:\s*"([^"]+)"/)?.[1] || "unknown" : "not_string"})`;
      callbacks.onError(errorMsg);
      setError(new Error(errorMsg));
    }
  }, [clearCompleteTimeout]); // Uses ref for callbacks, needs clearCompleteTimeout

  /**
   * Sends a chat message over the active WebSocket connection.
   *
   * Context: Called by ChatInterface when the user submits a message. Constructs
   * a WSChatRequest with temporal context from the Time Machine store and the
   * selected execution mode, then sends it as JSON over the WebSocket.
   *
   * @param message - User's chat message text
   * @param title - Optional title for new chat sessions
   * @param executionMode - AI tool risk level (safe/standard/expert)
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

      // Start complete message timeout
      startCompleteTimeout();

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

      // Debug callback for raw outgoing message
      callbacksRef.current.onRawMessage?.(request, "out");

      try {
        ws.send(JSON.stringify(request));
      } catch (err) {
        const errorMsg =
          err instanceof Error ? err.message : "Failed to send message";
        onError(errorMsg);
        setError(new Error(errorMsg));
      }
    },
    [sessionId, assistantId, onError, getSelectedTime, getSelectedBranch, getViewMode, startCompleteTimeout]
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

      // Debug callback for raw outgoing message
      callbacksRef.current.onRawMessage?.(response, "out");

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
   * Cancels the current request and closes the WebSocket connection.
   *
   * Context: Called by ChatInterface when the user clicks cancel during streaming.
   * Intentionally NOT memoized with useCallback to avoid being in the useEffect
   * dependency array, which would cause reconnection loops. The cleanup function
   * directly closes the connection without using this function.
   */
  const cancel = () => {
    cancelledRef.current = true;

    // Clear complete message timeout
    if (completeTimeoutRef.current !== null) {
      window.clearTimeout(completeTimeoutRef.current);
      completeTimeoutRef.current = null;
    }

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
     * Creates a new WebSocket connection and sets up lifecycle event handlers.
     *
     * Context: Called on mount and during reconnection attempts. Handles the
     * full connection lifecycle: open (updates state), message (delegates to
     * handleMessage), close (triggers reconnection with backoff), and error
     * (surfaces to user via onError callback).
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
        ws.addEventListener("close", (event: CloseEvent) => {
          setConnectionState(WSConnectionState.CLOSED);
          wsRef.current = null;

          // Don't reconnect on policy violations (auth failure)
          if (event.code === 1008) {
            const errorMsg = "Authentication failed. Please log in again.";
            const callbacks = callbacksRef.current;
            callbacks.onError(errorMsg);
            setError(new Error(errorMsg));
            return;
          }

          // Token expired (4008) or normal closure (1000) — reconnect with backoff.
          // By the time the backoff completes, the auth store may have a refreshed token.
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

      // Clear complete message timeout
      clearCompleteTimeout();

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
  }, [token, assistantId, handleMessage, clearCompleteTimeout]); // Only reconnect when token or assistantId changes

  return {
    sendMessage,
    sendApprovalResponse,
    cancel,
    connectionState,
    error,
  };
};
