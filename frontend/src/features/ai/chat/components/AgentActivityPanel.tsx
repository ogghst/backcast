/**
 * AgentActivityPanel Component
 *
 * Visualizes Deep Agent's latest planning, subagent delegation, and tool execution.
 * Simplified, clean design with activity history tracking.
 *
 * Features:
 * - Planning phase visualization (write_todos)
 * - Active subagent indicator
 * - Tool execution status
 * - Activity history with collapsible panel
 * - Smooth animations and transitions
 */

import { memo, useState, useEffect } from "react";
import { RobotOutlined, ThunderboltOutlined, DownOutlined } from "@ant-design/icons";
import { theme, Grid } from "antd";
import { useThemeTokens } from "@/hooks/useThemeTokens";

/**
 * Agent activity states - simplified to only track thinking and executing
 */
export type AgentActivityType = "thinking" | "executing";

/**
 * Agent activity state for visualization - simplified
 */
export interface AgentActivity {
  type: AgentActivityType;
  toolName?: string;
  timestamp: number;
}

interface AgentActivityPanelProps {
  /** Current agent activity (latest only) */
  activity: AgentActivity | null;
  /** Activity history items (max 10) */
  activityHistory?: ActivityHistoryItem[];
}

/**
 * Activity history item for tracking past activities
 */
export interface ActivityHistoryItem {
  activity: AgentActivity;
  displayTime: string; // Relative time like "2s ago"
}

/**
 * Latest activity display component with smooth transitions
 */
const LatestActivityDisplay = memo(({ activity }: { activity: AgentActivity }) => {
  const { spacing, typography, colors, borderRadius } = useThemeTokens();
  const [isVisible, setIsVisible] = useState(false);

  useEffect(() => {
    // Entrance animation
    const timer = setTimeout(() => setIsVisible(true), 50);
    return () => clearTimeout(timer);
  }, []);

  const getActivityConfig = () => {
    switch (activity.type) {
      case "executing":
        return {
          icon: <ThunderboltOutlined />,
          label: activity.toolName || "Executing tool",
          color: colors.info,
          bgColor: `${colors.info}08`,
        };
      default: // thinking
        return {
          icon: <RobotOutlined />,
          label: "Thinking",
          color: colors.textSecondary,
          bgColor: `${colors.textSecondary}08`,
        };
    }
  };

  const config = getActivityConfig();

  return (
    <div
      key={activity.timestamp}
      style={{
        display: "flex",
        alignItems: "flex-start",
        gap: spacing.sm,
        padding: spacing.sm,
        background: config.bgColor,
        borderLeft: `2px solid ${config.color}`,
        borderRadius: borderRadius.md,
        opacity: isVisible ? 1 : 0,
        transform: isVisible ? "translateX(0)" : "translateX(-10px)",
        transition: "opacity 0.2s ease, transform 0.2s ease",
      }}
    >
      {/* Icon with subtle animation for active states */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          width: 20,
          height: 20,
          borderRadius: "50%",
          background: config.color,
          color: "#fff",
          fontSize: typography.sizes.xs,
          flexShrink: 0,
          ...(activity.type !== "executing" && {
            animation: "gentle-pulse 2s ease-in-out infinite",
          }),
        }}
      >
        {config.icon}
      </div>

      {/* Content */}
      <div style={{ flex: 1, minWidth: 0 }}>
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: spacing.xs,
            marginBottom: activity.type === "planning" && activity.steps ? spacing.xs : 0,
          }}
        >
          <span
            style={{
              fontSize: typography.sizes.xs,
              fontWeight: typography.weights.medium,
              color: config.color,
              fontFamily: "system-ui, -apple-system, sans-serif",
              textTransform: "uppercase",
              letterSpacing: "0.3px",
            }}
          >
            {config.label}
          </span>

          {/* Loading dots for active states */}
          {activity.type === "thinking" || activity.type === "executing" ? (
            <span style={{ display: "flex", gap: 2, marginLeft: spacing.xs }}>
              <span
                style={{
                  width: 3,
                  height: 3,
                  borderRadius: "50%",
                  background: config.color,
                  animation: "dot-flashing 1.4s infinite ease-in-out both",
                }}
              />
              <span
                style={{
                  width: 3,
                  height: 3,
                  borderRadius: "50%",
                  background: config.color,
                  animation: "dot-flashing 1.4s infinite ease-in-out both 0.2s",
                }}
              />
              <span
                style={{
                  width: 3,
                  height: 3,
                  borderRadius: "50%",
                  background: config.color,
                  animation: "dot-flashing 1.4s infinite ease-in-out both 0.4s",
                }}
              />
            </span>
          ) : null}
        </div>
      </div>
    </div>
  );
});

LatestActivityDisplay.displayName = "LatestActivityDisplay";

/**
 * Activity history item component
 */
