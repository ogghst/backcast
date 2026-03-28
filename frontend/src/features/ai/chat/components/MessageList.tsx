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
  CheckOutlined,
} from "@ant-design/icons";
import type { ChatMessage, SubagentStream, MainAgentStream, StreamingState } from "../../types";
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
  /** Whether the stream is complete (for main agent streams) */
  isComplete?: boolean;
  token: Theme['token'];
  /** Whether to show a separator (when new text stream starts after tool execution) */
  showSeparator?: boolean;
  /** Whether the current viewport is mobile (< 768px) */
  isMobile?: boolean;
}

const StreamingMessage = ({
  content,
  isStreaming,
  isComplete = false,
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
          {/* Completion indicator */}
          {!isStreaming && isComplete && content && (
            <span
              style={{
                display: "flex",
                alignItems: "center",
                gap: spacing.xs,
                marginLeft: spacing.sm,
                color: token.colorSuccess,
              }}
            >
              <CheckOutlined style={{ fontSize: typography.sizes.xs }} />
              <Text style={{ fontSize: typography.sizes.xs, opacity: 0.7 }}>
                Done
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
          {/* Completion indicator */}
          {!subagent.is_active && subagent.is_complete && (
            <span
              style={{
                display: "flex",
                alignItems: "center",
                gap: spacing.xs,
                marginLeft: spacing.sm,
                color: token.colorSuccess,
              }}
            >
              <CheckOutlined style={{ fontSize: typography.sizes.xs }} />
              <Text style={{ fontSize: typography.sizes.xs, opacity: 0.7 }}>
                Done
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

/**
 * Displays chat messages with auto-scroll and progressive streaming rendering.
 *
 * Context: Primary message display component for the AI chat feature. Renders
 * persisted messages from the API alongside active streaming bubbles for the
 * main agent and subagents. Uses a useMemo-based sortedStreams computation to
 * render concurrent streams in sequence order without re-sorting on every token.
 *
 * @param props.messages - Array of completed (persisted) chat messages
 * @param props.loading - Whether messages are being fetched initially
 * @param props.streamingState - Current active streaming state with main and subagent streams
 * @param props.isStreaming - Whether a response is actively being streamed
 * @param props.activeToolCalls - Tools currently executing (for legacy fallback display)
 * @param props.showSeparator - Whether to show a divider before new text after tool execution
 * @param props.isMobile - Whether the viewport is below the md breakpoint
 */
export const MessageList = ({
  messages,
  loading,
  streamingState,
  isStreaming = false,
  showSeparator = false,
  isMobile = false,
}: MessageListProps) => {
  const { token } = theme.useToken();
  const { spacing, typography, borderRadius } = useThemeTokens();
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const scrollRafRef = useRef<number | null>(null);

  // Combine main agent streams and subagents, sorted by sequence for rendering
  const sortedStreams = useMemo(() => {
    type StreamItem =
      | { type: 'main'; sequence: number; started_at: number; data: MainAgentStream }
      | { type: 'subagent'; sequence: number; started_at: number; data: SubagentStream };

    const allStreams: StreamItem[] = [];

    if (streamingState?.mainStreams) {
      for (const stream of streamingState.mainStreams.values()) {
        allStreams.push({
          type: 'main',
          sequence: stream.sequence ?? 0,
          started_at: stream.started_at,
          data: stream,
        });
      }
    }

    if (streamingState?.subagents) {
      for (const stream of streamingState.subagents.values()) {
        allStreams.push({
          type: 'subagent',
          sequence: stream.sequence ?? 0,
          started_at: stream.started_at,
          data: stream,
        });
      }
    }

    allStreams.sort((a, b) =>
      a.sequence !== b.sequence
        ? a.sequence - b.sequence
        : a.started_at - b.started_at
    );

    return allStreams;
  }, [streamingState]);

  // Combine regular messages with streaming message for display
  // Filter out tool role messages but keep persisted subagent messages in order
  const displayMessages = useMemo(() => {
    // Filter out tool messages (but keep messages with subagent metadata)
    const filteredMessages = messages.filter(m => m.role !== "tool");
    const result = [...filteredMessages];

    // Only add streaming-temp for the legacy fallback path (main field)
    // when it has actual content. The new path uses mainStreams/subagents.
    const mainContent = streamingState?.main ?? "";
    if (mainContent) {
      result.push({
        id: "streaming-temp",
        role: "assistant" as const,
        content: mainContent,
        createdAt: new Date().toISOString(),
      });
    }

    return result;
  }, [messages, streamingState?.main]);

  // Auto-scroll to bottom when new messages arrive or streaming updates
  useEffect(() => {
    if (scrollRafRef.current !== null) {
      cancelAnimationFrame(scrollRafRef.current);
    }
    scrollRafRef.current = requestAnimationFrame(() => {
      scrollRafRef.current = null;
      messagesEndRef.current?.scrollIntoView({
        behavior: isStreaming ? "instant" : "smooth",
      });
    });
    return () => {
      if (scrollRafRef.current !== null) {
        cancelAnimationFrame(scrollRafRef.current);
        scrollRafRef.current = null;
      }
    };
  }, [displayMessages, streamingState?.main, streamingState?.subagents, isStreaming]);

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
  const hasStreamingTemp = (streamingState?.main ?? "").length > 0;

  return (
    <>
      <List
        dataSource={hasStreamingTemp ? displayMessages.slice(0, -1) : displayMessages}
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

      {/* Streaming message (legacy fallback, only shown when mainStreams is empty) */}
      {hasStreamingTemp && (!streamingState?.mainStreams || streamingState.mainStreams.size === 0) && (
        <StreamingMessage
          content={mainContent}
          isStreaming={isStreaming}
          token={token}
          showSeparator={showSeparator}
          isMobile={isMobile}
        />
      )}

      {/* Combine main agent streams and subagents, render in sequence order */}
      {sortedStreams.map((item) => {
        if (item.type === 'main') {
          return (
            <StreamingMessage
              key={item.data.invocation_id}
              content={item.data.content}
              isStreaming={item.data.is_active}
              isComplete={item.data.is_complete}
              token={token}
              showSeparator={false}
              isMobile={isMobile}
            />
          );
        } else {
          return (
            <SubagentMessage
              key={item.data.invocation_id}
              subagent={item.data}
              token={token}
              isMobile={isMobile}
              invocationNumber={item.data.invocation_number}
            />
          );
        }
      })}

      {/* Typing indicator when waiting for first token */}
      {isStreaming && sortedStreams.length === 0 && !(streamingState?.main) && (
        <StreamingMessage
          content=""
          isStreaming={true}
          token={token}
          isMobile={isMobile}
        />
      )}

      {/* Invisible element for auto-scroll */}
      <div ref={messagesEndRef} />
    </>
  );
};
