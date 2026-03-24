/**
 * WebSocket Debug Panel Component
 *
 * Displays all raw WebSocket messages for debugging and verification.
 * Shows both incoming and outgoing messages with timestamps.
 * Provides filtering and export functionality.
 *
 * Renders as an inline panel below the chat input.
 */

import { useState, useMemo, useCallback } from "react";
import { Typography, Tag, Space, Button, Input, Empty } from "antd";
import {
  ArrowUpOutlined,
  ArrowDownOutlined,
  ClearOutlined,
  DownloadOutlined,
  BugOutlined,
  UpOutlined,
} from "@ant-design/icons";
import { useThemeTokens } from "@/hooks/useThemeTokens";

const { Text } = Typography;
const { Search } = Input;

/** Direction of message flow */
type MessageDirection = "in" | "out";

/** Raw WebSocket message entry */
export interface DebugMessage {
  id: number;
  timestamp: number;
  direction: MessageDirection;
  data: unknown;
}

interface WebSocketDebugPanelProps {
  /** Whether the panel is visible */
  visible: boolean;
  /** Callback to close the panel */
  onClose: () => void;
  /** Array of debug messages to display */
  messages: DebugMessage[];
  /** Callback to clear all messages */
  onClear: () => void;
}

/** Color coding for message types */
const MESSAGE_TYPE_COLORS: Record<string, string> = {
  chat: "blue",
  token: "green",
  tool_call: "orange",
  tool_result: "gold",
  complete: "cyan",
  error: "red",
  approval_request: "magenta",
  approval_response: "purple",
  subagent: "lime",
  subagent_result: "geekblue",
  planning: "volcano",
  thinking: "default",
  ping: "default",
};

/**
 * Get color for a message type based on its content
 */
function getMessageColor(data: unknown): string {
  if (typeof data === "object" && data !== null && "type" in data) {
    const type = (data as { type: string }).type;
    return MESSAGE_TYPE_COLORS[type] || "default";
  }
  return "default";
}

/**
 * Get a short label for a message
 */
function getMessageLabel(data: unknown): string {
  if (typeof data === "object" && data !== null && "type" in data) {
    const type = (data as { type: string }).type;
    return type;
  }
  return "unknown";
}

/**
 * Format JSON data for display
 */
function formatJSON(data: unknown): string {
  try {
    return JSON.stringify(data, null, 2);
  } catch {
    return String(data);
  }
}

/**
 * Format timestamp as relative time
 */
function formatTimestamp(timestamp: number): string {
  const now = Date.now();
  const diff = now - timestamp;

  if (diff < 1000) return "Just now";
  if (diff < 60000) return `${Math.floor(diff / 1000)}s ago`;
  if (diff < 3600000) return `${Math.floor(diff / 60000)}m ago`;

  const date = new Date(timestamp);
  return date.toLocaleTimeString();
}

/**
 * WebSocket Debug Panel
 *
 * Inline panel that renders below the chat input with:
 * - Direction indicators (in/out)
 * - Timestamps
 * - Message type tags
 * - Formatted JSON content
 * - Search/filter functionality
 * - Export to JSON
 * - Fixed height with scrollable content
 */
