/**
 * MessageList Component
 *
 * Displays chat messages with auto-scroll to latest message.
 * Supports user, assistant, and tool message types.
 * Supports progressive rendering for streaming responses.
 */

import { useEffect, useRef, useMemo } from "react";
import { List, Empty, Typography, Spin, theme } from "antd";
import type { Theme } from "antd/es/config-provider/context";
import {
  UserOutlined,
  RobotOutlined,
  LoadingOutlined,
} from "@ant-design/icons";
import type { ChatMessage, SubagentStream, StreamingState } from "../../types";
import { useThemeTokens } from "@/hooks/useThemeTokens";
import { MarkdownRenderer } from "./MarkdownRenderer";

const { Text } = Typography;

/**
 * Props for the MessageList component
 */
interface MessageListProps {
  /** Array of completed messages */
  messages: ChatMessage[];
  /** Initial loading state (before any messages) */
  loading?: boolean;
  /** Current streaming state with main and subagent streams */
  streamingState?: StreamingState;
  /** Whether a message is currently being streamed */
  isStreaming?: boolean;
  /** Active tool calls being executed */
  activeToolCalls?: Array<{
    name: string;
    args: Record<string, unknown>;
  }>;
  /** Whether to show a separator (when new text stream starts after tool execution) */
  showSeparator?: boolean;
  /** Whether the current viewport is mobile (< 768px) */
  isMobile?: boolean;
}

/**
 * StreamingMessage sub-component for displaying in-progress responses
 */
interface StreamingMessageProps {
  /** Partial content received so far */
  content: string;
  /** Whether currently receiving tokens */
  isStreaming: boolean;
  token: Theme['token'];
  /** Whether to show a separator (when new text stream starts after tool execution) */
  showSeparator?: boolean;
  /** Whether the current viewport is mobile (< 768px) */
  isMobile?: boolean;
}

const StreamingMessage = ({
  content,
  isStreaming,
  token,
  showSeparator,
  isMobile = false,
}: StreamingMessageProps) => {
  const { spacing, typography, borderRadius, colors } = useThemeTokens();

  return (
    <List.Item
      style={{
        border: "none",
        display: "flex",
        justifyContent: "center",
        padding: `${spacing.sm}px ${isMobile ? spacing.sm : spacing.md}px`,
      }}
    >
      <div
        style={{
          display: "flex",
          flexDirection: "column",
          gap: spacing.sm,
          backgroundColor: token.colorFillTertiary,
          color: token.colorText,
          marginRight: "auto",
          maxWidth: isMobile ? "85%" : "70%",
          borderRadius: isMobile ? borderRadius.md : borderRadius.lg,
          padding: `${spacing.sm * 0.75}px ${isMobile ? spacing.sm : spacing.md}px`,
          wordBreak: "break-word",
          position: "relative",
        }}
      >
        {/* Message header with role and typing indicator */}
        <div style={{ display: "flex", alignItems: "center", gap: spacing.sm }}>
          <RobotOutlined />
          <Text strong style={{ fontSize: typography.sizes.sm }}>
            Assistant
          </Text>
          {isStreaming && (
            <span
              style={{
                display: "flex",
                alignItems: "center",
                gap: spacing.xs,
                marginLeft: spacing.sm,
              }}
            >
              <LoadingOutlined spin style={{ fontSize: typography.sizes.xs }} />
              <Text style={{ fontSize: typography.sizes.xs, opacity: 0.7 }}>
                generating
              </Text>
            </span>
          )}
        </div>

        {/* Minimalistic separator when text stream resumes after tool execution */}
        {showSeparator && (
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: spacing.sm,
              margin: `${spacing.sm}px 0`,
              opacity: 0.4,
            }}
          >
            <div
              style={{
                flex: 1,
                height: 1,
                background: `linear-gradient(to right, transparent, ${colors.textSecondary}, transparent)`,
              }}
            />
            <div
              style={{
                width: 4,
                height: 4,
                borderRadius: "50%",
                backgroundColor: colors.textSecondary,
              }}
            />
            <div
              style={{
                flex: 1,
                height: 1,
                background: `linear-gradient(to right, transparent, ${colors.textSecondary}, transparent)`,
              }}
            />
          </div>
        )}

        {/* Streaming content with markdown rendering */}
        {content && (
          <MarkdownRenderer content={content} isStreaming={isStreaming} />
        )}

        {/* Typing indicator dots when streaming with no content yet */}
        {isStreaming && !content && (
          <div style={{ display: "flex", gap: spacing.xs, padding: `${spacing.sm}px 0` }}>
            <span className="typing-dot" />
            <span className="typing-dot" />
            <span className="typing-dot" />
          </div>
        )}
      </div>

      {/* CSS for animations */}
      <style>{`
        @keyframes fadeIn {
          from {
            opacity: 0.7;
          }
          to {
            opacity: 1;
          }
        }

        .typing-dot {
          width: 8px;
          height: 8px;
          borderRadius: "50%",
          backgroundColor: token.colorPrimary,
          animation: "typingPulse 1.4s infinite ease-in-out both",
        }

        .typing-dot:nth-child(1) {
          animationDelay: "0s";
        }

        .typing-dot:nth-child(2) {
          animationDelay: "0.2s";
        }

        .typing-dot:nth-child(3) {
          animationDelay: "0.4s";
        }

        @keyframes typingPulse {
          0%, 80%, 100% {
            transform: "scale(0.8)";
            opacity: 0.5;
          }
          40% {
            transform: "scale(1)";
            opacity: 1;
          }
        }
      `}</style>
    </List.Item>
  );
};

