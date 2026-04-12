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
 * - Send button color indicates connection status
 * - Auto-expanding textarea
 */

import { useState, useCallback, useRef, useEffect } from "react";
import { Input, Button, theme, Popover, Tooltip } from "antd";
import {
  SendOutlined,
  StopOutlined,
  SecurityScanOutlined,
  SafetyOutlined,
  ThunderboltOutlined,
  PaperClipOutlined,
} from "@ant-design/icons";
import { Grid } from "antd";
import { useThemeTokens } from "@/hooks/useThemeTokens";
import { WSConnectionState } from "../types";

const { TextArea } = Input;
const { useBreakpoint } = Grid;

type ExecutionMode = "safe" | "standard" | "expert";

/**
 * Represents a file pending upload
 */
interface PendingAttachment {
  id: string;
  file: File;
  preview?: string; // URL for image preview
}

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
  /** WebSocket connection state for button color */
  connectionState?: WSConnectionState;
  /** Execution mode for AI tool risk level */
  executionMode?: ExecutionMode;
  /** Callback when execution mode changes */
  onExecutionModeChange?: (mode: ExecutionMode) => void;
  /** Callback when attachments are added */
  onAttachmentsChange?: (attachments: PendingAttachment[]) => void;
}

const MAX_LENGTH = 10000;
const MOBILE_MAX_ROWS = 4;
const DESKTOP_MAX_ROWS = 6;

// Icon and color mapping for execution modes
const MODE_CONFIG = {
  safe: {
    icon: SecurityScanOutlined,
    color: "#52c41a",
    bgColor: "#f6ffed",
    borderColor: "#b7eb8f",
    label: "Safe Mode",
    description: "Low risk only",
  },
  standard: {
    icon: SafetyOutlined,
    color: "#faad14",
    bgColor: "#fffbe6",
    borderColor: "#ffe58f",
    label: "Standard Mode",
    description: "Approval needed",
  },
  expert: {
    icon: ThunderboltOutlined,
    color: "#722ed1",
    bgColor: "#f9f0ff",
    borderColor: "#d3adf7",
    label: "Expert Mode",
    description: "All tools",
  },
} as const;

// Get button styling based on connection state
const getConnectionButtonStyle = (
  state: WSConnectionState,
  token: ReturnType<typeof theme.useToken>["token"],
  canSend: boolean
) => {
  // When streaming, always use danger/red style
  if (state === WSConnectionState.ERROR) {
    return {
      background: canSend ? "#ff4d4f" : token.colorErrorBg,
      borderColor: token.colorError,
      boxShadow: canSend ? `0 4px 12px ${token.colorError}40` : "none",
    };
  }

  if (state === WSConnectionState.CONNECTING || state === WSConnectionState.CLOSING) {
    return {
      background: canSend ? "#faad14" : token.colorWarningBg,
      borderColor: token.colorWarning,
      boxShadow: canSend ? `0 4px 12px rgba(250, 173, 20, 0.4)` : "none",
      animation: "buttonPulse 1.5s ease-in-out infinite",
    };
  }

  if (state === WSConnectionState.CLOSED) {
    return {
      background: canSend ? "#8c8c8c" : token.colorBgContainer,
      borderColor: "#8c8c8c",
      boxShadow: "none",
    };
  }

  // OPEN (connected) - use primary gradient
  return {
    background: canSend
      ? `linear-gradient(135deg, ${token.colorPrimary} 0%, ${token.colorPrimaryHover} 100%)`
      : token.colorPrimaryBg,
    borderColor: canSend ? token.colorPrimary : token.colorBorder,
    boxShadow: canSend ? `0 4px 12px ${token.colorPrimary}20` : "none",
  };
};

