/**
 * EmptyState Component
 *
 * Displays an empty state message with call-to-action.
 * Used when there's no data to display on the dashboard.
 */

import { Button, Typography } from "antd";
import { InboxOutlined } from "@ant-design/icons";
import { useNavigate } from "react-router-dom";
import { useThemeTokens } from "@/hooks/useThemeTokens";

const { Text, Title } = Typography;

interface EmptyStateProps {
  /** Empty state message */
  message?: string;
  /** Detailed explanation */
  detail?: string;
  /** Call-to-action button text */
  ctaText?: string;
  /** Call-to-action URL */
  ctaUrl?: string;
}

/**
 * Empty state component with optional call-to-action
 */
export function EmptyState({ message, detail, ctaText, ctaUrl }: EmptyStateProps) {
  const navigate = useNavigate();
  const { colors, spacing, typography, borderRadius } = useThemeTokens();

  const handleCtaClick = () => {
    if (ctaUrl) {
      navigate(ctaUrl);
    }
  };

  return (
    <div
      style={{
        textAlign: "center",
        padding: `${spacing.xl}px ${spacing.lg}px`,
      }}
    >
      <InboxOutlined
        style={{
          fontSize: "64px",
          color: colors.border,
          marginBottom: spacing.md,
        }}
      />
      <Title
        level={3}
        style={{
          fontSize: typography.sizes.lg,
          fontWeight: typography.weights.medium,
          color: colors.text,
          marginBottom: spacing.sm,
        }}
      >
        {message || "No activity yet"}
      </Title>
      <Text
        style={{
          fontSize: typography.sizes.md,
          color: colors.textSecondary,
          marginBottom: spacing.lg,
          display: "block",
        }}
      >
        {detail || "Get started by creating your first project."}
      </Text>
      {ctaText && ctaUrl && (
        <Button
          type="primary"
          onClick={handleCtaClick}
          style={{
            background: colors.primary,
            borderColor: colors.primary,
            borderRadius: borderRadius.md,
            padding: `${spacing.sm}px ${spacing.lg}px`,
            fontSize: typography.sizes.md,
            fontWeight: typography.weights.medium,
            height: "auto",
          }}
        >
          {ctaText}
        </Button>
      )}
    </div>
  );
}
