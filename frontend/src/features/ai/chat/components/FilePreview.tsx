/**
 * FilePreview Component
 *
 * Displays file attachments in chat messages.
 * Shows thumbnails for images (using inline base64 content) and file icons for documents.
 */

import { PaperClipOutlined } from "@ant-design/icons";
import { useThemeTokens } from "@/hooks/useThemeTokens";
import type { FileAttachment } from "@/features/ai/types";

interface FilePreviewProps {
  attachment: FileAttachment;
}

/**
 * Format file size to human-readable format
 */
const formatFileSize = (bytes: number): string => {
  if (bytes < 1024) {
    return `${bytes} B`;
  } else if (bytes < 1024 * 1024) {
    return `${(bytes / 1024).toFixed(0)} KB`;
  } else {
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  }
};

/**
 * Check if file is an image
 */
const isImage = (fileType: string): boolean => {
  return fileType.startsWith("image/");
};

/**
 * Builds a data URL from base64 content for image display
 */
const buildDataUrl = (fileType: string, content: string): string => {
  return `data:${fileType};base64,${content}`;
};

/**
 * Renders a single file attachment preview
 *
 * Displays:
 * - Thumbnail for image files (using inline base64 content)
 * - File icon for document files
 * - Filename and size
 */
export const FilePreview = ({ attachment }: FilePreviewProps) => {
  const { spacing, typography, borderRadius, colors } = useThemeTokens();
  const isImageFile = isImage(attachment.file_type);

  return (
    <div
      style={{
        display: "inline-flex",
        alignItems: "center",
        gap: spacing.sm,
        padding: `${spacing.xs}px ${spacing.sm}px`,
        backgroundColor: "rgba(0, 0, 0, 0.04)",
        borderRadius: borderRadius.sm,
        border: "1px solid rgba(0, 0, 0, 0.1)",
        color: "inherit",
      }}
      data-testid={`attachment-${attachment.filename}`}
    >
      {/* Thumbnail or icon */}
      {isImageFile && attachment.content ? (
        <img
          src={buildDataUrl(attachment.file_type, attachment.content)}
          alt={attachment.filename}
          style={{
            width: 40,
            height: 40,
            objectFit: "cover",
            borderRadius: borderRadius.xs,
          }}
          data-testid={`image-preview-${attachment.filename}`}
        />
      ) : (
        <PaperClipOutlined
          style={{
            fontSize: 20,
            color: colors.textSecondary,
          }}
          data-testid={`file-icon-${attachment.file_type.split("/")[1] || "file"}`}
        />
      )}

      {/* File info */}
      <div
        style={{
          display: "flex",
          flexDirection: "column",
        }}
      >
        <span
          style={{
            fontSize: typography.sizes.sm,
            fontWeight: typography.weights.medium,
            overflow: "hidden",
            textOverflow: "ellipsis",
            whiteSpace: "nowrap",
            maxWidth: 200,
          }}
        >
          {attachment.filename}
        </span>
        <span
          style={{
            fontSize: typography.sizes.xs,
            color: colors.textSecondary || "rgba(0, 0, 0, 0.45)",
          }}
        >
          {formatFileSize(attachment.file_size)}
        </span>
      </div>
    </div>
  );
};