/**
 * SubagentMessage sub-component for displaying subagent streaming responses
 */
interface SubagentMessageProps {
  subagent: SubagentStream;
  token: Theme['token'];
  isMobile?: boolean;
  invocationNumber?: number;
}

const SubagentMessage = ({
  subagent,
  token,
  isMobile = false,
  invocationNumber,
}: SubagentMessageProps) => {
  const { spacing, typography, borderRadius } = useThemeTokens();

  // Color coding for different subagent types
  const getSubagentColor = (name: string) => {
    const hash = name.split('').reduce((acc, char) => acc + char.charCodeAt(0), 0);
    const hue = hash % 360;
    return `hsl(${hue}, 70%, 45%)`;
  };

  const accentColor = getSubagentColor(subagent.subagent_name);

  return (
    <List.Item
      style={{
        border: "none",
        display: "flex",
        justifyContent: "center",
        padding: `${spacing.sm}px ${isMobile ? spacing.sm : spacing.md}px`,
      }}
    >
      <div
        style={{
          display: "flex",
          flexDirection: "column",
          gap: spacing.sm,
          backgroundColor: token.colorFillSecondary,
          color: token.colorText,
          marginRight: "auto",
          maxWidth: isMobile ? "85%" : "70%",
          borderRadius: isMobile ? borderRadius.md : borderRadius.lg,
          padding: `${spacing.sm * 0.75}px ${isMobile ? spacing.sm : spacing.md}px`,
          wordBreak: "break-word",
          borderLeft: `4px solid ${accentColor}`,
        }}
      >
        {/* Message header with subagent name and status */}
        <div style={{ display: "flex", alignItems: "center", gap: spacing.sm }}>
          <div
            style={{
              width: 24,
              height: 24,
              borderRadius: "50%",
              backgroundColor: accentColor,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              fontSize: typography.sizes.xs,
              color: "white",
              fontWeight: typography.weights.bold,
            }}
          >
            {subagent.subagent_name.charAt(0).toUpperCase()}
          </div>
          <Text strong style={{ fontSize: typography.sizes.sm }}>
            {subagent.subagent_name}
          </Text>
          {/* Show invocation number when greater than 1 */}
          {invocationNumber && invocationNumber > 1 && (
            <Text style={{ fontSize: typography.sizes.xs, opacity: 0.6 }}>
              ({invocationNumber})
            </Text>
          )}
          {subagent.is_active && (
            <span
              style={{
                display: "flex",
                alignItems: "center",
                gap: spacing.xs,
                marginLeft: spacing.sm,
              }}
            >
              <LoadingOutlined spin style={{ fontSize: typography.sizes.xs }} />
              <Text style={{ fontSize: typography.sizes.xs, opacity: 0.7 }}>
                {subagent.is_complete ? "finishing" : "working"}
              </Text>
            </span>
          )}
        </div>

        {/* Subagent content with markdown rendering */}
        {subagent.content && (
          <MarkdownRenderer content={subagent.content} isStreaming={subagent.is_active} />
        )}

        {/* Typing indicator when active with no content */}
        {subagent.is_active && !subagent.content && (
          <div style={{ display: "flex", gap: spacing.xs, padding: `${spacing.sm}px 0` }}>
            <span className="typing-dot" />
            <span className="typing-dot" />
            <span className="typing-dot" />
          </div>
        )}
      </div>

      {/* CSS for animations */}
      <style>{`
        .typing-dot {
          width: 8px;
          height: 8px;
          border-radius: "50%",
          backgroundColor: ${accentColor},
          animation: "typingPulse 1.4s infinite ease-in-out both",
        }

        .typing-dot:nth-child(1) {
          animationDelay: "0s";
        }

        .typing-dot:nth-child(2) {
          animationDelay: "0.2s";
        }

        .typing-dot:nth-child(3) {
          animationDelay: "0.4s";
        }

        @keyframes typingPulse {
          0%, 80%, 100% {
            transform: "scale(0.8)";
            opacity: 0.5;
          }
          40% {
            transform: "scale(1)";
            opacity: 1;
          }
        }
      `}</style>
    </List.Item>
  );
};

