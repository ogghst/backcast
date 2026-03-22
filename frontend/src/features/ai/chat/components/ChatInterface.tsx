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

import { useState, useCallback, useEffect, useMemo } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { queryKeys } from "@/api/queryKeys";
import { Layout, Alert, Drawer, Button, Typography, theme, Space, Tooltip, Grid, Dropdown, Select } from "antd";
import {
  MenuOutlined,
  RobotOutlined,
  PlusOutlined,
  MoreOutlined,
  SafetyOutlined,
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
import type { ChatMessage } from "../../types";
import { WSConnectionState, type WSApprovalRequestMessage } from "../types";
import { useThemeTokens } from "@/hooks/useThemeTokens";
import { generateSessionTitle } from "../utils/sessionTitle";
import { useExecutionMode } from "../../hooks/useExecutionMode";
import { ModeBadge } from "../../components/ModeBadge";
import { ApprovalDialog } from "../../components/ApprovalDialog";

const { Sider, Content, Header } = Layout;
const { Text } = Typography;
const { useBreakpoint } = Grid;

interface ChatInterfaceProps {
  // URL params can be passed in for direct linking
  sessionId?: string;
  assistantId?: string;
  // Optional project ID to scope chat to a specific project
  projectId?: string;
}

// Connection dot component - subtle status indicator
const ConnectionDot = ({ state, size = 8 }: { state: WSConnectionState; size?: number }) => {
  const colorMap = {
    [WSConnectionState.OPEN]: "#52c41a",
    [WSConnectionState.CONNECTING]: "#faad14",
    [WSConnectionState.CLOSING]: "#faad14",
    [WSConnectionState.CLOSED]: "#8c8c8c",
    [WSConnectionState.ERROR]: "#ff4d4f",
  };

  return (
    <div
      style={{
        width: size,
        height: size,
        borderRadius: "50%",
        backgroundColor: colorMap[state] || colorMap[WSConnectionState.CLOSED],
        transition: "background-color 0.3s ease",
        ...(state === WSConnectionState.CONNECTING && {
          animation: "pulse 1.5s ease-in-out infinite",
        }),
      }}
    />
  );
};

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

  // Approval state
  const [approvalRequest, setApprovalRequest] = useState<WSApprovalRequestMessage | null>(null);
  const [showApprovalDialog, setShowApprovalDialog] = useState(false);

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
  const handleToken = useCallback((token: string, sessionId: string) => {
    // We've received the first token, no longer waiting
    setIsWaitingForResponse(false);
    // Append token to streaming content
    setStreamingContent((prev) => prev + token);
    // Update session ID if this was a new session
    setCurrentSessionId((prev) => prev || sessionId);
  }, []);

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
    },
    [queryClient]
  );

  const handleError = useCallback((errorMsg: string) => {
    setIsWaitingForResponse(false);
    setError(`Chat error: ${errorMsg}`);
  }, []);

  const handleToolCall = useCallback((tool: string, args: Record<string, unknown>) => {
    // Add tool to active calls
    setActiveToolCalls((prev) => [...prev, { name: tool, args }]);
  }, []);

  const handleToolResult = useCallback((tool: string) => {
    // Remove tool from active calls
    setActiveToolCalls((prev) =>
      prev.filter((t) => t.name !== tool)
    );
  }, []);

  const handleApprovalRequest = useCallback((request: WSApprovalRequestMessage) => {
    // Show approval dialog
    setApprovalRequest(request);
    setShowApprovalDialog(true);
  }, []);

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
      setIsWaitingForResponse(true);

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
    setIsWaitingForResponse(false);
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

  const connectionStatus = getConnectionStatus();
  const { token } = theme.useToken();
  const { spacing, typography } = useThemeTokens();

  // Mobile menu items for the overflow menu
  const mobileMenuItems = useMemo(() => {
    const items = [
      {
        key: "assistant",
        label: selectedAssistantId ? "Change Assistant" : "Select Assistant",
        icon: <RobotOutlined />,
        disabled: !!currentSessionId,
      },
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
  }, [currentSessionId, selectedAssistantId]);

  const handleMobileMenuClick = useCallback(({ key }: { key: string }) => {
    switch (key) {
      case "new-chat":
        handleNewChat();
        break;
      case "assistant":
        // On mobile, assistant selector is shown in the header area
        // This could open a modal or bottom sheet in a future enhancement
        break;
    }
  }, [handleNewChat]);

  return (
    <>
      <style>
        {`
          @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.5; }
          }

          .chat-mobile-header {
            backdrop-filter: blur(8px);
            background: ${isMobile ? token.colorBgContainer : "transparent"};
          }

          .chat-connection-dot {
            box-shadow: 0 0 8px ${streamingChat.connectionState === WSConnectionState.OPEN
              ? "rgba(82, 196, 26, 0.4)"
              : "transparent"};
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
                  AI Chat
                </span>
              )}
            </div>

            <div style={{ flex: 1 }} />

            {/* Connection Status - subtle dot on mobile, full on desktop */}
            <div
              className="chat-connection-dot"
              style={{
                display: "flex",
                alignItems: "center",
                gap: spacing.xs,
                marginRight: isMobile ? spacing.sm : spacing.md,
              }}
              aria-label={`Connection: ${connectionStatus.text}`}
            >
              <ConnectionDot state={streamingChat.connectionState} size={isMobile ? 8 : 10} />
              {!isMobile && (
                <Text
                  type="secondary"
                  style={{
                    fontSize: typography.sizes.xs,
                    fontFamily: '"JetBrains Mono", monospace',
                    textTransform: "uppercase",
                    letterSpacing: "0.5px",
                  }}
                >
                  {connectionStatus.text}
                </Text>
              )}
            </div>

            {/* Execution Mode Selector - shown on both desktop and mobile */}
            <Tooltip title={`AI tool execution mode: ${executionMode}`}>
              <div
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: spacing.xs,
                  marginRight: isMobile ? spacing.sm : spacing.md,
                }}
              >
                {!isMobile && (
                  <SafetyOutlined
                    style={{
                      fontSize: typography.sizes.sm,
                      color: token.colorTextSecondary,
                    }}
                  />
                )}
                <Select
                  value={executionMode}
                  onChange={setExecutionMode}
                  style={{
                    minWidth: isMobile ? 80 : 120,
                    fontSize: isMobile ? typography.sizes.xs : typography.sizes.sm,
                  }}
                  size={isMobile ? "small" : "middle"}
                  options={[
                    {
                      value: "safe",
                      label: (
                        <div style={{ display: "flex", alignItems: "center", gap: 4 }}>
                          <ModeBadge mode="safe" />
                          {!isMobile && <span style={{ fontSize: "11px" }}>Low risk only</span>}
                        </div>
                      ),
                    },
                    {
                      value: "standard",
                      label: (
                        <div style={{ display: "flex", alignItems: "center", gap: 4 }}>
                          <ModeBadge mode="standard" />
                          {!isMobile && <span style={{ fontSize: "11px" }}>Approval needed</span>}
                        </div>
                      ),
                    },
                    {
                      value: "expert",
                      label: (
                        <div style={{ display: "flex", alignItems: "center", gap: 4 }}>
                          <ModeBadge mode="expert" />
                          {!isMobile && <span style={{ fontSize: "11px" }}>All tools</span>}
                        </div>
                      ),
                    },
                  ]}
                  aria-label="Select execution mode"
                />
              </div>
            </Tooltip>

            {/* Desktop: Assistant Selector + New Chat */}
            {!isMobile && (
              <Space size="small">
                <div style={{ minWidth: 200, maxWidth: 400 }}>
                  <AssistantSelector
                    value={selectedAssistantId}
                    onChange={setSelectedAssistantId}
                    disabled={!!currentSessionId}
                    locked={!!currentSessionId}
                  />
                </div>
                {currentSessionId && (
                  <Tooltip title="Start a new conversation with a different assistant">
                    <Button
                      type="text"
                      icon={<PlusOutlined />}
                      onClick={handleNewChat}
                      style={{
                        display: "flex",
                        alignItems: "center",
                        gap: spacing.xs,
                      }}
                    >
                      <span style={{ fontSize: typography.sizes.sm }}>New Chat</span>
                    </Button>
                  </Tooltip>
                )}
              </Space>
            )}

            {/* Mobile: Overflow menu */}
            {isMobile && (
              <>
                {/* Inline assistant selector when no session */}
                {!currentSessionId && (
                  <div style={{ flex: 1, maxWidth: 180 }}>
                    <AssistantSelector
                      value={selectedAssistantId}
                      onChange={setSelectedAssistantId}
                      disabled={false}
                      locked={false}
                    />
                  </div>
                )}

                {/* New Chat button when in active session */}
                {currentSessionId && (
                  <Button
                    type="text"
                    icon={<PlusOutlined style={{ fontSize: 18 }} />}
                    onClick={handleNewChat}
                    style={{
                      minWidth: 44,
                      height: 44,
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                    }}
                    aria-label="New chat"
                  />
                )}

                {/* Overflow menu for additional options */}
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
              </>
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
              />
            </div>

            {/* Input - fixed at bottom for mobile feel */}
            <MessageInput
              onSend={handleSendMessage}
              disabled={!selectedAssistantId}
              loading={messagesLoading}
              isStreaming={isStreaming}
              onCancel={handleCancel}
              placeholder={
                !selectedAssistantId
                  ? isSmallMobile
                    ? "Select an assistant"
                    : "Select an assistant to start chatting"
                  : "Type your message..."
              }
            />
          </Content>
        </Layout>
      </Layout>

      {/* Approval Dialog for critical tools */}
      <ApprovalDialog
        open={showApprovalDialog}
        approvalRequest={approvalRequest}
        onApprove={handleApprove}
        onReject={handleReject}
        onCancel={handleApprovalCancel}
      />
    </>
  );
};

// Helper function for connection status
function getConnectionStatus() {
  return {
    color: "success" as const,
    text: "Connected",
  };
}
