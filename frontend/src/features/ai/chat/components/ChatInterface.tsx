/**
 * ChatInterface Component
 *
 * Main container for the AI chat interface.
 * Orchestrates session management, message display, and chat operations.
 * Uses WebSocket streaming for real-time AI responses.
 *
 * Mobile-First Design:
 * - Industrial Technical Minimalism aesthetic
 * - Touch-optimized with 44px minimum touch targets
 * - Gesture-friendly navigation
 * - Smart typography scaling for readability
 */

import { useState, useCallback, useEffect, useMemo, useRef } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { queryKeys } from "@/api/queryKeys";
import { Layout, Alert, Drawer, Button, theme, Tooltip, Grid, Dropdown } from "antd";
import {
  MenuOutlined,
  RobotOutlined,
  PlusOutlined,
  MoreOutlined,
  CloseOutlined,
  BugOutlined,
} from "@ant-design/icons";
import {
  useChatSessions,
  useDeleteSession,
} from "../api/useChatSessions";
import { useChatMessages } from "../api/useChatSessions";
import { useStreamingChat } from "../api/useStreamingChat";
import { AssistantSelector } from "./AssistantSelector";
import { SessionList } from "./SessionList";
import { MessageList } from "./MessageList";
import { MessageInput } from "./MessageInput";
import { AgentActivityPanel } from "./AgentActivityPanel";
import type { AgentActivity, ActivityHistoryItem } from "./AgentActivityPanel";
import { WebSocketDebugPanel, type DebugMessage } from "./WebSocketDebugPanel";
import type { ChatMessage, MainAgentStream, SubagentStream, StreamingState } from "../../types";
import { WSConnectionState, type WSApprovalRequestMessage } from "../types";
import { useThemeTokens } from "@/hooks/useThemeTokens";
import { generateSessionTitle } from "../utils/sessionTitle";
import { useExecutionMode } from "../../hooks/useExecutionMode";
import { ApprovalDialog } from "../../components/ApprovalDialog";

const { Sider, Content, Header } = Layout;
const { useBreakpoint } = Grid;

interface ChatInterfaceProps {
  // URL params can be passed in for direct linking
  sessionId?: string;
  assistantId?: string;
  // Optional project ID to scope chat to a specific project
  projectId?: string;
}

/**
 * Main container for the AI chat interface.
 *
 * Context: Orchestrates the full chat experience including session management,
 * WebSocket streaming, multi-agent rendering (main agent + subagents), tool
 * execution tracking, and approval flows for critical tool operations. Used
 * as the primary route component for the AI chat feature.
 *
 * @param props.sessionId - Optional URL-param session ID for direct linking
 * @param props.assistantId - Optional URL-param assistant ID pre-selection
 * @param props.projectId - Optional project ID to scope chat context
 */