/**
 * PersistedSubagentMessage sub-component for displaying saved subagent messages from chat history
 */
interface PersistedSubagentMessageProps {
  subagentName: string;
  content: string;
  token: Theme['token'];
  isMobile?: boolean;
  invocationNumber?: number;
}

const PersistedSubagentMessage = ({
  subagentName,
  content,
  token,
  isMobile = false,
  invocationNumber,
}: PersistedSubagentMessageProps) => {
  const { spacing, typography, borderRadius } = useThemeTokens();

  // Color coding for different subagent types
  const getSubagentColor = (name: string) => {
    const hash = name.split('').reduce((acc, char) => acc + char.charCodeAt(0), 0);
    const hue = hash % 360;
    return `hsl(${hue}, 70%, 45%)`;
  };

  const accentColor = getSubagentColor(subagentName);

  return (
    <List.Item
      style={{
        border: "none",
        display: "flex",
        justifyContent: "center",
        padding: `${spacing.sm}px ${isMobile ? spacing.sm : spacing.md}px`,
      }}
    >
      <div
        style={{
          display: "flex",
          flexDirection: "column",
          gap: spacing.sm,
          backgroundColor: token.colorFillSecondary,
          color: token.colorText,
          marginRight: "auto",
          maxWidth: isMobile ? "85%" : "70%",
          borderRadius: isMobile ? borderRadius.md : borderRadius.lg,
          padding: `${spacing.sm * 0.75}px ${isMobile ? spacing.sm : spacing.md}px`,
          wordBreak: "break-word",
          borderLeft: `4px solid ${accentColor}`,
        }}
      >
        {/* Message header with subagent name */}
        <div style={{ display: "flex", alignItems: "center", gap: spacing.sm }}>
          <div
            style={{
              width: 24,
              height: 24,
              borderRadius: "50%",
              backgroundColor: accentColor,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              fontSize: typography.sizes.xs,
              color: "white",
              fontWeight: typography.weights.bold,
            }}
          >
            {subagentName.charAt(0).toUpperCase()}
          </div>
          <Text strong style={{ fontSize: typography.sizes.sm }}>
            {subagentName}
          </Text>
          {/* Show invocation number when greater than 1 */}
          {invocationNumber && invocationNumber > 1 && (
            <Text style={{ fontSize: typography.sizes.xs, opacity: 0.6 }}>
              ({invocationNumber})
            </Text>
          )}
        </div>

        {/* Subagent content with markdown rendering */}
        <MarkdownRenderer content={content} />
      </div>
    </List.Item>
  );
};

const getMessageIcon = (role: ChatMessage["role"]) => {
  switch (role) {
    case "user":
      return <UserOutlined />;
    case "assistant":
      return <RobotOutlined />;
    default:
      return null;
  }
};

const getMessageStyle = (role: ChatMessage["role"], token: Theme['token'], isMobile: boolean = false) => {
  switch (role) {
    case "user":
      return {
        backgroundColor: token.colorPrimary,
        color: token.colorTextLightSolid,
        marginLeft: "auto",
        maxWidth: isMobile ? "85%" : "70%",
      };
    case "assistant":
      return {
        backgroundColor: token.colorFillTertiary,
        color: token.colorText,
        marginRight: "auto",
        maxWidth: isMobile ? "85%" : "70%",
      };
    default:
      return {};
  }
};

