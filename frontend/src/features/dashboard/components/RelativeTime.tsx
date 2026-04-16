/**
 * RelativeTime Component
 *
 * Displays timestamps as relative time (e.g., "2 hours ago", "yesterday").
 * Updates automatically every minute when on page.
 */

import { useState, useEffect } from "react";
import { Typography } from "antd";
import { useThemeTokens } from "@/hooks/useThemeTokens";
import { formatDate } from "@/utils/formatters";

const { Text } = Typography;

interface RelativeTimeProps {
  /** ISO 8601 timestamp string */
  timestamp: string;
  /** CSS class name for custom styling */
  className?: string;
}

/**
 * Format timestamp as relative time with automatic updates
 *
 * Rules:
 * - < 1 minute: "Just now"
 * - < 1 hour: "X minutes ago"
 * - < 24 hours: "X hours ago"
 * - < 7 days: "X days ago"
 * - < 30 days: "X weeks ago"
 * - >= 30 days: "MMM DD, YYYY" (absolute date)
 */
export function RelativeTime({ timestamp, className }: RelativeTimeProps) {
  const [currentTime, setCurrentTime] = useState(() => Date.now());
  const { colors, typography } = useThemeTokens();

  // Update current time every minute
  useEffect(() => {
    const interval = setInterval(() => {
      setCurrentTime(Date.now());
    }, 60000); // Update every minute

    return () => clearInterval(interval);
  }, []);

  /**
   * Format the timestamp as relative time
   */
  const formatRelativeTime = (timestamp: string): string => {
    const date = new Date(timestamp);
    const now = new Date(currentTime);
    const diffMs = now.getTime() - date.getTime();
    const diffSecs = Math.floor(diffMs / 1000);
    const diffMins = Math.floor(diffSecs / 60);
    const diffHours = Math.floor(diffMins / 60);
    const diffDays = Math.floor(diffHours / 24);

    // Future dates - show absolute date
    if (diffMs < 0) {
      return formatDate(timestamp, { style: "medium" });
    }

    // Less than 1 minute
    if (diffMins < 1) {
      return "Just now";
    }

    // Less than 1 hour
    if (diffMins < 60) {
      return `${diffMins} minute${diffMins > 1 ? "s" : ""} ago`;
    }

    // Less than 24 hours
    if (diffHours < 24) {
      return `${diffHours} hour${diffHours > 1 ? "s" : ""} ago`;
    }

    // Less than 7 days
    if (diffDays < 7) {
      return `${diffDays} day${diffDays > 1 ? "s" : ""} ago`;
    }

    // Less than 30 days - show weeks
    if (diffDays < 30) {
      const weeks = Math.floor(diffDays / 7);
      return `${weeks} week${weeks > 1 ? "s" : ""} ago`;
    }

    // 30+ days - show absolute date
    return formatDate(timestamp, { style: "medium" });
  };

  return (
    <Text
      className={className}
      style={{
        fontSize: typography.sizes.sm,
        color: colors.textTertiary,
        fontWeight: typography.weights.normal,
      }}
    >
      {formatRelativeTime(timestamp)}
    </Text>
  );
}
