/**
 * ActivityItem Component
 *
 * Displays a single activity item with entity name, activity badge, and timestamp.
 * Clickable and navigates to the entity detail page.
 */

import { Typography } from "antd";
import { useNavigate } from "react-router-dom";
import { useThemeTokens } from "@/hooks/useThemeTokens";
import { RelativeTime } from "./RelativeTime";
import type { BaseActivityItemProps } from "../types";

const { Text } = Typography;

/**
 * Get color for activity type badge
 */
const ACTIVITY_BADGE_COLORS: Record<string, { bg: string; text: string }> = {
  created: { bg: "rgba(93, 165, 114, 0.15)", text: "#5da572" },
  updated: { bg: "rgba(212, 165, 73, 0.15)", text: "#b8942f" },
  deleted: { bg: "rgba(201, 93, 95, 0.15)", text: "#c95d5f" },
  merged: { bg: "rgba(93, 139, 168, 0.15)", text: "#5d8ba8" },
};
const DEFAULT_BADGE_COLOR = { bg: "rgba(150, 150, 150, 0.15)", text: "#888888" };

/**
 * Generate URL for entity detail page
 *
 * Navigation strategy:
 * - Projects: Navigate to project detail page
 * - WBEs: Navigate to parent project page (WBEs are viewed within project context)
 * - Cost Elements: Navigate to cost element detail page
 * - Change Orders: Navigate to parent project page (change orders are viewed within project context)
 */
const ENTITY_URL_MAP: Record<string, string> = {
  project: "/projects/",
  wbe: "/projects/",
  cost_element: "/cost-elements/",
  change_order: "/projects/",
};

const getEntityUrl = (
  entityType: string,
  entityId: string,
  projectId?: string | null
): string => {
  if ((entityType === "wbe" || entityType === "change_order") && projectId) {
    return `/projects/${projectId}`;
  }
  const prefix = ENTITY_URL_MAP[entityType];
  return prefix ? `${prefix}${entityId}` : "/";
};

/**
 * Single activity item component
 */
export function ActivityItem({ activity, onClick }: BaseActivityItemProps) {
  const navigate = useNavigate();
  const { spacing, typography, colors, borderRadius } = useThemeTokens();
  const badgeColor = ACTIVITY_BADGE_COLORS[activity.activity_type] || DEFAULT_BADGE_COLOR;

  const handleClick = () => {
    if (onClick) {
      onClick();
    } else {
      navigate(getEntityUrl(activity.entity_type, activity.id, activity.project_id));
    }
  };

  return (
    <div
      onClick={handleClick}
      role="button"
      tabIndex={0}
      style={{
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        padding: `${spacing.sm}px ${spacing.md}px`,
        borderRadius: borderRadius.md,
        cursor: "pointer",
        transition: "background 150ms ease",
        textDecoration: "none",
        color: "inherit",
        minHeight: "44px", // Touch target size
      }}
      onMouseEnter={(e) => {
        e.currentTarget.style.background = colors.bgLayout;
      }}
      onMouseLeave={(e) => {
        e.currentTarget.style.background = "transparent";
      }}
      onKeyDown={(e) => {
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          handleClick();
        }
      }}
      aria-label={`View ${activity.name} details`}
    >
      {/* Left side: bullet and entity name */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: spacing.sm,
          flex: 1,
          minWidth: 0, // Allow text truncation
        }}
      >
        <Text
          style={{
            color: colors.textTertiary,
            fontSize: typography.sizes.sm,
          }}
        >
          •
        </Text>
        <Text
          style={{
            fontSize: typography.sizes.md,
            fontWeight: typography.weights.medium,
            color: colors.text,
            whiteSpace: "nowrap",
            overflow: "hidden",
            textOverflow: "ellipsis",
          }}
          title={activity.name} // Show full name on hover
        >
          {activity.name}
        </Text>
      </div>

      {/* Right side: badge and timestamp */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: spacing.sm,
          flexShrink: 0,
        }}
      >
        {/* Activity Badge */}
        <span
          style={{
            fontSize: typography.sizes.xs,
            fontWeight: typography.weights.semiBold,
            padding: "2px 8px",
            borderRadius: borderRadius.sm,
            textTransform: "uppercase",
            letterSpacing: "0.5px",
            background: badgeColor.bg,
            color: badgeColor.text,
          }}
        >
          {activity.activity_type}
        </span>

        {/* Timestamp */}
        <RelativeTime timestamp={activity.timestamp} />
      </div>
    </div>
  );
}