export const MessageList = ({
  messages,
  loading,
  streamingState,
  isStreaming = false,
  activeToolCalls = [],
  showSeparator = false,
  isMobile = false,
}: MessageListProps) => {
  const { token } = theme.useToken();
  const { spacing, typography, borderRadius } = useThemeTokens();
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Combine regular messages with streaming message for display
  // Filter out tool role messages but keep persisted subagent messages in order
  const displayMessages = useMemo(() => {
    // Filter out tool messages (but keep messages with subagent metadata)
    const filteredMessages = messages.filter(m => m.role !== "tool");
    const result = [...filteredMessages];

    // Add main agent streaming message if there's content
    const mainContent = streamingState?.main ?? "";
    if (isStreaming || mainContent || activeToolCalls.length > 0) {
      result.push({
        id: "streaming-temp",
        role: "assistant" as const,
        content: mainContent,
        createdAt: new Date().toISOString(),
      });
    }

    return result;
  }, [messages, streamingState?.main, isStreaming, activeToolCalls]);

  // Auto-scroll to bottom when new messages arrive or streaming updates
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [displayMessages, streamingState?.main, streamingState?.subagents]);

  if (loading && messages.length === 0) {
    return (
      <div style={{ textAlign: "center", padding: spacing.xl }}>
        <Spin size="large" />
      </div>
    );
  }

  const mainContent = streamingState?.main ?? "";
  const hasSubagents = streamingState?.subagents.size ?? 0 > 0;

  if (messages.length === 0 && !isStreaming && !mainContent && !hasSubagents) {
    return (
      <Empty
        description="Start a conversation by sending a message"
        style={{ marginTop: spacing.xxl }}
      />
    );
  }

  // Check if the last message is the streaming message
  const lastMessageIsStreaming = isStreaming || mainContent || activeToolCalls.length > 0;

  return (
    <>
      <List
        dataSource={displayMessages.slice(0, lastMessageIsStreaming ? -1 : undefined)}
        renderItem={(message) => {
          // Render persisted subagent message
          if (message.metadata?.subagent_name) {
            return (
              <PersistedSubagentMessage
                key={message.id}
                subagentName={message.metadata.subagent_name}
                content={message.content}
                token={token}
                isMobile={isMobile}
                invocationNumber={message.metadata.invocation_number}
              />
            );
          }

          // Render regular message
          return (
            <List.Item
              key={message.id}
              style={{
                border: "none",
                display: "flex",
                justifyContent: "center",
                padding: `${spacing.sm}px ${isMobile ? spacing.sm : spacing.md}px`,
              }}
            >
              <div
                style={{
                  display: "flex",
                  flexDirection: "column",
                  gap: spacing.xs,
                  ...getMessageStyle(message.role, token, isMobile),
                  borderRadius: isMobile ? borderRadius.md : borderRadius.lg,
                  padding: `${spacing.sm * 0.75}px ${isMobile ? spacing.sm : spacing.md}px`,
                  wordBreak: "break-word",
                }}
              >
                {/* Message header with role */}
                <div style={{ display: "flex", alignItems: "center", gap: spacing.sm }}>
                  {getMessageIcon(message.role)}
                  <Text strong style={{ fontSize: typography.sizes.sm }}>
                    {message.role === "user"
                      ? "You"
                      : "Assistant"}
                  </Text>
                </div>

                {/* Message content */}
                {message.role === "user" ? (
                  // User messages remain as plain text
                  <Text
                    style={{
                      whiteSpace: "pre-wrap",
                      fontSize: typography.sizes.md,
                      color: "inherit",
                    }}
                  >
                    {message.content}
                  </Text>
                ) : (
                  // Assistant messages render markdown
                  <MarkdownRenderer content={message.content} />
                )}
              </div>
            </List.Item>
          );
        }}
      />

      {/* Streaming message (always last if present) */}
      {lastMessageIsStreaming && (
        <StreamingMessage
          content={mainContent}
          isStreaming={isStreaming}
          token={token}
          showSeparator={showSeparator}
          isMobile={isMobile}
        />
      )}

      {/* Subagent streaming messages */}
      {streamingState?.subagents && Array.from(streamingState.subagents.values())
        .sort((a, b) => a.started_at - b.started_at)  // Show in order started
        .map((subagent) => (
          <SubagentMessage
            key={subagent.invocation_id}
            subagent={subagent}
            token={token}
            isMobile={isMobile}
            invocationNumber={subagent.invocation_number}
          />
        ))
      }

      {/* Invisible element for auto-scroll */}
      <div ref={messagesEndRef} />
    </>
  );
};
