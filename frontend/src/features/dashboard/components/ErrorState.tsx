/**
 * ErrorState Component
 *
 * Displays an error message with retry button.
 * Used when dashboard data fails to load.
 */

import { Button, Typography } from "antd";
import { CloseCircleOutlined } from "@ant-design/icons";
import { useThemeTokens } from "@/hooks/useThemeTokens";

const { Text, Title } = Typography;

interface ErrorStateProps {
  /** Error message to display */
  message?: string;
  /** Detailed error information */
  detail?: string;
  /** Retry callback function */
  onRetry?: () => void;
}

/**
 * Error state component with retry action
 */
export function ErrorState({ message, detail, onRetry }: ErrorStateProps) {
  const { colors, spacing, typography, borderRadius } = useThemeTokens();

  return (
    <div
      style={{
        textAlign: "center",
        padding: `${spacing.xl}px ${spacing.lg}px`,
      }}
    >
      <CloseCircleOutlined
        style={{
          fontSize: "48px",
          color: colors.error,
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
        {message || "Unable to load dashboard"}
      </Title>
      <Text
        style={{
          fontSize: typography.sizes.md,
          color: colors.textSecondary,
          marginBottom: spacing.lg,
          display: "block",
        }}
      >
        {detail || "There was a problem loading your dashboard data. Please try again."}
      </Text>
      {onRetry && (
        <Button
          type="primary"
          onClick={onRetry}
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
          Try Again
        </Button>
      )}
    </div>
  );
}
