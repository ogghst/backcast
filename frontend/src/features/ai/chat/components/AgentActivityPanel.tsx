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
import { ClockCircleOutlined, RobotOutlined, ThunderboltOutlined, CheckCircleOutlined } from "@ant-design/icons";
import { theme, Grid } from "antd";
import { useThemeTokens } from "@/hooks/useThemeTokens";

/**
 * Agent activity states
 */
export type AgentActivityType = "thinking" | "planning" | "delegating" | "executing";

/**
 * Agent activity state for visualization
 */
export interface AgentActivity {
  type: AgentActivityType;
  message?: string;
  subagent?: string;
  toolName?: string;
  steps?: Array<{ text: string; done: boolean }>;
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
 * Subagent display names - colors will be applied from theme
 */
const SUBAGENT_STYLES: Record<string, { name: string; icon: string; colorKey: keyof ReturnType<typeof useThemeTokens>['colors'] }> = {
  evm_analyst: { name: "EVM Analyst", icon: "📊", colorKey: "info" },
  change_order_manager: { name: "Change Order Manager", icon: "📋", colorKey: "warning" },
  forecast_analyst: { name: "Forecast Analyst", icon: "📈", colorKey: "success" },
  project_admin: { name: "Project Admin", icon: "📁", colorKey: "primary" },
  advanced_analyst: { name: "Advanced Analyst", icon: "🔬", colorKey: "error" },
};

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
      case "planning":
        return {
          icon: <ClockCircleOutlined />,
          label: "Creating plan",
          color: colors.warning,
          bgColor: `${colors.warning}08`,
        };
      case "delegating": {
        const subagentStyle = SUBAGENT_STYLES[activity.subagent || ""];
        const color = subagentStyle ? colors[subagentStyle.colorKey] : colors.primary;
        return {
          icon: <span style={{ fontSize: typography.sizes.sm }}>{subagentStyle?.icon || "🤖"}</span>,
          label: `Delegating to ${subagentStyle?.name || activity.subagent || "specialist"}`,
          color,
          bgColor: `${color}08`,
        };
      }
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

        {/* Optional message */}
        {activity.message && (
          <div
            style={{
              fontSize: typography.sizes.xs,
              color: colors.textSecondary,
              lineHeight: 1.4,
            }}
          >
            {activity.message}
          </div>
        )}

        {/* Planning steps */}
        {activity.type === "planning" && activity.steps && activity.steps.length > 0 && (
          <div style={{ marginTop: spacing.xs }}>
            {activity.steps.map((step, idx) => (
              <div
                key={idx}
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: spacing.xs,
                  padding: `${spacing.xs / 2}px 0`,
                  fontSize: typography.sizes.xs,
                  color: step.done ? colors.textSecondary : colors.text,
                  opacity: step.done ? 0.7 : 1,
                }}
              >
                <CheckCircleOutlined
                  style={{
                    fontSize: typography.sizes.xs,
                    color: step.done ? colors.success : colors.border,
                  }}
                />
                <span style={{ fontFamily: "system-ui, -apple-system, sans-serif" }}>
                  {step.text}
                </span>
              </div>
            ))}
          </div>
        )}
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
      case "planning":
        return { icon: <ClockCircleOutlined />, color: colors.warning };
      case "delegating":
        return { icon: <RobotOutlined />, color: colors.primary };
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
        {item.activity.toolName || item.activity.message || item.activity.type}
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
  const { spacing } = useThemeTokens();
  const screens = Grid.useBreakpoint();
  const isMobile = !screens.md; // md breakpoint is 768px

  // Hover state for history expansion
  const [isHovered, setIsHovered] = useState(false);

  // Use passed history or empty array
  const activityHistory = propActivityHistory;

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
        `}
      </style>

      <div
        style={{
          background: token.colorBgLayout,
          borderTop: `1px solid ${token.colorBorderSecondary}`,
          borderBottom: `1px solid ${token.colorBorderSecondary}`,
        }}
      >
        {/* Latest activity display with hover expansion */}
        <div
          style={{
            padding: `${spacing.xs}px ${isMobile ? spacing.sm : spacing.md}px`,
            position: "relative"
          }}
          onMouseEnter={() => activityHistory.length > 0 && setIsHovered(true)}
          onMouseLeave={() => setIsHovered(false)}
        >
          <LatestActivityDisplay activity={activity} />

          {/* Activity history panel - expands on hover */}
          {activityHistory.length > 0 && (
            <div
              style={{
                maxHeight: isHovered ? "300px" : "0",
                overflowY: "auto",
                opacity: isHovered ? 1 : 0,
                transition: "max-height 0.3s ease-out, opacity 0.3s ease-out",
                marginTop: spacing.sm,
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
