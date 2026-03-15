/**
 * DashboardHeader Component
 *
 * Displays welcome message with user's name.
 * Uses useAuthStore to get the current user's information.
 */

import { Typography } from "antd";
import { useAuthStore } from "@/stores/useAuthStore";
import { useThemeTokens } from "@/hooks/useThemeTokens";

const { Title, Text } = Typography;

/**
 * Dashboard header with welcome message
 */
export function DashboardHeader() {
  const { user } = useAuthStore();
  const { colors, typography, spacing } = useThemeTokens();

  // Extract first name from full name
  const firstName = user?.full_name?.split(" ")[0] || "there";

  return (
    <div
      style={{
        padding: 0,
        paddingBottom: spacing.lg,
        marginBottom: spacing.lg,
        borderBottom: `1px solid ${colors.border}`,
      }}
    >
      <Text
        style={{
          fontSize: typography.sizes.xl,
          fontWeight: typography.weights.semiBold,
          color: colors.textSecondary,
          display: "block",
          marginBottom: spacing.xs,
        }}
      >
        Welcome back,
      </Text>
      <Title
        level={1}
        style={{
          fontSize: typography.sizes.xxl,
          fontWeight: typography.weights.bold,
          color: colors.primary,
          margin: 0,
          lineHeight: 1.2,
        }}
      >
        {firstName}
      </Title>
    </div>
  );
}
