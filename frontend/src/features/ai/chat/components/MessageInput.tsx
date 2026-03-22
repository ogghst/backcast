/**
 * MessageInput Component
 *
 * Text input for sending chat messages.
 * Mobile-optimized with larger touch targets and gesture-friendly layout.
 * Supports Enter to send, Shift+Enter for newline.
 * Includes cancel button for stopping in-progress AI generation.
 *
 * Design: Industrial Technical Minimalism
 * - 44px minimum touch targets for mobile
 * - Prominent primary action button
 * - Character count as subtle indicator
 * - Auto-expanding textarea
 */

import { useState, useCallback, useRef, useEffect } from "react";
import { Input, Button, Space, Typography, theme } from "antd";
import { SendOutlined, StopOutlined } from "@ant-design/icons";
import { Grid } from "antd";
import { useThemeTokens } from "@/hooks/useThemeTokens";

const { TextArea } = Input;
const { Text } = Typography;
const { useBreakpoint } = Grid;

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
const MOBILE_MAX_ROWS = 4;
const DESKTOP_MAX_ROWS = 6;

export const MessageInput = ({
  onSend,
  disabled = false,
  loading = false,
  placeholder = "Type your message...",
  maxLength = MAX_LENGTH,
  isStreaming = false,
  onCancel,
}: MessageInputProps) => {
  const screens = useBreakpoint();
  const isMobile = !screens.md; // md breakpoint is 768px
  const isSmallMobile = screens.xs; // xs is 480px

  const { token } = theme.useToken();
  const { spacing, typography } = useThemeTokens();
  const [message, setMessage] = useState("");
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Focus textarea on mount (for desktop)
  useEffect(() => {
    if (!isMobile && textareaRef.current) {
      textareaRef.current.focus();
    }
  }, [isMobile]);

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

  const canSend = message.trim().length > 0 && !disabled && !loading && !isStreaming;
  const isInputDisabled = disabled || isStreaming;
  const showCharCount = message.length > maxLength * 0.8 || isSmallMobile;

  // Mobile: inline button layout
  if (isMobile) {
    return (
      <div
        style={{
          padding: spacing.sm,
          borderTop: `1px solid ${token.colorBorderSecondary}`,
          backgroundColor: token.colorBgContainer,
          paddingBottom: `calc(${spacing.sm}px + env(safe-area-inset-bottom))`,
        }}
      >
        <div
          style={{
            display: "flex",
            gap: spacing.xs,
            alignItems: "flex-end",
          }}
        >
          {/* Text input area */}
          <div
            style={{
              flex: 1,
              display: "flex",
              flexDirection: "column",
              gap: spacing.xs,
            }}
          >
            <TextArea
              ref={textareaRef}
              value={message}
              onChange={(e) => setMessage(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder={placeholder}
              disabled={isInputDisabled}
              maxLength={maxLength}
              autoSize={{
                minRows: 1,
                maxRows: MOBILE_MAX_ROWS,
              }}
              style={{
                resize: "none",
                borderRadius: 20,
                padding: `${spacing.sm}px ${spacing.md}px`,
                fontSize: typography.sizes.md,
              }}
            />
            {/* Character count - show when approaching limit or on small mobile */}
            {showCharCount && (
              <div
                style={{
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "center",
                  paddingHorizontal: spacing.xs,
                }}
              >
                <Text
                  type="secondary"
                  style={{
                    fontSize: typography.sizes.xs,
                    fontFamily: '"JetBrains Mono", monospace',
                    opacity: 0.6,
                  }}
                >
                  {message.length.toLocaleString()}
                </Text>
              </div>
            )}
          </div>

          {/* Send/Stop button - fixed size, prominent */}
          <Button
            type={isStreaming ? "default" : "primary"}
            danger={isStreaming}
            icon={isStreaming ? <StopOutlined /> : <SendOutlined />}
            onClick={isStreaming ? handleCancel : handleSend}
            disabled={!isStreaming && !canSend}
            loading={loading && !isStreaming}
            aria-label={isStreaming ? "Stop generation" : "Send message"}
            style={{
              minWidth: 44,
              height: 44,
              borderRadius: 22,
              flexShrink: 0,
              ...(!isStreaming && canSend && {
                background: `linear-gradient(135deg, ${token.colorPrimary} 0%, ${token.colorPrimaryHover} 100%)`,
                border: "none",
                boxShadow: `0 4px 12px ${token.colorPrimary}20`,
              }),
            }}
          />
        </div>
      </div>
    );
  }

  // Desktop: traditional layout with button below
  return (
    <div
      style={{
        padding: spacing.md,
        borderTop: `1px solid ${token.colorBorderSecondary}`,
        backgroundColor: token.colorBgContainer,
      }}
    >
      <Space direction="vertical" style={{ width: "100%" }} size="small">
        <TextArea
          ref={textareaRef}
          value={message}
          onChange={(e) => setMessage(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={placeholder}
          disabled={isInputDisabled}
          maxLength={maxLength}
          autoSize={{ minRows: 1, maxRows: DESKTOP_MAX_ROWS }}
          style={{ resize: "none" }}
        />
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
          }}
        >
          <Text
            type="secondary"
            style={{
              fontSize: typography.sizes.xs,
              fontFamily: '"JetBrains Mono", monospace',
            }}
          >
            {message.length.toLocaleString()} / {maxLength.toLocaleString()}
          </Text>
          {isStreaming ? (
            <Button
              type="primary"
              danger
              icon={<StopOutlined />}
              onClick={handleCancel}
              aria-label="Stop generation"
              style={{
                minWidth: 88,
                height: 36,
              }}
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
              style={{
                minWidth: 88,
                height: 36,
              }}
            >
              Send
            </Button>
          )}
        </div>
      </Space>
    </div>
  );
};
