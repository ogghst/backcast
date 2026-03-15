/**
 * ActivitySection Component
 *
 * Displays a section of recent activity for a specific entity type.
 * Shows title with icon, list of activities, and "View All" link.
 */

import { Typography } from "antd";
import { Link } from "react-router-dom";
import { useThemeTokens } from "@/hooks/useThemeTokens";
import { ActivityItem } from "./ActivityItem";
import type { ActivitySectionProps } from "../types";

const { Text } = Typography;

/**
 * Activity section component with header and activity list
 */
export function ActivitySection({
  title,
  icon,
  entityType,
  activities,
  maxItems = 5,
  viewAllUrl,
}: ActivitySectionProps) {
  const { colors, spacing, typography, borderRadius } = useThemeTokens();

  // Limit activities to maxItems
  const displayActivities = activities.slice(0, maxItems);

  // Entity type colors for icons
  const getEntityColor = () => {
    const colorMap = {
      project: colors.primary,
      wbe: colors.info,
      cost_element: colors.chartEV,
      change_order: colors.chartForecast,
    };
    return colorMap[entityType] || colors.primary;
  };

  const entityColor = getEntityColor();

  return (
    <div
      style={{
        background: colors.bgContainer,
        borderRadius: borderRadius.xl,
        padding: spacing.lg,
        height: "100%",
        display: "flex",
        flexDirection: "column",
      }}
    >
      {/* Section Header */}
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          marginBottom: spacing.md,
          paddingBottom: spacing.md,
          borderBottom: `1px solid ${colors.borderSecondary}`,
        }}
      >
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: spacing.sm,
          }}
        >
          <span
            style={{
              fontSize: typography.sizes.xl,
              color: entityColor,
            }}
          >
            {icon}
          </span>
          <Text
            style={{
              fontSize: typography.sizes.lg,
              fontWeight: typography.weights.semiBold,
              color: colors.text,
            }}
          >
            {title}
          </Text>
        </div>

        {/* View All Link */}
        {viewAllUrl && (
          <Link
            to={viewAllUrl}
            style={{
              fontSize: typography.sizes.sm,
              fontWeight: typography.weights.medium,
              color: colors.primary,
              textDecoration: "none",
              transition: "color 150ms ease",
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.textDecoration = "underline";
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.textDecoration = "none";
            }}
            aria-label={`View all ${title.toLowerCase()}`}
          >
            View All →
          </Link>
        )}
      </div>

      {/* Activity List */}
      <div
        style={{
          display: "flex",
          flexDirection: "column",
          gap: spacing.xs,
          flex: 1,
        }}
        role="list"
        aria-label={`Recent ${title.toLowerCase()}`}
      >
        {displayActivities.length === 0 ? (
          <Text
            style={{
              fontSize: typography.sizes.md,
              color: colors.textSecondary,
              textAlign: "center",
              padding: `${spacing.lg}px 0`,
            }}
          >
            No recent activity
          </Text>
        ) : (
          displayActivities.map((activity) => (
            <ActivityItem key={activity.id} activity={activity} />
          ))
        )}
      </div>
    </div>
  );
}