const ActivityHistoryItem = memo(({ item }: { item: ActivityHistoryItem }) => {
  const { spacing, typography, colors } = useThemeTokens();

  const getConfig = () => {
    switch (item.activity.type) {
      case "executing":
        return { icon: <ThunderboltOutlined />, color: colors.info };
      default:
        return { icon: <RobotOutlined />, color: colors.textSecondary };
    }
  };

  const config = getConfig();

  return (
    <div
      style={{
        display: "flex",
        alignItems: "center",
        gap: spacing.xs,
        padding: `${spacing.xs / 2}px ${spacing.sm}`,
        fontSize: typography.sizes.xs,
        color: colors.textSecondary,
        fontFamily: "system-ui, -apple-system, sans-serif",
      }}
    >
      <span style={{ color: config.color, fontSize: typography.sizes.xs }}>
        {config.icon}
      </span>
      <span style={{ flex: 1, minWidth: 0, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
        {item.activity.toolName || item.activity.type}
      </span>
      <span style={{ fontSize: typography.sizes.xs, opacity: 0.7 }}>
        {item.displayTime || "Recently"}
      </span>
    </div>
  );
});

ActivityHistoryItem.displayName = "ActivityHistoryItem";

/**
 * Main AgentActivityPanel component - shows latest activity with optional history
 */
export const AgentActivityPanel = memo(({ activity, activityHistory: propActivityHistory = [] }: AgentActivityPanelProps) => {
  const { token } = theme.useToken();
  const { spacing, colors, borderRadius } = useThemeTokens();
  const screens = Grid.useBreakpoint();
  const isMobile = !screens.md; // md breakpoint is 768px

  // Use state-based expansion instead of hover for touch compatibility
  const [isExpanded, setIsExpanded] = useState(false);

  // Use passed history or empty array
  const activityHistory = propActivityHistory;
  const hasHistory = activityHistory.length > 0;

  const toggleExpanded = () => {
    if (hasHistory) {
      setIsExpanded(prev => !prev);
    }
  };

  if (!activity) {
    return null;
  }

  return (
    <>
      <style>
        {`
          @keyframes gentle-pulse {
            0%, 100% { opacity: 1; transform: scale(1); }
            50% { opacity: 0.8; transform: scale(1.05); }
          }

          @keyframes dot-flashing {
            0% { opacity: 0.3; transform: scale(0.8); }
            50% { opacity: 1; transform: scale(1); }
            100% { opacity: 0.3; transform: scale(0.8); }
          }

          @keyframes chevron-rotate {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(180deg); }
          }

          .chevron-icon {
            transition: transform 0.3s ease;
          }

          .chevron-icon.expanded {
            transform: rotate(180deg);
          }

          .history-toggle-button {
            cursor: pointer;
            user-select: none;
            -webkit-tap-highlight-color: transparent;
          }

          .history-toggle-button:active {
            opacity: 0.7;
          }
        `}
      </style>

      <div
        style={{
          background: token.colorBgLayout,
          borderTop: `1px solid ${token.colorBorderSecondary}`,
          borderBottom: `1px solid ${token.colorBorderSecondary}`,
        }}
      >
        {/* Latest activity display with expand toggle button */}
        <div
          style={{
            padding: `${spacing.xs}px ${isMobile ? spacing.sm : spacing.md}px`,
            position: "relative"
          }}
        >
          {/* Expandable header with latest activity and toggle button */}
          {hasHistory && (
            <div
              className="history-toggle-button"
              onClick={toggleExpanded}
              style={{
                display: "flex",
                alignItems: "center",
                justifyContent: "space-between",
                marginBottom: spacing.sm,
                padding: `${spacing.xs}px ${spacing.sm}px`,
                background: isExpanded ? `${colors.primary}08` : "transparent",
                borderRadius: borderRadius.md,
                transition: "background 0.2s ease",
              }}
              role="button"
              tabIndex={0}
              aria-expanded={isExpanded}
              aria-label={isExpanded ? "Collapse activity history" : "Expand activity history"}
              onKeyDown={(e) => {
                if (e.key === "Enter" || e.key === " ") {
                  e.preventDefault();
                  toggleExpanded();
                }
              }}
            >
              <div style={{ flex: 1 }}>
                <LatestActivityDisplay activity={activity} />
              </div>

              {/* Chevron icon for expansion indication */}
              <div
                style={{
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  width: 24,
                  height: 24,
                  borderRadius: "50%",
                  background: isExpanded ? `${colors.primary}15` : "transparent",
                  transition: "background 0.2s ease",
                  marginLeft: spacing.sm,
                  flexShrink: 0,
                }}
              >
                <DownOutlined
                  className={`chevron-icon ${isExpanded ? "expanded" : ""}`}
                  style={{
                    fontSize: 12,
                    color: colors.primary,
                  }}
                />
              </div>
            </div>
          )}

          {/* If no history, just show latest activity without toggle */}
          {!hasHistory && (
            <LatestActivityDisplay activity={activity} />
          )}

          {/* Activity history panel - expands on toggle */}
          {hasHistory && (
            <div
              style={{
                maxHeight: isExpanded ? "300px" : "0",
                overflowY: isExpanded ? "auto" : "hidden",
                opacity: isExpanded ? 1 : 0,
                transition: "max-height 0.3s ease-out, opacity 0.3s ease-out",
                marginTop: isExpanded ? spacing.sm : 0,
              }}
            >
              <div
                style={{
                  borderTop: `1px solid ${token.colorBorderSecondary}`,
                  paddingTop: spacing.sm,
                }}
              >
                {activityHistory.map((item, idx) => (
                  <ActivityHistoryItem key={`${item.activity.timestamp}-${idx}`} item={item} />
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </>
  );
});

AgentActivityPanel.displayName = "AgentActivityPanel";
