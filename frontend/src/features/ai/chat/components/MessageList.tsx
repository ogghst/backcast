/**
 * MessageList Component
 *
 * Displays chat messages with auto-scroll to latest message.
 * Supports user, assistant, and tool message types.
 * Supports progressive rendering for streaming responses.
 */

import { useEffect, useRef, useMemo, useState } from "react";
import { List, Empty, Typography, Spin, theme, Tag } from "antd";
import type { GlobalToken } from "antd/es/theme/interface";
import {
  UserOutlined,
  RobotOutlined,
  LoadingOutlined,
  CheckOutlined,
  DownOutlined,
  UpOutlined,
} from "@ant-design/icons";
import type { ChatMessage } from "../../types";
import type { ContentPart, MainAgentStream, SubagentStream, StreamingState, TokenUsage } from "../types";
import { useThemeTokens } from "@/hooks/useThemeTokens";
import { MarkdownRenderer } from "./MarkdownRenderer";
import { TokenUsageBar } from "./TokenUsageBar";
import { FilePreview } from "./FilePreview";

const { Text } = Typography;

/** Deterministic color for a subagent name based on character hash. */
const getSubagentColor = (name: string): string => {
  const hash = name.split('').reduce((acc, char) => acc + char.charCodeAt(0), 0);
  return `hsl(${hash % 360}, 70%, 45%)`;
};

/** Shared typing dot animation CSS. Inject once per component tree. */
const TYPING_DOT_CSS = `
@keyframes typingPulse {
  0%, 80%, 100% {
    transform: scale(0.8);
    opacity: 0.5;
  }
  40% {
    transform: scale(1);
    opacity: 1;
  }
}
`;

/**
 * Compact inline tool-call chip. Renders on its own line (caller wraps in a
 * block div) between text segments, showing a spinner until completed.
 */
interface ToolCallTagProps {
  part: Extract<ContentPart, { type: "tool_call" }>;
}

const ToolCallTag = ({ part }: ToolCallTagProps) => {
  const { typography } = useThemeTokens();
  return (
    <Tag
      color={part.completed ? "default" : "processing"}
      icon={
        part.completed ? (
          <CheckOutlined style={{ fontSize: typography.sizes.xs }} />
        ) : (
          <LoadingOutlined spin style={{ fontSize: typography.sizes.xs }} />
        )
      }
      style={{ margin: 0, fontSize: typography.sizes.xs }}
    >
      {part.name}
    </Tag>
  );
};

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
  /** Whether to show a separator (when new text stream starts after tool execution) */
  showSeparator?: boolean;
  /** Whether the current viewport is mobile (< 768px) */
  isMobile?: boolean;
  /** Token usage metrics from the last completed response */
  tokenUsage?: TokenUsage | null;
}

/**
 * StreamingMessage sub-component for displaying in-progress responses
 */
interface StreamingMessageProps {
  /** Ordered content parts (text + inline tool calls) */
  parts: ContentPart[];
  /** Whether currently receiving tokens */
  isStreaming: boolean;
  /** Whether the stream is complete (for main agent streams) */
  isComplete?: boolean;
  token: GlobalToken;
  /** Whether to show a separator (when new text stream starts after tool execution) */
  showSeparator?: boolean;
  /** Whether the current viewport is mobile (< 768px) */
  isMobile?: boolean;
}

