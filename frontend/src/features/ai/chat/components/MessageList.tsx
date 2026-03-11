/**
 * MessageList Component
 *
 * Displays chat messages with auto-scroll to latest message.
 * Supports user, assistant, and tool message types.
 * Supports progressive rendering for streaming responses.
 */

import { useEffect, useRef, useMemo } from "react";
import { List, Empty, Typography, Tag, Spin, theme } from "antd";
import type { Theme } from "antd/es/config-provider/context";
import {
  UserOutlined,
  RobotOutlined,
  ToolOutlined,
  LoadingOutlined,
} from "@ant-design/icons";
import type { ChatMessage } from "../../types";

const { Text } = Typography;

/**
 * Format tool name for display (convert snake_case to Title Case)
 */
const formatToolName = (toolName: string): string => {
  return toolName
    .split("_")
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(" ");
};

/**
 * Props for the MessageList component
 */
interface MessageListProps {
  /** Array of completed messages */
  messages: ChatMessage[];
  /** Initial loading state (before any messages) */
  loading?: boolean;
  /** Current streaming content (partial response) */
  streamingContent?: string;
  /** Whether a message is currently being streamed */
  isStreaming?: boolean;
  /** Active tool calls being executed */
  activeToolCalls?: Array<{
    name: string;
    args: Record<string, unknown>;
  }>;
}

/**
 * StreamingMessage sub-component for displaying in-progress responses
 */
interface StreamingMessageProps {
  /** Partial content received so far */
  content: string;
  /** Whether currently receiving tokens */
  isStreaming: boolean;
  /** Active tool calls being executed */
  activeToolCalls?: Array<{
    name: string;
    args: Record<string, unknown>;
  }>;
  token: Theme['token'];
}