export const WebSocketDebugPanel: React.FC<WebSocketDebugPanelProps> = ({
  visible,
  onClose,
  messages,
  onClear,
}) => {
  const { spacing } = useThemeTokens();
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedType, setSelectedType] = useState<string | null>(null);

  // Filter messages based on search query and type filter
  const filteredMessages = useMemo(() => {
    return messages.filter((msg) => {
      const jsonStr = JSON.stringify(msg.data).toLowerCase();
      const matchesSearch = !searchQuery || jsonStr.includes(searchQuery.toLowerCase());

      const msgType = getMessageLabel(msg.data);
      const matchesType = !selectedType || msgType === selectedType;

      return matchesSearch && matchesType;
    });
  }, [messages, searchQuery, selectedType]);

  // Get all unique message types for filtering
  const messageTypes = useMemo(() => {
    const types = new Set<string>();
    messages.forEach((msg) => {
      types.add(getMessageLabel(msg.data));
    });
    return Array.from(types).sort();
  }, [messages]);

  // Export messages to JSON file
  const handleExport = useCallback(() => {
    const dataStr = JSON.stringify(messages, null, 2);
    const dataBlob = new Blob([dataStr], { type: "application/json" });
    const url = URL.createObjectURL(dataBlob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `websocket-debug-${Date.now()}.json`;
    link.click();
    URL.revokeObjectURL(url);
  }, [messages]);

  // Don't render if not visible
  if (!visible) {
    return null;
  }

  return (
    <div
      style={{
        borderTop: "1px solid #444",
        background: "#1e1e1e",
        display: "flex",
        flexDirection: "column",
      }}
    >
      {/* Header - always visible */}
      <div
        style={{
          padding: `${spacing.sm}px ${spacing.md}px`,
          background: "#2d2d2d",
          borderBottom: "1px solid #444",
          display: "flex",
          alignItems: "center",
          gap: spacing.sm,
          flexShrink: 0,
        }}
      >
        <Space size="small" style={{ flex: 1 }}>
          <BugOutlined style={{ color: "#888" }} />
          <Text style={{ color: "#e0e0e0", fontWeight: 500 }}>WebSocket Debug</Text>
          <Tag color="blue">{messages.length} messages</Tag>
          {filteredMessages.length !== messages.length && (
            <Tag color="green">{filteredMessages.length} filtered</Tag>
          )}
        </Space>

        <Space size="small">
          <Button
            icon={<DownloadOutlined />}
            onClick={handleExport}
            size="small"
            type="text"
            style={{ color: "#aaa" }}
          >
            Export
          </Button>
          <Button
            icon={<ClearOutlined />}
            onClick={onClear}
            size="small"
            type="text"
            style={{ color: "#aaa" }}
          >
            Clear
          </Button>
          <Button
            icon={<UpOutlined />}
            onClick={onClose}
            size="small"
            type="text"
            style={{ color: "#aaa" }}
          >
            Hide
          </Button>
        </Space>
      </div>

      {/* Controls */}
      <div
        style={{
          padding: `${spacing.sm}px ${spacing.md}px`,
          background: "#252525",
          borderBottom: "1px solid #333",
          flexShrink: 0,
        }}
      >
        <Space direction="vertical" size="small" style={{ width: "100%" }}>
          <Search
            placeholder="Search messages..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            allowClear
            size="small"
            style={{ background: "#1e1e1e" }}
          />

          {/* Message type filters */}
          <Space size="small" wrap style={{ width: "100%" }}>
            <Tag
              clickable
              color={selectedType === null ? "blue" : "default"}
              onClick={() => setSelectedType(null)}
              style={{ cursor: "pointer", margin: 2 }}
            >
              All ({filteredMessages.length})
            </Tag>
            {messageTypes.map((type) => (
              <Tag
                key={type}
                clickable
                color={selectedType === type ? MESSAGE_TYPE_COLORS[type] || "blue" : "default"}
                onClick={() => setSelectedType(selectedType === type ? null : type)}
                style={{ cursor: "pointer", margin: 2 }}
              >
                {type} ({messages.filter((m) => getMessageLabel(m.data) === type).length})
              </Tag>
            ))}
          </Space>
        </Space>
      </div>

      {/* Messages list - scrollable with fixed height */}
      <div
        style={{
          height: 300,
          overflow: "auto",
          padding: spacing.md,
        }}
      >
        {filteredMessages.length === 0 ? (
          <Empty
            description={
              <Text style={{ color: "#888" }}>
                {messages.length === 0 ? "No messages yet" : "No messages match filters"}
              </Text>
            }
            style={{ marginTop: 40 }}
          />
        ) : (
          <Space direction="vertical" size="small" style={{ width: "100%" }}>
            {filteredMessages.map((msg) => {
              const msgColor = getMessageColor(msg.data);
              const msgLabel = getMessageLabel(msg.data);

              return (
                <div
                  key={msg.id}
                  style={{
                    background: "#252525",
                    border: `1px solid ${msg.direction === "in" ? "#3a6" : "#a63"}`,
                    borderRadius: 4,
                    overflow: "hidden",
                  }}
                >
                  {/* Header */}
                  <div
                    style={{
                      padding: "6px 10px",
                      background: msg.direction === "in" ? "#1a2a1a" : "#2a1a1a",
                      borderBottom: "1px solid #333",
                      display: "flex",
                      alignItems: "center",
                      gap: 8,
                    }}
                  >
                    {msg.direction === "in" ? (
                      <ArrowDownOutlined style={{ color: "#3a6", fontSize: 12 }} />
                    ) : (
                      <ArrowUpOutlined style={{ color: "#a63", fontSize: 12 }} />
                    )}
                    <Tag color={msgColor} style={{ margin: 0, fontSize: 11 }}>
                      {msgLabel}
                    </Tag>
                    <Text style={{ color: "#888", fontSize: 11, marginLeft: "auto" }}>
                      {formatTimestamp(msg.timestamp)}
                    </Text>
                  </div>

                  {/* Content */}
                  <pre
                    style={{
                      margin: 0,
                      padding: "8px 10px",
                      fontSize: 11,
                      color: "#d4d4d4",
                      whiteSpace: "pre-wrap",
                      wordBreak: "break-all",
                      maxHeight: 200,
                      overflow: "auto",
                      background: "#1e1e1e",
                    }}
                  >
                    {formatJSON(msg.data)}
                  </pre>
                </div>
              );
            })}
          </Space>
        )}
      </div>
    </div>
  );
};

export default WebSocketDebugPanel;