const StreamingMessage = ({
  parts,
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
          {!isStreaming && isComplete && parts.length > 0 && (
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

        {/* Ordered parts: text segments render as markdown, tool calls inline on their own line */}
        {parts.map((part, index) => {
          if (part.type === "text") {
            return <MarkdownRenderer key={index} content={part.text} isStreaming={isStreaming} />;
          }
          return (
            <div key={index} style={{ margin: "6px 0" }}>
              <ToolCallTag part={part} />
            </div>
          );
        })}

        {/* Typing indicator dots when streaming with no content yet */}
        {isStreaming && parts.length === 0 && (
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
          from { opacity: 0.7; }
          to { opacity: 1; }
        }
        ${TYPING_DOT_CSS}
        .typing-dot {
          width: 8px;
          height: 8px;
          border-radius: 50%;
          background-color: ${token.colorPrimary};
          animation: typingPulse 1.4s infinite ease-in-out both;
        }

        .typing-dot:nth-child(1) {
          animation-delay: 0s;
        }

        .typing-dot:nth-child(2) {
          animation-delay: 0.2s;
        }

        .typing-dot:nth-child(3) {
          animation-delay: 0.4s;
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
  token: GlobalToken;
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
  // Start expanded whenever the bubble has content or is actively streaming,
  // so the supervisor→specialist→supervisor flow reads top-to-bottom.
  // Stays collapsible so the user can fold long specialist output.
  const [isExpanded, setIsExpanded] = useState(
    () => subagent.parts.length > 0 || subagent.is_active,
  );

  const accentColor = getSubagentColor(subagent.subagent_name);

  // Determine if bubble should be clickable (has content or is complete)
  const isClickable = subagent.parts.length > 0 || subagent.is_complete;

  const handleToggle = () => {
    if (isClickable) {
      setIsExpanded(!isExpanded);
    }
  };

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
        onClick={handleToggle}
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
          cursor: isClickable ? "pointer" : "default",
          transition: "opacity 0.2s",
          opacity: isClickable && !isExpanded ? 0.9 : 1,
        }}
        onMouseEnter={(e) => {
          if (isClickable && !isExpanded) {
            e.currentTarget.style.opacity = "1";
          }
        }}
        onMouseLeave={(e) => {
          if (isClickable && !isExpanded) {
            e.currentTarget.style.opacity = "0.9";
          }
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
          {/* Expand/collapse indicator */}
          {isClickable && (
            <span style={{ marginLeft: "auto", opacity: 0.5 }}>
              {isExpanded ? (
                <UpOutlined style={{ fontSize: typography.sizes.xs }} />
              ) : (
                <DownOutlined style={{ fontSize: typography.sizes.xs }} />
              )}
            </span>
          )}
        </div>

        {/* Subagent content rendered as ordered parts - only show when expanded */}
        {isExpanded && subagent.parts.map((part, index) => {
          if (part.type === "text") {
            return <MarkdownRenderer key={index} content={part.text} isStreaming={subagent.is_active} />;
          }
          return (
            <div key={index} style={{ margin: "6px 0" }}>
              <ToolCallTag part={part} />
            </div>
          );
        })}

        {/* Typing indicator when active with no content */}
        {subagent.is_active && subagent.parts.length === 0 && (
          <div style={{ display: "flex", gap: spacing.xs, padding: `${spacing.sm}px 0` }}>
            <span className="typing-dot" />
            <span className="typing-dot" />
            <span className="typing-dot" />
          </div>
        )}
      </div>

      <style>{`
        ${TYPING_DOT_CSS}
        .typing-dot {
          width: 8px;
          height: 8px;
          border-radius: 50%;
          background-color: ${accentColor};
          animation: typingPulse 1.4s infinite ease-in-out both;
        }

        .typing-dot:nth-child(1) {
          animation-delay: 0s;
        }

        .typing-dot:nth-child(2) {
          animation-delay: 0.2s;
        }

        .typing-dot:nth-child(3) {
          animation-delay: 0.4s;
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
  token: GlobalToken;
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
  const [isExpanded, setIsExpanded] = useState(false);

  const accentColor = getSubagentColor(subagentName);

  const handleToggle = () => {
    setIsExpanded(!isExpanded);
  };

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
        onClick={handleToggle}
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
          cursor: "pointer",
          transition: "opacity 0.2s",
          opacity: !isExpanded ? 0.9 : 1,
        }}
        onMouseEnter={(e) => {
          if (!isExpanded) {
            e.currentTarget.style.opacity = "1";
          }
        }}
        onMouseLeave={(e) => {
          if (!isExpanded) {
            e.currentTarget.style.opacity = "0.9";
          }
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
          {/* Completion indicator */}
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
          {/* Expand/collapse indicator */}
          <span style={{ marginLeft: "auto", opacity: 0.5 }}>
            {isExpanded ? (
              <UpOutlined style={{ fontSize: typography.sizes.xs }} />
            ) : (
              <DownOutlined style={{ fontSize: typography.sizes.xs }} />
            )}
          </span>
        </div>

        {/* Subagent content with markdown rendering - only show when expanded */}
        {isExpanded && <MarkdownRenderer content={content} />}
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

const getMessageStyle = (role: ChatMessage["role"], token: GlobalToken, isMobile: boolean = false) => {
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
 * persisted messages from the API alongside one bubble per live stream
 * (main agent segments and subagent handoffs), ordered chronologically by
 * globalSequence so supervisor and specialist bubbles interleave correctly.
 *
 * @param props.messages - Array of completed (persisted) chat messages
 * @param props.loading - Whether messages are being fetched initially
 * @param props.streamingState - Current active streaming state with main and subagent streams
 * @param props.isStreaming - Whether a response is actively being streamed
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
  tokenUsage,
}: MessageListProps) => {
  const { token } = theme.useToken();
  const { spacing, typography, borderRadius } = useThemeTokens();
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const scrollRafRef = useRef<number | null>(null);
  const isNearBottomRef = useRef(true);

  // Unified, chronologically-ordered view of all live streams.
  // Each entry becomes its own bubble so supervisor segments and specialist
  // handoffs interleave in true chronological order (sorted by globalSequence).
  const orderedStreams = useMemo(() => {
    const all: Array<{ kind: "main"; s: MainAgentStream } | { kind: "subagent"; s: SubagentStream }> = [
      ...Array.from(streamingState?.mainStreams?.values() ?? []).map(s => ({ kind: "main" as const, s })),
      ...Array.from(streamingState?.subagents?.values() ?? []).map(s => ({ kind: "subagent" as const, s })),
    ];
    return all.sort((a, b) => a.s.globalSequence - b.s.globalSequence);
  }, [streamingState]);

  // Combine regular messages with streaming message for display
  // Filter out tool role messages but keep persisted subagent messages in order
  const displayMessages = useMemo(() => {
    // When streaming subagents are still visible (completed or active),
    // hide their persisted counterparts to prevent duplicate bubbles
    const hasStreamingSubagents = (streamingState?.subagents.size ?? 0) > 0;

    const filteredMessages = messages.filter(m => {
      if (m.role === "tool") return false;
      // Hide persisted subagent messages when streaming subagents are visible
      if (m.metadata?.subagent_name && hasStreamingSubagents) return false;
      return true;
    });
    return filteredMessages;
  }, [messages, streamingState?.subagents]);

  // Track whether user is near the bottom of the scrollable container
  useEffect(() => {
    const container = messagesEndRef.current?.parentElement;
    if (!container) return;

    const handleScroll = () => {
      const threshold = 80;
      isNearBottomRef.current =
        container.scrollHeight - container.scrollTop - container.clientHeight < threshold;
    };

    container.addEventListener("scroll", handleScroll, { passive: true });
    return () => container.removeEventListener("scroll", handleScroll);
  }, []);

  // When a new user message is sent, force scroll to bottom
  const prevMessageCountRef = useRef(messages.length);
  useEffect(() => {
    if (messages.length > prevMessageCountRef.current) {
      const lastMsg = messages[messages.length - 1];
      if (lastMsg?.role === "user") {
        isNearBottomRef.current = true;
      }
    }
    prevMessageCountRef.current = messages.length;
  }, [messages]);

  // Auto-scroll to bottom only when user is already near the bottom
  useEffect(() => {
    if (!isNearBottomRef.current) return;
    if (scrollRafRef.current !== null) {
      cancelAnimationFrame(scrollRafRef.current);
    }
    scrollRafRef.current = requestAnimationFrame(() => {
      scrollRafRef.current = null;
      // Scroll ONLY the messages container (its parentElement) — never ancestors.
      // scrollIntoView() scrolls every scrollable ancestor including documentElement
      // (it ignores overflow:hidden), which on mobile hides the header and pushes
      // the composer up ~the header height during streaming. scrollTo() is scoped.
      const container = messagesEndRef.current?.parentElement;
      container?.scrollTo({
        top: container.scrollHeight,
        behavior: isStreaming ? "instant" : "smooth",
      });
    });
    return () => {
      if (scrollRafRef.current !== null) {
        cancelAnimationFrame(scrollRafRef.current);
        scrollRafRef.current = null;
      }
    };
  }, [displayMessages, streamingState, isStreaming]);

  if (loading && messages.length === 0) {
    return (
      <div style={{ textAlign: "center", padding: spacing.xl }}>
        <Spin size="large" />
      </div>
    );
  }

  if (messages.length === 0 && !isStreaming && orderedStreams.length === 0) {
    return (
      <Empty
        description="Start a conversation by sending a message"
        style={{ marginTop: spacing.xxl }}
      />
    );
  }

  return (
    <>
      <List
        dataSource={displayMessages}
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

                {/* File attachments */}
                {message.metadata?.attachments && message.metadata.attachments.length > 0 && (
                  <div
                    data-testid="attachment-container"
                    style={{
                      display: "flex",
                      flexWrap: "wrap",
                      gap: spacing.sm,
                      marginTop: spacing.xs,
                    }}
                  >
                    {message.metadata.attachments.map((attachment) => (
                      <FilePreview key={attachment.file_id} attachment={attachment} />
                    ))}
                  </div>
                )}
              </div>
            </List.Item>
          );
        }}
      />

      {/* One bubble per live stream in chronological order. Each supervisor
          segment AND each specialist handoff is its own bubble. */}
      {orderedStreams.map((entry) =>
        entry.kind === "main" ? (
          <StreamingMessage
            key={`main-${entry.s.invocation_id}`}
            parts={entry.s.parts}
            isStreaming={entry.s.is_active}
            isComplete={entry.s.is_complete}
            token={token}
            showSeparator={entry.s.is_active && showSeparator}
            isMobile={isMobile}
          />
        ) : (
          <SubagentMessage
            key={`sub-${entry.s.invocation_id}`}
            subagent={entry.s}
            token={token}
            isMobile={isMobile}
            invocationNumber={entry.s.invocation_number}
          />
        ),
      )}

      {/* Typing indicator when waiting for the first token of any stream */}
      {isStreaming && orderedStreams.length === 0 && (
        <StreamingMessage
          parts={[]}
          isStreaming={true}
          token={token}
          isMobile={isMobile}
        />
      )}

      {/* Token usage telemetry - appears after response completes */}
      {tokenUsage && !isStreaming && (
        <TokenUsageBar token_usage={tokenUsage} />
      )}

      {/* Invisible element for auto-scroll */}
      <div ref={messagesEndRef} />
    </>
  );
};
