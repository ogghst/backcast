/**
 * ChatInterface Component
 *
 * Main container for the AI chat interface.
 * Orchestrates session management, message display, and chat operations.
 * Uses WebSocket streaming for real-time AI responses.
 */

import { useState, useCallback, useEffect } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { queryKeys } from "@/api/queryKeys";
import { Layout, Alert, Drawer, Button, Badge, Typography, theme, Space, Tooltip } from "antd";
import {
  MenuOutlined,
  RobotOutlined,
  WifiOutlined,
  LoadingOutlined,
  PlusOutlined,
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
import { WSConnectionState } from "../types";
import { useThemeTokens } from "@/hooks/useThemeTokens";
import { generateSessionTitle } from "../utils/sessionTitle";

const { Sider, Content, Header } = Layout;
const { Text } = Typography;

interface ChatInterfaceProps {
  // URL params can be passed in for direct linking
  sessionId?: string;
  assistantId?: string;
}

export const ChatInterface = ({
  sessionId: initialSessionId,
  assistantId: initialAssistantId,
}: ChatInterfaceProps) => {
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

  // Streaming chat hook
  const streamingChat = useStreamingChat({
    sessionId: currentSessionId,
    assistantId: selectedAssistantId ?? "",
    onToken: handleToken,
    onComplete: handleComplete,
    onError: handleError,
    onToolCall: handleToolCall,
    onToolResult: handleToolResult,
  });

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

      // Send message via streaming hook
      streamingChat.sendMessage(messageContent, title ?? undefined);
    },
    [selectedAssistantId, streamingChat, currentSessionId]
  );

  // Handle canceling the current stream
  const handleCancel = useCallback(() => {
    streamingChat.cancel();
    setStreamingContent("");
    setActiveToolCalls([]);
    setIsWaitingForResponse(false);
  }, [streamingChat]);

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

  // Connection status indicator
  const getConnectionStatus = useCallback(() => {
    switch (streamingChat.connectionState) {
      case WSConnectionState.OPEN:
        return { color: "success" as const, text: "Connected", icon: <WifiOutlined /> };
      case WSConnectionState.CONNECTING:
        return { color: "processing" as const, text: "Connecting...", icon: <LoadingOutlined spin /> };
      case WSConnectionState.CLOSING:
        return { color: "warning" as const, text: "Closing...", icon: <LoadingOutlined spin /> };
      case WSConnectionState.CLOSED:
        return { color: "default" as const, text: "Disconnected", icon: <WifiOutlined /> };
      case WSConnectionState.ERROR:
        return { color: "error" as const, text: "Connection Error", icon: <WifiOutlined /> };
      default:
        return { color: "default" as const, text: "Unknown", icon: <WifiOutlined /> };
    }
  }, [streamingChat.connectionState]);

  const connectionStatus = getConnectionStatus();
  const { token } = theme.useToken();
  const { spacing, typography } = useThemeTokens();

  return (
    <Layout style={{ height: "calc(100vh - 300px)", minHeight: 400 }}>
      {/* Desktop Sidebar */}
      <Sider
        width={280}
        collapsible
        collapsed={isCollapsed}
        onCollapse={setIsCollapsed}
        breakpoint="lg"
        collapsedWidth="0"
        style={{
          display: window.innerWidth >= 768 ? "block" : "none",
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
        width={280}
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
        <Header
          style={{
            padding: `0 ${spacing.md}px`,
            backgroundColor: token.colorBgContainer,
            borderBottom: `1px solid ${token.colorBorderSecondary}`,
            display: "flex",
            alignItems: "center",
            gap: spacing.sm,
          }}
        >
          {/* Mobile menu button */}
          <Button
            type="text"
            icon={<MenuOutlined />}
            onClick={() => setSidebarOpen(true)}
            style={{ display: window.innerWidth < 768 ? "block" : "none" }}
          />

          <RobotOutlined style={{ fontSize: typography.sizes.lg, color: token.colorPrimary }} />
          <span style={{ fontWeight: typography.weights.semiBold }}>AI Chat</span>

          <div style={{ flex: 1 }} />

          {/* Connection Status Indicator */}
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: spacing.xs,
              marginRight: spacing.md,
            }}
          >
            {connectionStatus.icon}
            <Badge
              status={connectionStatus.color}
              text={
                <Text type="secondary" style={{ fontSize: typography.sizes.sm }}>
                  {connectionStatus.text}
                </Text>
              }
            />
          </div>

          {/* Assistant Selector with New Chat button */}
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
        </Header>

        <Content
          style={{
            display: "flex",
            flexDirection: "column",
            flex: 1,
            overflow: "hidden",
            backgroundColor: token.colorBgContainer,
          }}
        >
          {/* Error Alert */}
          {error && (
            <Alert
              type="error"
              message={error}
              closable
              onClose={() => setError(null)}
              style={{ margin: spacing.md }}
            />
          )}

          {/* Messages */}
          <div
            style={{
              flex: 1,
              overflow: "auto",
              backgroundColor: token.colorBgLayout,
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

          {/* Input */}
          <MessageInput
            onSend={handleSendMessage}
            disabled={!selectedAssistantId}
            loading={messagesLoading}
            isStreaming={isStreaming}
            onCancel={handleCancel}
            placeholder={
              !selectedAssistantId
                ? "Select an assistant to start chatting"
                : "Type your message..."
            }
          />
        </Content>
      </Layout>
    </Layout>
  );
};
