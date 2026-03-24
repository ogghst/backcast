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
import type { ChatMessage } from "../../types";
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
  const [streamingContent, setStreamingContent] = useState("");
  const [isWaitingForResponse, setIsWaitingForResponse] = useState(false);
  const [activeToolCalls, setActiveToolCalls] = useState<
    Array<{ name: string; args: Record<string, unknown> }>
  >([]);
  const [toolJustFinished, setToolJustFinished] = useState(false);
  const [showStreamSeparator, setShowStreamSeparator] = useState(false);

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

  // Callbacks for streaming chat (defined outside the conditional to avoid hooks rule violation)
  const handleToken = useCallback((
    token: string,
    sessionId: string,
    // eslint-disable-next-line @typescript-eslint/no-unused-vars
    source: "main" | "subagent" = "main",
    // eslint-disable-next-line @typescript-eslint/no-unused-vars
    subagentName?: string,
  ) => {
    // We've received the first token, no longer waiting
    setIsWaitingForResponse(false);

    // All tokens (main and subagent) go to main chat content
    // Subagent tokens are no longer routed to activity panel

    // If a tool just finished, show the separator for this stream
    if (toolJustFinished) {
      setShowStreamSeparator(true);
      setToolJustFinished(false);
    }

    // Append token to streaming content
    setStreamingContent((prev) => prev + token);
    // Update session ID if this was a new session
    setCurrentSessionId((prev) => prev || sessionId);
  }, [toolJustFinished]);

  const handleComplete = useCallback(
    (sessionId: string, messageId: string) => {
      // messageId is available for future use (e.g., for highlighting the completed message)
      void messageId; // Explicitly mark as intentionally unused for now
      // Update session ID if this was a new session (do this first)
      setCurrentSessionId((prev) => prev || sessionId);
      // Invalidate the queries so the completed message is fetched
      queryClient.invalidateQueries({ queryKey: queryKeys.ai.chat.messages(sessionId) });
      queryClient.invalidateQueries({ queryKey: queryKeys.ai.chat.sessions() });
      // Clear streaming state — the query refetch will populate messages
      setIsWaitingForResponse(false);
      setStreamingContent("");
      setActiveToolCalls([]);
      // Always clear activity on complete - panel MUST close reliably
      setLatestActivity(null);
      setShowStreamSeparator(false); // Reset separator state
      setToolJustFinished(false); // Reset tool finished state
    },
    [queryClient]
  );

  const handleError = useCallback((errorMsg: string) => {
    setIsWaitingForResponse(false);
    setError(`Chat error: ${errorMsg}`);
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

  const handleToolCall = useCallback((tool: string, args: Record<string, unknown>) => {
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

      // Clear any previous streaming state
      setStreamingContent("");
      setActiveToolCalls([]);
      setLatestActivity(null);
      setIsWaitingForResponse(true);
      setShowStreamSeparator(false);
      setToolJustFinished(false);

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
    setStreamingContent("");
    setActiveToolCalls([]);
    setLatestActivity(null);
    setIsWaitingForResponse(false);
    setShowStreamSeparator(false);
    setToolJustFinished(false);
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
  const chatMessages: ChatMessage[] =
    messages?.map((msg) => ({
      id: msg.id,
      role: msg.role,
      content: msg.content,
      toolCalls: msg.tool_calls,
      toolResults: msg.tool_results,
      createdAt: msg.created_at,
    })) ?? [];

  // Determine if currently streaming (we have streaming content, active tools, or are waiting for the first chunk)
  const isStreaming: boolean =
    streamingContent.length > 0 || activeToolCalls.length > 0 || isWaitingForResponse;

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
                streamingContent={streamingContent}
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