export const ChatInterface = ({
  sessionId: initialSessionId,
  assistantId: initialAssistantId,
  projectId,
}: ChatInterfaceProps) => {
  // Responsive breakpoints
  const screens = useBreakpoint();
  const isMobile = !screens.md; // md breakpoint is 768px
  const isSmallMobile = screens.xs; // xs is 480px

  // State
  const [currentSessionId, setCurrentSessionId] = useState<string | undefined>(
    initialSessionId
  );
  const [selectedAssistantId, setSelectedAssistantId] = useState<
    string | undefined
  >(initialAssistantId);
  const [isSidebarOpen, setSidebarOpen] = useState(false);
  const [isCollapsed, setIsCollapsed] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Streaming state
  const [streamingState, setStreamingState] = useState<StreamingState>({
    main: "",
    mainStreams: new Map<string, MainAgentStream>(),
    subagents: new Map<string, SubagentStream>(),
  });
  const [isWaitingForResponse, setIsWaitingForResponse] = useState(false);
  const [activeToolCalls, setActiveToolCalls] = useState<
    Array<{ name: string; args: Record<string, unknown> }>
  >([]);
  const [toolJustFinished, setToolJustFinished] = useState(false);
  const [showStreamSeparator, setShowStreamSeparator] = useState(false);
  const contentResetOccurredRef = useRef(false);
  const contentResetCounterRef = useRef(0);
  const [pendingUserMessage, setPendingUserMessage] = useState<ChatMessage | null>(null);

  // Agent activity state (Deep Agent planning, subagent delegation, etc.)
  const [latestActivity, setLatestActivity] = useState<AgentActivity | null>(null);
  const [activityHistory, setActivityHistory] = useState<ActivityHistoryItem[]>([]);

  // Approval state
  const [approvalRequest, setApprovalRequest] = useState<WSApprovalRequestMessage | null>(null);
  const [showApprovalDialog, setShowApprovalDialog] = useState(false);
  const [approvalRemaining, setApprovalRemaining] = useState<number | null>(null);

  // Debug state for WebSocket messages
  const [debugMessages, setDebugMessages] = useState<DebugMessage[]>([]);
  const [showDebugPanel, setShowDebugPanel] = useState(false);
  const debugMessageIdRef = useRef(0);

  // Track invocation counts per subagent name
  const [subagentInvocationCounts, setSubagentInvocationCounts] = useState<Record<string, number>>({});

  // Track sequence order for streams (to ensure proper rendering order)
  const streamSequenceRef = useRef(0);
  const completionTurnRef = useRef(0);

  // Query client for cache invalidation
  const queryClient = useQueryClient();

  // Queries
  const { data: sessions, isLoading: sessionsLoading } = useChatSessions();
  const { data: messages, isLoading: messagesLoading } = useChatMessages(
    currentSessionId
  );
  const deleteSession = useDeleteSession();

  // Find current session to get its assistant ID
  const currentSession = sessions?.find((s) => s.id === currentSessionId);

  // Set assistant from session when session changes
  useEffect(() => {
    if (currentSession && !selectedAssistantId) {
      setSelectedAssistantId(currentSession.assistant_config_id);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [currentSession?.id, selectedAssistantId]);

  // Determine if currently streaming (we have streaming content, active tools, or are waiting for the first chunk)
  // Computed early so the cleanup useEffect below can reference it.
  const isStreaming: boolean =
    streamingState.main.length > 0 ||
    Array.from(streamingState.mainStreams.values()).some(ms => ms.is_active) ||
    Array.from(streamingState.subagents.values()).some(sa => sa.is_active) ||
    activeToolCalls.length > 0 ||
    isWaitingForResponse;

  // Clear streaming subagents when persisted messages are available
  // (prevents duplicate subagent bubbles after query invalidation on complete)
  // Guard: only run when NOT actively streaming, to prevent clearing new Q2
  // subagents triggered by stale Q1 persisted subagents in the messages cache.
  useEffect(() => {
    if (isStreaming) return;

    if (messages && messages.length > 0 && streamingState.subagents.size > 0) {
      const hasPersistedSubagents = messages.some(m => m.metadata?.subagent_name);
      if (hasPersistedSubagents) {
        setStreamingState(prev => ({
          ...prev,
          subagents: new Map<string, SubagentStream>(),
        }));
      }
    }
  }, [messages, streamingState.subagents.size, isStreaming]);

  // Clear optimistic user message when persisted messages arrive
  useEffect(() => {
    if (pendingUserMessage && messages) {
      const persisted = messages.some(
        (m) => m.role === "user" && m.content === pendingUserMessage.content
      );
      if (persisted) {
        setPendingUserMessage(null);
      }
    }
  }, [messages, pendingUserMessage]);

  /**
   * Processes incoming streaming tokens and routes them to the correct stream.
   *
   * Context: Called by useStreamingChat for every token/batch received from the
   * WebSocket. Maintains separate streams for main agent and subagent content,
   * handles content reset events that force new stream creation, and tracks
   * invocation IDs for multi-stream rendering.
   *
   * @param token - Text content received from the LLM
   * @param sessionId - Chat session ID for the current conversation
   * @param source - Whether the token is from the main agent or a subagent
   * @param subagentName - Display name of the subagent (when source is "subagent")
   * @param invocationId - Unique ID for the current stream segment
   */
  const handleToken = useCallback((
    token: string,
    sessionId: string,
    source: "main" | "subagent" = "main",
    subagentName?: string,
    invocationId?: string,
  ) => {
    // We've received the first token, no longer waiting
    setIsWaitingForResponse(false);

    // If a tool just finished, show the separator for this stream
    if (toolJustFinished) {
      setShowStreamSeparator(true);
      setToolJustFinished(false);
    }

    if (source === "main") {
      // Main agent tokens - use invocation_id if provided to separate streams
      if (invocationId) {
        // Treat as separate stream based on invocation_id
        setStreamingState((prev) => {
          const mainStreams = new Map(prev.mainStreams);
          const existing = mainStreams.get(invocationId);

          // If content reset occurred, force new stream creation
          if (contentResetOccurredRef.current && existing) {
            // Generate a unique suffix using monotonic counter to avoid collisions
            const uniqueId = `${invocationId}-cr${contentResetCounterRef.current++}`;
            mainStreams.set(uniqueId, {
              invocation_id: uniqueId,
              content: token,
              is_active: true,
              is_complete: false,
              started_at: Date.now(),
              sequence: streamSequenceRef.current++,
            });
            contentResetOccurredRef.current = false; // Reset flag after first token
            return { ...prev, mainStreams };
          }

          if (existing) {
            mainStreams.set(invocationId, {
              ...existing,
              content: existing.content + token,
              is_active: true,
            });
          } else {
            mainStreams.set(invocationId, {
              invocation_id: invocationId,
              content: token,
              is_active: true,
              is_complete: false,
              started_at: Date.now(),
              sequence: streamSequenceRef.current++,
            });
          }

          return { ...prev, mainStreams };
        });
      } else {
        // Fallback: group in main (backward compatibility)
        setStreamingState((prev) => ({
          ...prev,
          main: prev.main + token,
        }));
      }
    } else if (source === "subagent" && invocationId) {
      // Subagent tokens - route to correct subagent
      setStreamingState((prev) => {
        const subagents = new Map(prev.subagents);
        const existing = subagents.get(invocationId);

        if (existing) {
          // Update existing subagent stream
          subagents.set(invocationId, {
            ...existing,
            content: existing.content + token,
            is_active: true,
          });
        } else {
          // Create new subagent stream (shouldn't happen if subagent message was sent first)
          subagents.set(invocationId, {
            invocation_id: invocationId,
            subagent_name: subagentName || "Subagent",
            content: token,
            is_active: true,
            is_complete: false,
            started_at: Date.now(),
          });
        }

        return { ...prev, subagents };
      });
    }

    // Update session ID if this was a new session
    setCurrentSessionId((prev) => prev || sessionId);
  }, [toolJustFinished]);

  const handleSubagentStart = useCallback((subagent: string, invocationId: string, message?: string) => {
    // message parameter describes what the subagent is doing - currently unused but available for future use
    void message;

    // Increment invocation count for this subagent name
    setSubagentInvocationCounts((prev) => {
      const currentCount = prev[subagent] || 0;
      return {
        ...prev,
        [subagent]: currentCount + 1,
      };
    });

    setStreamingState((prev) => {
      const subagents = new Map(prev.subagents);

      // Get the current invocation number for this subagent
      const invocationNumber = (subagentInvocationCounts[subagent] || 0) + 1;

      subagents.set(invocationId, {
        invocation_id: invocationId,
        subagent_name: subagent,
        content: "",
        is_active: true,
        is_complete: false,
        started_at: Date.now(),
        invocation_number: invocationNumber,
        sequence: streamSequenceRef.current++,
      });
      return { ...prev, subagents };
    });
  }, [subagentInvocationCounts]);

  const handleSubagentComplete = useCallback((invocationId: string) => {
    setStreamingState((prev) => {
      const subagents = new Map(prev.subagents);
      const existing = subagents.get(invocationId);

      if (existing) {
        subagents.set(invocationId, {
          ...existing,
          is_active: false,
          is_complete: true,
        });
      }

      return { ...prev, subagents };
    });
  }, []);

  const handleMainAgentComplete = useCallback((invocationId: string) => {
    setStreamingState((prev) => {
      const mainStreams = new Map(prev.mainStreams);
      const existing = mainStreams.get(invocationId);

      if (existing) {
        mainStreams.set(invocationId, {
          ...existing,
          is_active: false,
          is_complete: true,
        });
      }

      return { ...prev, mainStreams };
    });
  }, []);

  /**
   * Handles content reset events by completing active main agent streams.
   *
   * Context: Called by useStreamingChat when a subagent completes and the server
   * sends a content_reset event. Sets a flag that forces the next token to create
   * a new main agent stream rather than appending to the previous one.
   *
   * @param reason - Why the content was reset (e.g., "subagent_complete")
   */
  const handleContentReset = useCallback((reason: string) => {
    // reason parameter indicates why content was reset (e.g., "subagent_complete")
    // Mark all existing main streams as complete to prepare for new stream
    void reason; // Explicitly mark as intentionally unused for now
    contentResetOccurredRef.current = true; // Set flag to force new stream creation
    setStreamingState((prev) => {
      const mainStreams = new Map(prev.mainStreams);
      for (const [id, stream] of mainStreams) {
        if (stream.is_active) {
          mainStreams.set(id, { ...stream, is_active: false, is_complete: true });
        }
      }
      return { ...prev, mainStreams };
    });
  }, []);

  /**
   * Handles session completion by invalidating query caches and resetting
   * all streaming state.
   *
   * Context: Called by useStreamingChat when the server sends a "complete" event,
   * indicating the full response has been persisted. Invalidates TanStack Query
   * caches to fetch the final messages, then clears streaming state, tool calls,
   * and activity panel to return the UI to its idle state.
   *
   * @param sessionId - The completed chat session ID
   * @param messageId - The ID of the persisted assistant message
   */
  const handleComplete = useCallback(
    (sessionId: string, messageId: string) => {
      void messageId;
      // Update session ID if this was a new session (do this first)
      setCurrentSessionId((prev) => prev || sessionId);
      setIsWaitingForResponse(false);
      setActiveToolCalls([]);
      setLatestActivity(null);
      setShowStreamSeparator(false);
      setToolJustFinished(false);
      contentResetOccurredRef.current = false;

      // Increment turn counter to guard against stale completions
      const turn = ++completionTurnRef.current;

      // Mark all streams as inactive but KEEP their content visible
      // until persisted messages arrive in the query cache
      setStreamingState((prev) => ({
        main: "",
        mainStreams: new Map(
          Array.from(prev.mainStreams.entries()).map(([id, stream]) => [
            id,
            { ...stream, is_active: false, is_complete: true },
          ])
        ),
        subagents: new Map(
          Array.from(prev.subagents.entries()).map(([id, sa]) => [
            id,
            { ...sa, is_active: false, is_complete: true },
          ])
        ),
      }));

      // Invalidate sessions (no flicker concern since sidebar is separate)
      queryClient.invalidateQueries({ queryKey: queryKeys.ai.chat.sessions() });

      // Refetch messages and clear streaming state AFTER cache is updated
      queryClient
        .refetchQueries({ queryKey: queryKeys.ai.chat.messages(sessionId) })
        .then(() => {
          // Only clear if this is still the latest completion turn
          if (completionTurnRef.current === turn) {
            setStreamingState({
              main: "",
              mainStreams: new Map<string, MainAgentStream>(),
              subagents: new Map<string, SubagentStream>(),
            });
            streamSequenceRef.current = 0;
          }
        });
    },
    [queryClient]
  );

  const handleError = useCallback((errorMsg: string) => {
    setIsWaitingForResponse(false);
    setError(`Chat error: ${errorMsg}`);
    setPendingUserMessage(null);
  }, []);

  // Debug: Capture all raw WebSocket messages
  const handleRawMessage = useCallback((data: unknown, direction: "in" | "out") => {
    setDebugMessages((prev) => {
      const newMessages = [
        ...prev,
        {
          id: debugMessageIdRef.current++,
          timestamp: Date.now(),
          direction,
          data,
        },
      ];
      // Keep only the last 500 messages to prevent memory issues
      return newMessages.length > 500 ? newMessages.slice(-500) : newMessages;
    });
  }, []);

  // Track tool execution with step counts
  const toolStepCounter = useRef<Map<string, number>>(new Map());
  const totalToolSteps = useRef<Map<string, number>>(new Map());

  // Helper function to format relative time
  const formatRelativeTime = useCallback((timestamp: number): string => {
    const now = Date.now();
    const diff = now - timestamp;

    if (diff < 1000) return "Just now";
    if (diff < 60000) return `${Math.floor(diff / 1000)}s ago`;
    if (diff < 3600000) return `${Math.floor(diff / 60000)}m ago`;
    return `${Math.floor(diff / 3600000)}h ago`;
  }, []);

  // Helper function to add current activity to history before updating
  const addToActivityHistory = useCallback((activity: AgentActivity) => {
    setActivityHistory((prev) => {
      // Don't add if it's the same as the current activity
      if (prev.length > 0 && prev[0].activity.timestamp === activity.timestamp) {
        return prev;
      }
      // Create history item with relative time
      const historyItem: ActivityHistoryItem = {
        activity,
        displayTime: formatRelativeTime(activity.timestamp),
      };
      // Keep only the last 10 activities
      return [historyItem, ...prev].slice(0, 10);
    });
  }, [formatRelativeTime]);

  const handleApprovalRequest = useCallback((request: WSApprovalRequestMessage) => {
    // Show approval dialog and reset countdown
    setApprovalRequest(request);
    setShowApprovalDialog(true);
    setApprovalRemaining(null); // Will be set by first heartbeat
  }, []);

  const handleApprovalCountdown = useCallback((remaining: number) => {
    setApprovalRemaining(remaining);
  }, []);

  const handleApprovalTimeout = useCallback(() => {
    setApprovalRemaining(0);
    // Auto-dismiss after a brief delay so the user sees "Expired"
    setTimeout(() => {
      setShowApprovalDialog(false);
      setApprovalRequest(null);
      setApprovalRemaining(null);
    }, 1500);
  }, []);

  // Deep Agent activity handlers
  const handleThinking = useCallback(() => {
    // Only set thinking if we don't have recent activity
    if (latestActivity && Date.now() - latestActivity.timestamp < 2000) {
      return;
    }
    // Add current activity to history before updating
    if (latestActivity) {
      addToActivityHistory(latestActivity);
    }
    setLatestActivity({
      type: "thinking",
      timestamp: Date.now(),
    });
  }, [latestActivity, addToActivityHistory]);

  /**
   * Handles tool call events by marking active streams as complete and updating
   * the agent activity panel.
   *
   * Context: Called by useStreamingChat when the AI agent invokes a tool.
   * Completes any active main agent streams so that content before the tool call
   * appears in its own bubble, then adds the tool to the active calls list for
   * the activity panel display.
   *
   * @param tool - Name of the tool being invoked
   * @param args - Arguments passed to the tool
   */
  const handleToolCall = useCallback((tool: string, args: Record<string, unknown>) => {
    // Mark current main agent streams as complete when a tool is called
    // This ensures main agent content before the tool appears in its own bubble
    setStreamingState((prev) => {
      const mainStreams = new Map(prev.mainStreams);
      for (const [id, stream] of mainStreams) {
        if (stream.is_active) {
          mainStreams.set(id, { ...stream, is_active: false, is_complete: true });
        }
      }
      return { ...prev, mainStreams };
    });

    // Track tool execution steps
    toolStepCounter.current.set(tool, (toolStepCounter.current.get(tool) || 0) + 1);
    const currentStep = toolStepCounter.current.get(tool)!;
    const totalSteps = totalToolSteps.current.get(tool) || currentStep;
    totalToolSteps.current.set(tool, Math.max(totalSteps, currentStep));

    // Add tool to active calls
    setActiveToolCalls((prev) => [...prev, { name: tool, args }]);

    // Add current activity to history before updating
    if (latestActivity && latestActivity.toolName !== tool) {
      addToActivityHistory(latestActivity);
    }

    // Update latest activity
    setLatestActivity({
      type: "executing",
      toolName: tool,
      timestamp: Date.now(),
    });
  }, [latestActivity, addToActivityHistory]);

  const handleToolResult = useCallback((tool: string) => {
    // Remove tool from active calls
    setActiveToolCalls((prev) =>
      prev.filter((t) => t.name !== tool)
    );

    // Clear the step counter for this tool when it completes
    toolStepCounter.current.delete(tool);
    totalToolSteps.current.delete(tool);

    // Clear latest activity if it was for this tool
    if (latestActivity?.type === "executing" && latestActivity.toolName === tool) {
      setLatestActivity(null);
    }

    // Set flag to add separator before next text stream
    setToolJustFinished(true);
  }, [latestActivity]);

  // Streaming chat hook
  const streamingChat = useStreamingChat({
    sessionId: currentSessionId,
    assistantId: selectedAssistantId ?? "",
    projectId,
    onToken: handleToken,
    onComplete: handleComplete,
    onError: handleError,
    onToolCall: handleToolCall,
    onToolResult: handleToolResult,
    onApprovalRequest: handleApprovalRequest,
    onApprovalCountdown: handleApprovalCountdown,
    onApprovalTimeout: handleApprovalTimeout,
    onThinking: handleThinking,
    onSubagentStart: handleSubagentStart,
    onSubagentComplete: handleSubagentComplete,
    onMainAgentComplete: handleMainAgentComplete,
    onContentReset: handleContentReset,
    onRawMessage: handleRawMessage,
  });

  // Execution mode hook for managing AI tool risk level
  const { executionMode, setExecutionMode } = useExecutionMode();

  // Handle new chat
  const handleNewChat = useCallback(() => {
    setCurrentSessionId(undefined);
    setSelectedAssistantId(undefined);
    setSidebarOpen(false);
    setError(null);
    setPendingUserMessage(null);
  }, []);

  // Handle session selection
  const handleSessionSelect = useCallback(
    (sessionId: string) => {
      setCurrentSessionId(sessionId);
      setSidebarOpen(false);
      setError(null);
    },
    []
  );

  // Handle session deletion
  const handleDeleteSession = useCallback(
    (sessionId: string) => {
      deleteSession.mutate(sessionId, {
        onSuccess: () => {
          if (currentSessionId === sessionId) {
            handleNewChat();
          }
        },
      });
    },
    [currentSessionId, handleNewChat, deleteSession]
  );

  // Handle sending a message
  const handleSendMessage = useCallback(
    (messageContent: string) => {
      setError(null);

      if (!selectedAssistantId) {
        setError("Please select an AI assistant first.");
        return;
      }

      // Optimistically display user message before WebSocket roundtrip
      setPendingUserMessage({
        id: `pending-${Date.now()}`,
        role: "user",
        content: messageContent,
        createdAt: new Date().toISOString(),
      });

      // Clear any previous streaming state
      setStreamingState({
        main: "",
        mainStreams: new Map<string, MainAgentStream>(),
        subagents: new Map<string, SubagentStream>(),
      });
      setActiveToolCalls([]);
      setLatestActivity(null);
      setIsWaitingForResponse(true);
      setShowStreamSeparator(false);
      setToolJustFinished(false);
      contentResetOccurredRef.current = false;
      streamSequenceRef.current = 0; // Reset sequence counter for new message
      completionTurnRef.current = 0;
      setSubagentInvocationCounts({});

      // Only send if the WebSocket is connected
      if (streamingChat.connectionState !== WSConnectionState.OPEN) {
        setError("Not connected to chat service. Please wait for connection.");
        return;
      }

      // Generate title for new sessions (when no current session exists)
      const title = currentSessionId ? undefined : generateSessionTitle(messageContent);

      // Send message via streaming hook with execution mode
      streamingChat.sendMessage(messageContent, title ?? undefined, executionMode);
    },
    [selectedAssistantId, streamingChat, currentSessionId, executionMode]
  );

  // Handle canceling the current stream
  const handleCancel = useCallback(() => {
    streamingChat.cancel();
    setStreamingState({
      main: "",
      mainStreams: new Map<string, MainAgentStream>(),
      subagents: new Map<string, SubagentStream>(),
    });
    setActiveToolCalls([]);
    setLatestActivity(null);
    setIsWaitingForResponse(false);
    setShowStreamSeparator(false);
    setToolJustFinished(false);
    contentResetOccurredRef.current = false;
    streamSequenceRef.current = 0; // Reset sequence counter on cancel
    setPendingUserMessage(null);
  }, [streamingChat]);

  // Handle approval decision
  const handleApproval = useCallback((approved: boolean) => {
    if (!approvalRequest) {
      return;
    }

    // Send approval response
    streamingChat.sendApprovalResponse(approvalRequest.approval_id, approved);

    // Close dialog and clear state
    setShowApprovalDialog(false);
    setApprovalRequest(null);
    setApprovalRemaining(null);
  }, [approvalRequest, streamingChat]);

  const handleApprove = useCallback(() => {
    handleApproval(true);
  }, [handleApproval]);

  const handleReject = useCallback(() => {
    handleApproval(false);
  }, [handleApproval]);

  const handleApprovalCancel = useCallback(() => {
    setShowApprovalDialog(false);
    setApprovalRequest(null);
    setApprovalRemaining(null);
  }, []);

  // Handle clearing debug messages
  const handleClearDebugMessages = useCallback(() => {
    setDebugMessages([]);
  }, []);

  // Helper: Convert API messages to ChatMessage type
  const chatMessages: ChatMessage[] = useMemo(() => {
    const base: ChatMessage[] =
      messages?.map((msg) => ({
        id: msg.id,
        role: msg.role,
        content: msg.content,
        toolCalls: msg.tool_calls,
        toolResults: msg.tool_results,
        createdAt: msg.created_at,
        metadata: msg.metadata,
      })) ?? [];

    if (pendingUserMessage) {
      const alreadyExists = base.some(
        (m) => m.role === "user" && m.content === pendingUserMessage.content
      );
      if (!alreadyExists) {
        base.push(pendingUserMessage);
      }
    }

    return base;
  }, [messages, pendingUserMessage]);

  const { token } = theme.useToken();
  const { spacing, typography } = useThemeTokens();

  // Mobile menu items for the overflow menu
  const mobileMenuItems = useMemo(() => {
    const items = [
      {
        key: "new-chat",
        label: "New Chat",
        icon: <PlusOutlined />,
        disabled: !currentSessionId,
      },
    ];

    if (currentSessionId) {
      items.push({
        key: "divider",
        type: "divider" as const,
      });
    }

    return items;
  }, [currentSessionId]);

  const handleMobileMenuClick = useCallback(({ key }: { key: string }) => {
    switch (key) {
      case "new-chat":
        handleNewChat();
        break;
    }
  }, [handleNewChat]);

  return (
    <>
      <style>
        {`
          .chat-mobile-header {
            backdrop-filter: blur(8px);
            background: ${isMobile ? token.colorBgContainer : "transparent"};
          }
        `}
      </style>

      <Layout
        style={{
          height: isMobile ? "100dvh" : "calc(100vh - 300px)",
          minHeight: isMobile ? "100dvh" : 400,
          background: token.colorBgLayout,
        }}
      >
        {/* Desktop Sidebar */}
        <Sider
          width={280}
          collapsible
          collapsed={isCollapsed}
          onCollapse={setIsCollapsed}
          breakpoint="lg"
          collapsedWidth="0"
          trigger={null}
          style={{
            display: isMobile ? "none" : "block",
            backgroundColor: token.colorBgContainer,
            borderRight: `1px solid ${token.colorBorderSecondary}`,
          }}
        >
          {!isCollapsed && (
            <SessionList
              sessions={sessions ?? []}
              currentSessionId={currentSessionId}
              onSessionSelect={handleSessionSelect}
              onNewChat={handleNewChat}
              onDeleteSession={handleDeleteSession}
              loading={sessionsLoading}
              hideNewChatButton
            />
          )}
        </Sider>

        {/* Mobile Sidebar Drawer */}
        <Drawer
          title="Conversations"
          placement="left"
          open={isSidebarOpen}
          onClose={() => setSidebarOpen(false)}
          width={isSmallMobile ? "85%" : 280}
          styles={{ body: { padding: 0 } }}
        >
          <SessionList
            sessions={sessions ?? []}
            currentSessionId={currentSessionId}
            onSessionSelect={handleSessionSelect}
            onNewChat={handleNewChat}
            onDeleteSession={handleDeleteSession}
            loading={sessionsLoading}
            hideNewChatButton
          />
        </Drawer>

        {/* Main Chat Area */}
        <Layout>
          {/* Header - Mobile Optimized */}
          <Header
            className="chat-mobile-header"
            style={{
              padding: isMobile ? `${spacing.sm}px ${spacing.md}px` : `0 ${spacing.md}px`,
              backgroundColor: token.colorBgContainer,
              borderBottom: `1px solid ${token.colorBorderSecondary}`,
              display: "flex",
              alignItems: "center",
              gap: isMobile ? spacing.sm : spacing.md,
              height: isMobile ? 56 : "auto",
              lineHeight: isMobile ? "56px" : "auto",
              position: "relative",
              zIndex: 10,
            }}
          >
            {/* Mobile menu button - larger touch target */}
            {isMobile && (
              <Button
                type="text"
                icon={<MenuOutlined style={{ fontSize: 20 }} />}
                onClick={() => setSidebarOpen(true)}
                style={{
                  minWidth: 44,
                  height: 44,
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                }}
                aria-label="Open conversations"
              />
            )}

            {/* Desktop sidebar toggle button - visible when collapsed or to collapse */}
            {!isMobile && (
              <Button
                type="text"
                icon={
                  isCollapsed ? (
                    <MenuOutlined style={{ fontSize: 18 }} />
                  ) : (
                    <CloseOutlined style={{ fontSize: 16 }} />
                  )
                }
                onClick={() => setIsCollapsed(!isCollapsed)}
                style={{
                  minWidth: 40,
                  height: 40,
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  ...(isCollapsed && {
                    background: token.colorFillAlter,
                  }),
                }}
                aria-label={isCollapsed ? "Open sidebar" : "Close sidebar"}
                title={isCollapsed ? "Open conversations" : "Close conversations"}
              />
            )}

            {/* Brand - compact on mobile */}
            <div
              style={{
                display: "flex",
                alignItems: "center",
                gap: isMobile ? spacing.xs : spacing.sm,
              }}
            >
              <RobotOutlined
                style={{
                  fontSize: isMobile ? typography.sizes.md : typography.sizes.lg,
                  color: token.colorPrimary,
                }}
              />
              {!isSmallMobile && (
                <span
                  style={{
                    fontWeight: typography.weights.semiBold,
                    fontSize: isMobile ? typography.sizes.md : typography.sizes.md,
                  }}
                >
                  
                </span>
              )}
            </div>

            <div style={{ flex: 1 }} />

            {/* Right-aligned section: New Chat button and Assistant selector */}
            <div
              style={{
                display: "flex",
                alignItems: "center",
                gap: spacing.md,
              }}
            >
              {/* Assistant Selector - shown on desktop */}
              {!isMobile && (
                <div style={{ minWidth: 200, maxWidth: 400 }}>
                  <AssistantSelector
                    value={selectedAssistantId}
                    onChange={setSelectedAssistantId}
                    disabled={!!currentSessionId}
                    locked={!!currentSessionId}
                    bordered={false}
                  />
                </div>
              )}

                {/* New Chat button - shown when in active session */}
              {currentSessionId && (
                <Tooltip title="Start a new conversation">
                  <Button
                    type="text"
                    icon={<PlusOutlined style={{ fontSize: isMobile ? 18 : 16 }} />}
                    onClick={handleNewChat}
                    style={{
                      minWidth: isMobile ? 44 : 40,
                      height: isMobile ? 44 : 40,
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                    }}
                    aria-label="New chat"
                  />
                </Tooltip>
              )}

              {/* Debug Panel toggle button */}
              <Tooltip title="WebSocket Debug Panel">
                <Button
                  type="text"
                  icon={<BugOutlined style={{ fontSize: isMobile ? 18 : 16 }} />}
                  onClick={() => setShowDebugPanel(!showDebugPanel)}
                  style={{
                    minWidth: isMobile ? 44 : 40,
                    height: isMobile ? 44 : 40,
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    color: showDebugPanel ? token.colorPrimary : undefined,
                  }}
                  aria-label="Toggle debug panel"
                />
              </Tooltip>
            </div>

            {/* Mobile: Assistant selector when no session */}
            {isMobile && !currentSessionId && (
              <div style={{ flex: 1, maxWidth: 180 }}>
                <AssistantSelector
                  value={selectedAssistantId}
                  onChange={setSelectedAssistantId}
                  disabled={false}
                  locked={false}
                  bordered={false}
                />
              </div>
            )}

            {/* Mobile: Overflow menu */}
            {isMobile && (
              <Dropdown
                menu={{ items: mobileMenuItems, onClick: handleMobileMenuClick }}
                trigger={["click"]}
                placement="bottomRight"
              >
                <Button
                  type="text"
                  icon={<MoreOutlined style={{ fontSize: 18 }} />}
                  style={{
                    minWidth: 44,
                    height: 44,
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                  }}
                  aria-label="More options"
                />
              </Dropdown>
            )}
          </Header>

          {/* Content Area */}
          <Content
            style={{
              display: "flex",
              flexDirection: "column",
              flex: 1,
              overflow: "hidden",
              backgroundColor: token.colorBgContainer,
            }}
          >
            {/* Error Alert - mobile optimized */}
            {error && (
              <Alert
                type="error"
                message={isSmallMobile ? "Error" : error}
                description={isSmallMobile ? error : undefined}
                closable
                onClose={() => setError(null)}
                style={{
                  margin: isMobile ? spacing.sm : spacing.md,
                  borderRadius: isMobile ? 8 : token.borderRadius,
                }}
                showIcon
              />
            )}

            {/* Messages - with safe area for mobile */}
            <div
              style={{
                flex: 1,
                overflow: "auto",
                backgroundColor: token.colorBgLayout,
                // Add padding for safe area on mobile devices
                paddingBottom: isMobile ? "env(safe-area-inset-bottom)" : 0,
              }}
            >
              <MessageList
                messages={chatMessages}
                loading={messagesLoading}
                streamingState={streamingState}
                isStreaming={isStreaming}
                activeToolCalls={activeToolCalls}
                showSeparator={showStreamSeparator}
                isMobile={isMobile}
              />
            </div>

            {/* Agent Activity Panel - between messages and input */}
            <AgentActivityPanel activity={latestActivity} activityHistory={activityHistory} />

            {/* Input - fixed at bottom for mobile feel */}
            <MessageInput
              onSend={handleSendMessage}
              disabled={!selectedAssistantId}
              loading={messagesLoading}
              isStreaming={isStreaming}
              onCancel={handleCancel}
              connectionState={streamingChat.connectionState}
              executionMode={executionMode}
              onExecutionModeChange={setExecutionMode}
              placeholder={
                !selectedAssistantId
                  ? isSmallMobile
                    ? "Select an assistant"
                    : "Select an assistant to start chatting"
                  : "Type your message..."
              }
            />

            {/* WebSocket Debug Panel - inline below input */}
            <WebSocketDebugPanel
              visible={showDebugPanel}
              onClose={() => setShowDebugPanel(false)}
              messages={debugMessages}
              onClear={handleClearDebugMessages}
            />
          </Content>
        </Layout>
      </Layout>

      {/* Approval Dialog for critical tools */}
      <ApprovalDialog
        open={showApprovalDialog}
        approvalRequest={approvalRequest}
        remainingSeconds={approvalRemaining}
        onApprove={handleApprove}
        onReject={handleReject}
        onCancel={handleApprovalCancel}
      />
    </>
  );
};
