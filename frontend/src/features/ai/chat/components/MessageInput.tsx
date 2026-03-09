/**
 * MessageInput Component
 *
 * Text input for sending chat messages.
 * Supports Enter to send, Shift+Enter for newline.
 * Includes cancel button for stopping in-progress AI generation.
 */

import { useState, useCallback } from "react";
import { Input, Button, Space, Typography, theme } from "antd";
import { SendOutlined, StopOutlined } from "@ant-design/icons";

const { TextArea } = Input;
const { Text } = Typography;

interface MessageInputProps {
  onSend: (message: string) => void;
  disabled?: boolean;
  loading?: boolean;
  placeholder?: string;
  maxLength?: number;
  /** Whether AI is currently streaming a response */
  isStreaming?: boolean;
  /** Callback invoked when user cancels streaming */
  onCancel?: () => void;
}

const MAX_LENGTH = 10000;

export const MessageInput = ({
  onSend,
  disabled = false,
  loading = false,
  placeholder = "Type your message...",
  maxLength = MAX_LENGTH,
  isStreaming = false,
  onCancel,
}: MessageInputProps) => {
  const { token } = theme.useToken();
  const [message, setMessage] = useState("");

  const handleSend = useCallback(() => {
    const trimmed = message.trim();
    if (trimmed && !disabled && !loading) {
      onSend(trimmed);
      setMessage("");
    }
  }, [message, onSend, disabled, loading]);

  const handleCancel = useCallback(() => {
    onCancel?.();
  }, [onCancel]);

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        handleSend();
      }
    },
    [handleSend]
  );

  // Note: Ant Design TextArea with autoSize handles height automatically
  // No need for manual height adjustment

  const canSend = message.trim().length > 0 && !disabled && !loading && !isStreaming;
  const isInputDisabled = disabled || isStreaming;

  return (
    <div
      style={{
        padding: "1rem",
        borderTop: `1px solid ${token.colorBorderSecondary}`,
        backgroundColor: token.colorBgContainer,
      }}
    >
      <Space direction="vertical" style={{ width: "100%" }} size="small">
        <TextArea
          value={message}
          onChange={(e) => setMessage(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={placeholder}
          disabled={isInputDisabled}
          maxLength={maxLength}
          autoSize={{ minRows: 1, maxRows: 6 }}
          style={{ resize: "none" }}
        />
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
          }}
        >
          <Text type="secondary" style={{ fontSize: "0.75rem" }}>
            {message.length} / {maxLength}
          </Text>
          {isStreaming ? (
            <Button
              type="primary"
              danger
              icon={<StopOutlined />}
              onClick={handleCancel}
              aria-label="Stop generation"
            >
              Stop
            </Button>
          ) : (
            <Button
              type="primary"
              icon={<SendOutlined />}
              onClick={handleSend}
              disabled={!canSend}
              loading={loading}
            >
              Send
            </Button>
          )}
        </div>
      </Space>
    </div>
  );
};