const StreamingMessage = ({
  content,
  isStreaming,
  activeToolCalls = [],
  token,
}: StreamingMessageProps) => {
  return (
    <List.Item
      style={{
        border: "none",
        display: "flex",
        justifyContent: "center",
        padding: "0.5rem 1rem",
      }}
    >
      <div
        style={{
          display: "flex",
          flexDirection: "column",
          gap: "0.5rem",
          backgroundColor: token.colorFillTertiary,
          color: token.colorText,
          marginRight: "auto",
          maxWidth: "70%",
          borderRadius: "8px",
          padding: "0.75rem 1rem",
          wordBreak: "break-word",
          position: "relative",
        }}
      >
        {/* Message header with role and typing indicator */}
        <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
          <RobotOutlined />
          <Text strong style={{ fontSize: "0.85rem" }}>
            Assistant
          </Text>
          {isStreaming && (
            <span
              style={{
                display: "flex",
                alignItems: "center",
                gap: "0.25rem",
                marginLeft: "0.5rem",
              }}
            >
              <LoadingOutlined spin style={{ fontSize: "0.8rem" }} />
              <Text style={{ fontSize: "0.75rem", opacity: 0.7 }}>
                generating
              </Text>
            </span>
          )}
        </div>

        {/* Streaming content with fade-in animation for new content */}
        {content && (
          <Text
            style={{
              whiteSpace: "pre-wrap",
              fontSize: "0.95rem",
              color: "inherit",
              animation: isStreaming ? "fadeIn 0.3s ease-in" : "none",
            }}
          >
            {content}
          </Text>
        )}

        {/* Active tool calls */}
        {activeToolCalls.length > 0 && (
          <div style={{ marginTop: "0.5rem" }}>
            <Text style={{ fontSize: "0.85rem", opacity: 0.8, marginRight: "0.5rem" }}>
              Using tools:
            </Text>
            {activeToolCalls.map((tool, idx) => (
              <Tag
                key={idx}
                icon={<ToolOutlined />}
                color="processing"
                style={{ marginLeft: "0.25rem" }}
              >
                {formatToolName(tool.name)}
              </Tag>
            ))}
          </div>
        )}

        {/* Typing indicator dots when streaming with no content yet */}
        {isStreaming && !content && (
          <div style={{ display: "flex", gap: "0.25rem", padding: "0.5rem 0" }}>
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
          backgroundColor: "#1890ff",
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

const getMessageIcon = (role: ChatMessage["role"]) => {
  switch (role) {
    case "user":
      return <UserOutlined />;
    case "assistant":
      return <RobotOutlined />;
    case "tool":
      return <ToolOutlined />;
    default:
      return null;
  }
};

const getMessageStyle = (role: ChatMessage["role"], token: Theme['token']) => {
  switch (role) {
    case "user":
      return {
        backgroundColor: token.colorPrimary,
        color: token.colorTextLightSolid,
        marginLeft: "auto",
        maxWidth: "70%",
      };
    case "assistant":
      return {
        backgroundColor: token.colorFillTertiary,
        color: token.colorText,
        marginRight: "auto",
        maxWidth: "70%",
      };
    case "tool":
      return {
        backgroundColor: token.colorWarningBg,
        color: token.colorText,
        border: `1px solid ${token.colorWarningBorder}`,
        margin: "0 auto",
        maxWidth: "80%",
      };
    default:
      return {};
  }
};

export const MessageList = ({
  messages,
  loading,
  streamingContent = "",
  isStreaming = false,
  activeToolCalls = [],
}: MessageListProps) => {
  const { token } = theme.useToken();
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Combine regular messages with streaming message for display
  const displayMessages = useMemo(() => {
    const result = [...messages];

    // Add streaming message if there's content or we're actively streaming
    if (isStreaming || streamingContent || activeToolCalls.length > 0) {
      result.push({
        id: "streaming-temp",
        role: "assistant" as const,
        content: streamingContent,
        createdAt: new Date().toISOString(),
      });
    }

    return result;
  }, [messages, streamingContent, isStreaming, activeToolCalls]);

  // Auto-scroll to bottom when new messages arrive or streaming updates
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [displayMessages, streamingContent]);

  if (loading && messages.length === 0) {
    return (
      <div style={{ textAlign: "center", padding: "2rem" }}>
        <Spin size="large" />
      </div>
    );
  }

  if (messages.length === 0 && !isStreaming && !streamingContent) {
    return (
      <Empty
        description="Start a conversation by sending a message"
        style={{ marginTop: "3rem" }}
      />
    );
  }

  // Check if the last message is the streaming message
  const lastMessageIsStreaming = isStreaming || streamingContent || activeToolCalls.length > 0;

  return (
    <>
      <List
        dataSource={displayMessages.slice(0, lastMessageIsStreaming ? -1 : undefined)}
        renderItem={(message) => (
          <List.Item
            style={{
              border: "none",
              display: "flex",
              justifyContent: "center",
              padding: "0.5rem 1rem",
            }}
          >
            <div
              style={{
                display: "flex",
                flexDirection: "column",
                gap: "0.25rem",
                ...getMessageStyle(message.role, token),
                borderRadius: "8px",
                padding: "0.75rem 1rem",
                wordBreak: "break-word",
              }}
            >
              {/* Message header with role */}
              <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
                {getMessageIcon(message.role)}
                <Text strong style={{ fontSize: "0.85rem" }}>
                  {message.role === "user"
                    ? "You"
                    : message.role === "assistant"
                    ? "Assistant"
                    : "Tool Result"}
                </Text>
              </div>

              {/* Message content */}
              <Text
                style={{
                  whiteSpace: "pre-wrap",
                  fontSize: "0.95rem",
                  color: "inherit",
                }}
              >
                {message.content}
              </Text>

              {/* Tool calls display */}
              {message.toolCalls && message.toolCalls.length > 0 && (
                <div style={{ marginTop: "0.5rem" }}>
                  <Text style={{ fontSize: "0.85rem", opacity: 0.8 }}>
                    Tools used:
                  </Text>
                  {message.toolCalls.map((tool, idx) => (
                    <Tag
                      key={idx}
                      icon={<ToolOutlined />}
                      style={{ marginLeft: "0.25rem" }}
                    >
                      {tool.name || tool.function?.name || "Unknown tool"}
                    </Tag>
                  ))}
                </div>
              )}

              {/* Tool results display */}
              {message.toolResults && (
                <div style={{ marginTop: "0.5rem" }}>
                  <Text style={{ fontSize: "0.85rem", opacity: 0.8, marginRight: "0.5rem" }}>
                    Tool results:
                  </Text>
                  {Array.isArray(message.toolResults) ? (
                    message.toolResults.map((result, idx) => (
                      <Tag
                        key={idx}
                        icon={<ToolOutlined />}
                        color={result.success ? "success" : "error"}
                        style={{ marginLeft: "0.25rem" }}
                      >
                        {formatToolName(result.tool || "Unknown")}
                      </Tag>
                    ))
                  ) : (
                    <Tag icon={<ToolOutlined />}>Results available</Tag>
                  )}
                </div>
              )}
            </div>
          </List.Item>
        )}
      />

      {/* Streaming message (always last if present) */}
      {lastMessageIsStreaming && (
        <StreamingMessage
          content={streamingContent}
          isStreaming={isStreaming}
          activeToolCalls={activeToolCalls}
          token={token}
        />
      )}

      {/* Invisible element for auto-scroll */}
      <div ref={messagesEndRef} />
    </>
  );
};
