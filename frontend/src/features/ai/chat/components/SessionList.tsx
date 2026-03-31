/**
 * SessionList Component
 *
 * Sidebar displaying conversation sessions.
 * Supports selection, deletion, and new chat creation.
 */

import { List, Button, Empty, Popconfirm, Typography, theme } from "antd";
import {
  PlusOutlined,
  DeleteOutlined,
  MessageOutlined,
} from "@ant-design/icons";
import type { AIConversationSessionPublic, AgentExecutionPublic } from "../../types";
import { useThemeTokens } from "@/hooks/useThemeTokens";
import { LoadMoreButton } from "./LoadMoreButton";

const { Text } = Typography;

interface SessionListProps {
  sessions: AIConversationSessionPublic[];
  currentSessionId?: string;
  onSessionSelect: (sessionId: string) => void;
  onNewChat: () => void;
  onDeleteSession: (sessionId: string) => void;
  loading?: boolean;
  /** Hide the "New Chat" button in the header (useful when embedded in ChatInterface) */
  hideNewChatButton?: boolean;
  /** Pagination props */
  hasMore?: boolean;
  onLoadMore?: () => void;
  loadingMore?: boolean;
}

/**
 * Status dot indicator for active agent executions.
 * Uses Ant Design theme tokens for consistent coloring.
 * Green pulsing for running, amber for awaiting_approval.
 */
const ExecutionStatusDot = ({ execution }: { execution: AgentExecutionPublic }) => {
  const { token } = theme.useToken();

  const dotColor =
    execution.status === "running"
      ? token.colorSuccess
      : execution.status === "awaiting_approval"
        ? token.colorWarning
        : "transparent";

  const needsPulse = execution.status === "running" || execution.status === "awaiting_approval";

  return (
    <span
      title={`Execution ${execution.status}`}
      style={{
        display: "inline-block",
        width: 8,
        height: 8,
        borderRadius: "50%",
        backgroundColor: dotColor,
        flexShrink: 0,
        animation: needsPulse ? "status-pulse 2s ease-in-out infinite" : "none",
      }}
    />
  );
};

const formatSessionTitle = (
  session: AIConversationSessionPublic
): string => {
  if (session.title) {
    return session.title;
  }
  // Fallback: use date as title
  const date = new Date(session.created_at);
  return date.toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
};

const formatSessionTime = (dateStr: string): string => {
  const date = new Date(dateStr);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffMins = Math.floor(diffMs / 60000);
  const diffHours = Math.floor(diffMs / 3600000);
  const diffDays = Math.floor(diffMs / 86400000);

  if (diffMins < 1) return "Just now";
  if (diffMins < 60) return `${diffMins}m ago`;
  if (diffHours < 24) return `${diffHours}h ago`;
  if (diffDays < 7) return `${diffDays}d ago`;
  return date.toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
  });
};

export const SessionList = ({
  sessions,
  currentSessionId,
  onSessionSelect,
  onNewChat,
  onDeleteSession,
  loading = false,
  hideNewChatButton = false,
  hasMore = false,
  onLoadMore,
  loadingMore = false,
}: SessionListProps) => {
  const { token } = theme.useToken();
  const { spacing, typography, borderRadius } = useThemeTokens();

  return (
    <div
      style={{
        height: "100%",
        display: "flex",
        flexDirection: "column",
        borderRight: `1px solid ${token.colorBorderSecondary}`,
        backgroundColor: token.colorBgContainer,
      }}
    >
      <style>
        {`
          @keyframes status-pulse {
            0%, 100% { opacity: 1; transform: scale(1); }
            50% { opacity: 0.5; transform: scale(0.85); }
          }
        `}
      </style>
      {/* Header - only show if not hiding the New Chat button */}
      {!hideNewChatButton && (
        <div
          style={{
            padding: spacing.md,
            borderBottom: `1px solid ${token.colorBorderSecondary}`,
          }}
        >
          <Button
            type="primary"
            icon={<PlusOutlined />}
            onClick={onNewChat}
            block
          >
            New Chat
          </Button>
        </div>
      )}

      {/* Sessions List */}
      <div style={{ flex: 1, overflow: "auto" }}>
        {sessions.length === 0 && !loading ? (
          <Empty
            description="No conversations yet"
            image={Empty.PRESENTED_IMAGE_SIMPLE}
            style={{ marginTop: spacing.xl }}
          />
        ) : (
          <>
            <List
              dataSource={sessions}
              loading={loading}
              renderItem={(session) => (
              <List.Item
                style={{
                  padding: `${spacing.sm * 0.75}px ${spacing.md}px`,
                  margin: `${spacing.xs}px ${spacing.sm}px`,
                  borderRadius: borderRadius.md,
                  cursor: "pointer",
                  backgroundColor:
                    session.id === currentSessionId ? token.colorPrimaryBg : "transparent",
                  border:
                    session.id === currentSessionId
                      ? `1px solid ${token.colorPrimaryBorder}`
                      : "1px solid transparent",
                  transition: "all 0.2s",
                }}
                onClick={() => onSessionSelect(session.id)}
                onMouseEnter={(e) => {
                  if (session.id !== currentSessionId) {
                    e.currentTarget.style.backgroundColor = token.colorBgTextHover;
                  }
                }}
                onMouseLeave={(e) => {
                  if (session.id !== currentSessionId) {
                    e.currentTarget.style.backgroundColor = "transparent";
                  }
                }}
              >
                <div
                  style={{
                    width: "100%",
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "flex-start",
                  }}
                  onClick={(e) => {
                    // Prevent triggering session select when clicking delete
                    if ((e.target as HTMLElement).closest(".delete-btn")) {
                      e.stopPropagation();
                    }
                  }}
                >
                  <div
                    style={{
                      flex: 1,
                      minWidth: 0,
                      display: "flex",
                      alignItems: "center",
                      gap: spacing.sm,
                    }}
                  >
                    {session.active_execution ? (
                      <ExecutionStatusDot execution={session.active_execution} />
                    ) : (
                      <MessageOutlined style={{ color: token.colorPrimary }} />
                    )}
                    <div style={{ minWidth: 0, flex: 1 }}>
                      <Text
                        ellipsis={{ tooltip: formatSessionTitle(session) }}
                        strong={session.id === currentSessionId}
                      >
                        {formatSessionTitle(session)}
                      </Text>
                      <div>
                        <Text type="secondary" style={{ fontSize: typography.sizes.xs }}>
                          {formatSessionTime(session.updated_at)}
                        </Text>
                      </div>
                    </div>
                  </div>
                  <Popconfirm
                    title="Delete this chat?"
                    description="This action cannot be undone."
                    onConfirm={(e) => {
                      e?.stopPropagation();
                      onDeleteSession(session.id);
                    }}
                    okText="Delete"
                    cancelText="Cancel"
                    okButtonProps={{ danger: true }}
                  >
                    <Button
                      type="text"
                      icon={<DeleteOutlined />}
                      danger
                      size="small"
                      className="delete-btn"
                      onClick={(e) => e.stopPropagation()}
                      disabled={session.active_execution?.status === "running" || session.active_execution?.status === "awaiting_approval"}
                      style={{ padding: `0 ${spacing.sm}px` }}
                    />
                  </Popconfirm>
                </div>
              </List.Item>
            )}
            />
            {/* Load More Button */}
            {hasMore && onLoadMore && (
              <LoadMoreButton
                onLoadMore={onLoadMore}
                loading={loadingMore}
                disabled={loading}
              />
            )}
          </>
        )}
      </div>
    </div>
  );
};