export const MessageInput = ({
  onSend,
  disabled = false,
  loading = false,
  placeholder = "Type your message...",
  maxLength = MAX_LENGTH,
  isStreaming = false,
  onCancel,
  connectionState = WSConnectionState.CLOSED,
  executionMode = "standard",
  onExecutionModeChange,
  onAttachmentsChange,
}: MessageInputProps) => {
  const screens = useBreakpoint();
  const isMobile = !screens.md; // md breakpoint is 768px

  const { token } = theme.useToken();
  const { spacing, typography } = useThemeTokens();
  const [message, setMessage] = useState("");
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [modePopoverOpen, setModePopoverOpen] = useState(false);

  // Attachment state
  const [pendingAttachments, setPendingAttachments] = useState<PendingAttachment[]>([]);
  const [isDragging, setIsDragging] = useState(false);

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

  // Attachment handlers
  const handleAttachmentClick = useCallback(() => {
    fileInputRef.current?.click();
  }, []);

  const handleFileSelect = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const files = Array.from(e.target.files || []);
      if (files.length === 0) return;

      // Validate file types
      const supportedImageTypes = ["image/png", "image/jpeg", "image/jpg"];
      const supportedDocumentTypes = [
        "application/pdf",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document", // DOCX
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", // XLSX
        "application/vnd.openxmlformats-officedocument.presentationml.presentation", // PPTX
        "text/plain",
        "text/csv",
        "application/json",
      ];

      const unsupportedFiles = files.filter(
        (file) =>
          !supportedImageTypes.includes(file.type) &&
          !supportedDocumentTypes.includes(file.type)
      );

      if (unsupportedFiles.length > 0) {
        const unsupportedNames = unsupportedFiles.map((f) => f.name).join(", ");
        alert(
          `Unsupported file type: ${unsupportedNames}\n\n` +
            `Supported files:\n` +
            `• Images: PNG, JPG, JPEG\n` +
            `• Documents: PDF, DOCX, XLSX, PPTX, TXT, CSV, JSON\n\n` +
            `HTML files are not supported for security reasons.`
        );
        // Reset file input
        if (fileInputRef.current) {
          fileInputRef.current.value = "";
        }
        return;
      }

      const newAttachments: PendingAttachment[] = files.map((file) => {
        const id = `${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
        let preview: string | undefined;

        // Create preview for images
        if (file.type.startsWith("image/")) {
          preview = URL.createObjectURL(file);
        }

        return { id, file, preview };
      });

      setPendingAttachments((prev) => [...prev, ...newAttachments]);
      onAttachmentsChange?.([...pendingAttachments, ...newAttachments]);

      // Reset file input
      if (fileInputRef.current) {
        fileInputRef.current.value = "";
      }
    },
    [pendingAttachments, onAttachmentsChange]
  );

  const handleRemoveAttachment = useCallback(
    (id: string) => {
      setPendingAttachments((prev) => {
        const attachment = prev.find((a) => a.id === id);
        if (attachment?.preview) {
          URL.revokeObjectURL(attachment.preview);
        }
        return prev.filter((a) => a.id !== id);
      });
    },
    []
  );

  // Drag and drop handlers
  const handleDragEnter = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(true);
  }, []);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
  }, []);

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
  }, []);

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      e.stopPropagation();
      setIsDragging(false);

      const files = Array.from(e.dataTransfer.files);
      if (files.length === 0) return;

      // Validate file types (same validation as file input)
      const supportedImageTypes = ["image/png", "image/jpeg", "image/jpg"];
      const supportedDocumentTypes = [
        "application/pdf",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document", // DOCX
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", // XLSX
        "application/vnd.openxmlformats-officedocument.presentationml.presentation", // PPTX
        "text/plain",
        "text/csv",
        "application/json",
      ];

      const unsupportedFiles = files.filter(
        (file) =>
          !supportedImageTypes.includes(file.type) &&
          !supportedDocumentTypes.includes(file.type)
      );

      if (unsupportedFiles.length > 0) {
        const unsupportedNames = unsupportedFiles.map((f) => f.name).join(", ");
        alert(
          `Unsupported file type: ${unsupportedNames}\n\n` +
            `Supported files:\n` +
            `• Images: PNG, JPG, JPEG\n` +
            `• Documents: PDF, DOCX, XLSX, PPTX, TXT, CSV, JSON\n\n` +
            `HTML files are not supported for security reasons.`
        );
        return;
      }

      const newAttachments: PendingAttachment[] = files.map((file) => {
        const id = `${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
        let preview: string | undefined;

        if (file.type.startsWith("image/")) {
          preview = URL.createObjectURL(file);
        }

        return { id, file, preview };
      });

      setPendingAttachments((prev) => [...prev, ...newAttachments]);
      onAttachmentsChange?.([...pendingAttachments, ...newAttachments]);
    },
    [pendingAttachments, onAttachmentsChange]
  );

  const canSend = message.trim().length > 0 && !disabled && !loading && !isStreaming;
  const isInputDisabled = disabled || isStreaming;

  // Connection-based button style (only when not streaming)
  const connectionStyle = !isStreaming
    ? getConnectionButtonStyle(connectionState, token, canSend)
    : null;

  // Execution mode button content
  const currentModeConfig = MODE_CONFIG[executionMode];
  const ModeIcon = currentModeConfig.icon;

  // Execution mode popover content
  const modePopoverContent = (
    <div style={{ minWidth: 180 }}>
      {Object.entries(MODE_CONFIG).map(([mode, config]) => {
        const Icon = config.icon;
        const isSelected = executionMode === mode;
        return (
          <div
            key={mode}
            onClick={() => {
              onExecutionModeChange?.(mode as ExecutionMode);
              setModePopoverOpen(false);
            }}
            style={{
              display: "flex",
              alignItems: "center",
              gap: spacing.sm,
              padding: `${spacing.xs}px ${spacing.sm}px`,
              borderRadius: token.borderRadiusSM,
              cursor: "pointer",
              backgroundColor: isSelected ? token.colorFillAlter : "transparent",
              transition: "background-color 0.2s",
            }}
            onMouseEnter={(e) => {
              if (!isSelected) {
                e.currentTarget.style.backgroundColor = token.colorFillQuaternary;
              }
            }}
            onMouseLeave={(e) => {
              if (!isSelected) {
                e.currentTarget.style.backgroundColor = "transparent";
              }
            }}
          >
            <div
              style={{
                width: 32,
                height: 32,
                borderRadius: "50%",
                backgroundColor: config.bgColor,
                border: `1px solid ${config.borderColor}`,
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                color: config.color,
              }}
            >
              <Icon style={{ fontSize: 16 }} />
            </div>
            <div style={{ flex: 1 }}>
              <div
                style={{
                  fontSize: typography.sizes.sm,
                  fontWeight: typography.weights.medium,
                  color: token.colorText,
                }}
              >
                {config.label}
              </div>
              <div
                style={{
                  fontSize: typography.sizes.xs,
                  color: token.colorTextSecondary,
                }}
              >
                {config.description}
              </div>
            </div>
            {isSelected && (
              <div
                style={{
                  width: 8,
                  height: 8,
                  borderRadius: "50%",
                  backgroundColor: config.color,
                }}
              />
            )}
          </div>
        );
      })}
    </div>
  );

  // Execution mode button
  const executionModeButton = onExecutionModeChange ? (
    <Popover
      content={modePopoverContent}
      trigger="click"
      placement="topLeft"
      open={modePopoverOpen}
      onOpenChange={setModePopoverOpen}
      overlayStyle={{ paddingBottom: 0 }}
      getPopupContainer={(trigger) => trigger.parentElement || document.body}
    >
      <Tooltip title={`${currentModeConfig.label} - ${currentModeConfig.description}`}>
        <Button
          type="text"
          icon={<ModeIcon style={{ fontSize: 18 }} />}
          style={{
            minWidth: 42,
            height: 42,
            borderRadius: 21,
            flexShrink: 0,
            border: "none",
            backgroundColor: currentModeConfig.bgColor,
            color: currentModeConfig.color,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            padding: 0,
          }}
          aria-label={`Change execution mode (${currentModeConfig.label})`}
        />
      </Tooltip>
    </Popover>
  ) : null;

  // Attachment previews
  const attachmentPreviews = pendingAttachments.length > 0 && (
    <div
      style={{
        display: "flex",
        flexWrap: "wrap",
        gap: spacing.sm,
        padding: `${spacing.xs}px ${spacing.sm}px`,
        maxHeight: 120,
        overflowY: "auto",
      }}
    >
      {pendingAttachments.map((attachment) => (
        <div
          key={attachment.id}
          style={{
            display: "flex",
            alignItems: "center",
            gap: spacing.xs,
            padding: spacing.xs,
            backgroundColor: token.colorFillTertiary,
            borderRadius: token.borderRadiusSM,
            border: `1px solid ${token.colorBorderSecondary}`,
          }}
        >
          {attachment.preview ? (
            <img
              data-testid={`thumbnail-${attachment.file.name}`}
              src={attachment.preview}
              alt={attachment.file.name}
              style={{
                width: 40,
                height: 40,
                objectFit: "cover",
                borderRadius: token.borderRadiusXS,
              }}
            />
          ) : (
            <PaperClipOutlined
              data-testid={`file-icon-${attachment.file.name.split(".").pop()}`}
              style={{ fontSize: 24, color: token.colorTextSecondary }}
            />
          )}
          <div
            style={{
              display: "flex",
              flexDirection: "column",
              maxWidth: 150,
            }}
          >
            <span
              style={{
                fontSize: typography.sizes.xs,
                fontWeight: typography.weights.medium,
                overflow: "hidden",
                textOverflow: "ellipsis",
                whiteSpace: "nowrap",
              }}
            >
              {attachment.file.name}
            </span>
            <span
              style={{
                fontSize: typography.sizes.xs,
                color: token.colorTextSecondary,
              }}
            >
              {attachment.file.size < 1024
                ? `${attachment.file.size} B`
                : attachment.file.size < 1024 * 1024
                ? `${(attachment.file.size / 1024).toFixed(1)} KB`
                : `${(attachment.file.size / (1024 * 1024)).toFixed(1)} MB`}
            </span>
          </div>
          <Button
            type="text"
            size="small"
            danger
            aria-label={`Remove ${attachment.file.name}`}
            onClick={() => handleRemoveAttachment(attachment.id)}
            style={{
              minWidth: 20,
              height: 20,
              borderRadius: "50%",
              padding: 0,
            }}
          >
            ×
          </Button>
        </div>
      ))}
    </div>
  );

  // Mobile: inline button layout
  if (isMobile) {
    return (
      <>
        <style>{`
          @keyframes buttonPulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.7; }
          }
        `}</style>
        <div
          data-testid="message-input-container"
          onDragEnter={handleDragEnter}
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
          style={{
            padding: spacing.sm,
            borderTop: `1px solid ${token.colorBorderSecondary}`,
            backgroundColor: token.colorBgContainer,
            paddingBottom: `calc(${spacing.sm}px + env(safe-area-inset-bottom))`,
          }}
        >
          {/* Drop zone overlay */}
          {isDragging && (
            <div
              data-testid="drop-zone-overlay"
              style={{
                position: "absolute",
                top: 0,
                left: 0,
                right: 0,
                bottom: 0,
                backgroundColor: `${token.colorPrimary}10`,
                border: `2px dashed ${token.colorPrimary}`,
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                zIndex: 10,
                opacity: isDragging ? 1 : 0,
                transition: "opacity 0.2s",
                pointerEvents: "none",
              }}
            >
              <div style={{ textAlign: "center" }}>
                <PaperClipOutlined style={{ fontSize: 48, color: token.colorPrimary }} />
                <div style={{ marginTop: spacing.sm, color: token.colorPrimary }}>
                  Drop files to attach
                </div>
              </div>
            </div>
          )}

          <div
            style={{
              display: "flex",
              gap: spacing.xs,
              alignItems: "flex-start",
            }}
          >
            {/* Hidden file input */}
            <input
              ref={fileInputRef}
              type="file"
              aria-label="Upload file"
              style={{ display: "none" }}
              accept="image/*,.pdf,.csv,.json,.txt,.docx,.xlsx,.pptx"
              multiple
              onChange={handleFileSelect}
            />

            {/* Attachment button */}
            <Tooltip title="Attach file">
              <Button
                type="text"
                icon={<PaperClipOutlined />}
                onClick={handleAttachmentClick}
                aria-label="Attach file"
                style={{
                  minWidth: 42,
                  height: 42,
                  borderRadius: 21,
                  flexShrink: 0,
                }}
              />
            </Tooltip>

            {/* Execution mode button - shown when handler provided */}
            {executionModeButton}

            {/* Text input area */}
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
                flex: 1,
                height: 44,
              }}
            />

          {/* Send/Stop button - color indicates connection status */}
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
              border: "none",
              ...(isStreaming ? {
                background: token.colorError,
                color: token.colorErrorBorder,
              } : connectionStyle),
            }}
          />
        </div>

        {/* Attachment previews */}
        {attachmentPreviews}
      </div>
      </>
    );
  }

  // Desktop: compact inline layout (same as mobile)
  return (
    <>
      <style>{`
        @keyframes buttonPulse {
          0%, 100% { opacity: 1; }
          50% { opacity: 0.7; }
        }
      `}</style>
      <div
        data-testid="message-input-container"
        onDragEnter={handleDragEnter}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        style={{
          padding: spacing.md,
          borderTop: `1px solid ${token.colorBorderSecondary}`,
          backgroundColor: token.colorBgContainer,
        }}
      >
        {/* Drop zone overlay */}
        {isDragging && (
          <div
            data-testid="drop-zone-overlay"
            style={{
              position: "absolute",
              top: 0,
              left: 0,
              right: 0,
              bottom: 0,
              backgroundColor: `${token.colorPrimary}10`,
              border: `2px dashed ${token.colorPrimary}`,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              zIndex: 10,
              opacity: isDragging ? 1 : 0,
              transition: "opacity 0.2s",
              pointerEvents: "none",
            }}
          >
            <div style={{ textAlign: "center" }}>
              <PaperClipOutlined style={{ fontSize: 48, color: token.colorPrimary }} />
              <div style={{ marginTop: spacing.sm, color: token.colorPrimary }}>
                Drop files to attach
              </div>
            </div>
          </div>
        )}

        <div
          style={{
            display: "flex",
            gap: spacing.sm,
            alignItems: "flex-start",
          }}
        >
          {/* Hidden file input */}
          <input
            ref={fileInputRef}
            type="file"
            aria-label="Upload file"
            style={{ display: "none" }}
            accept="image/*,.pdf,.csv,.json,.txt,.docx,.xlsx,.pptx"
            multiple
            onChange={handleFileSelect}
          />

          {/* Attachment button */}
          <Tooltip title="Attach file">
            <Button
              type="text"
              icon={<PaperClipOutlined />}
              onClick={handleAttachmentClick}
              aria-label="Attach file"
              style={{
                minWidth: 42,
                height: 42,
                borderRadius: 21,
                flexShrink: 0,
              }}
            />
          </Tooltip>

          {/* Execution mode button - shown when handler provided */}
          {executionModeButton}

          {/* Text input area */}
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
              maxRows: DESKTOP_MAX_ROWS,
            }}
            style={{
              resize: "none",
              borderRadius: 20,
              padding: `${spacing.sm}px ${spacing.md}px`,
              fontSize: typography.sizes.md,
              flex: 1,
              height: 44,
            }}
          />

          {/* Send/Stop button - compact icon-only, color indicates connection status */}
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
              border: "none",
              ...(isStreaming ? {
                background: token.colorError,
                color: token.colorErrorBorder,
              } : connectionStyle),
            }}
          />
        </div>

        {/* Attachment previews */}
        {attachmentPreviews}
      </div>
    </>
  );
};
