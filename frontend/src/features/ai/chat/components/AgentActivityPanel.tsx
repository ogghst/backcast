/**
 * AgentActivityPanel Component
 *
 * Visualizes Deep Agent's latest planning, subagent delegation, and tool execution.
 * Displays only the most recent activity with distinctive industrial-technical aesthetic.
 *
 * Features:
 * - Planning phase visualization (write_todos)
 * - Active subagent indicator
 * - Tool execution progress
 * - Animated state transitions
 */

import { memo, useEffect, useState } from "react";
import { ClockCircleOutlined, RobotOutlined, ThunderboltOutlined, CheckCircleOutlined } from "@ant-design/icons";
import { theme } from "antd";
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
  currentStep?: number;
  totalSteps?: number;
  timestamp: number;
}

interface AgentActivityPanelProps {
  /** Current agent activity (latest only) */
  activity: AgentActivity | null;
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
 * Latest activity display component with animations
 */
const LatestActivityDisplay = memo(({ activity }: { activity: AgentActivity }) => {
  const { token } = theme.useToken();
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
          bgGradient: `linear-gradient(135deg, ${colors.warning}15 0%, ${colors.warning}08 100%)`,
        };
      case "delegating": {
        const subagentStyle = SUBAGENT_STYLES[activity.subagent || ""];
        const color = subagentStyle ? colors[subagentStyle.colorKey] : colors.primary;
        return {
          icon: <span style={{ fontSize: typography.sizes.md }}>{subagentStyle?.icon || "🤖"}</span>,
          label: `Delegating to ${subagentStyle?.name || activity.subagent || "specialist"}`,
          color,
          bgGradient: `linear-gradient(135deg, ${color}15 0%, ${color}08 100%)`,
        };
      }
      case "executing": {
        const stepText = activity.currentStep && activity.totalSteps
          ? `Step ${activity.currentStep} of ${activity.totalSteps}`
          : null;
        const label = activity.toolName
          ? (stepText ? `${activity.toolName} • ${stepText}` : `Running ${activity.toolName}`)
          : (stepText || "Executing tool");

        return {
          icon: <ThunderboltOutlined />,
          label,
          color: colors.info,
          bgGradient: `linear-gradient(135deg, ${colors.info}15 0%, ${colors.info}08 100%)`,
        };
      }
      default: // thinking
        return {
          icon: <RobotOutlined />,
          label: "Thinking",
          color: colors.textSecondary,
          bgGradient: `linear-gradient(135deg, ${colors.textSecondary}15 0%, ${colors.textSecondary}08 100%)`,
        };
      }
  };

  const config = getActivityConfig();

  return (
    <div
      style={{
        display: "flex",
        alignItems: "flex-start",
        gap: spacing.md,
        padding: `${spacing.md}px ${spacing.lg}px`,
        background: config.bgGradient,
        borderLeft: `3px solid ${config.color}`,
        borderRadius: borderRadius.lg,
        opacity: isVisible ? 1 : 0,
        transform: isVisible ? "translateX(0)" : "translateX(-10px)",
        transition: "all 0.3s cubic-bezier(0.4, 0, 0.2, 1)",
      }}
    >
      {/* Icon with pulsing animation for active states */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          width: 28,
          height: 28,
          borderRadius: "50%",
          background: config.color,
          color: "#fff",
          fontSize: typography.sizes.md,
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
            gap: spacing.sm,
            marginBottom: activity.type === "planning" && activity.steps ? spacing.sm : 0,
          }}
        >
          <span
            style={{
              fontSize: typography.sizes.sm,
              fontWeight: typography.weights.semiBold,
              color: config.color,
              fontFamily: '"JetBrains Mono", "SF Mono", monospace',
              textTransform: "uppercase",
              letterSpacing: "0.5px",
            }}
          >
            {config.label}
          </span>

          {/* Loading dots for active states */}
          {activity.type === "thinking" || activity.type === "executing" ? (
            <span style={{ display: "flex", gap: 3, marginLeft: spacing.xs }}>
              <span
                style={{
                  width: 4,
                  height: 4,
                  borderRadius: "50%",
                  background: config.color,
                  animation: "dot-flashing 1.4s infinite ease-in-out both",
                }}
              />
              <span
                style={{
                  width: 4,
                  height: 4,
                  borderRadius: "50%",
                  background: config.color,
                  animation: "dot-flashing 1.4s infinite ease-in-out both 0.2s",
                }}
              />
              <span
                style={{
                  width: 4,
                  height: 4,
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
              fontSize: typography.sizes.sm,
              color: colors.textSecondary,
              lineHeight: 1.5,
            }}
          >
            {activity.message}
          </div>
        )}

        {/* Progress bar for executing state with steps */}
        {activity.type === "executing" && activity.currentStep && activity.totalSteps && (
          <div style={{ marginTop: spacing.sm }}>
            <div
              style={{
                display: "flex",
                alignItems: "center",
                gap: spacing.sm,
                fontSize: typography.sizes.xs,
                fontFamily: '"JetBrains Mono", monospace',
                color: colors.textSecondary,
                marginBottom: spacing.xs,
              }}
            >
              <span>Progress</span>
              <span style={{ marginLeft: "auto" }}>
                {Math.round((activity.currentStep / activity.totalSteps) * 100)}%
              </span>
            </div>
            <div
              style={{
                width: "100%",
                height: 4,
                backgroundColor: token.colorBorderSecondary,
                borderRadius: borderRadius.sm,
                overflow: "hidden",
              }}
            >
              <div
                style={{
                  width: `${(activity.currentStep / activity.totalSteps) * 100}%`,
                  height: "100%",
                  backgroundColor: config.color,
                  transition: "width 0.3s ease-out",
                }}
              />
            </div>
          </div>
        )}

        {/* Planning steps */}
        {activity.type === "planning" && activity.steps && activity.steps.length > 0 && (
          <div style={{ marginTop: spacing.sm }}>
            {activity.steps.map((step, idx) => (
              <div
                key={idx}
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: spacing.sm,
                  padding: `${spacing.xs}px 0`,
                  fontSize: typography.sizes.sm,
                  color: step.done ? colors.textSecondary : colors.text,
                  opacity: step.done ? 0.7 : 1,
                }}
              >
                <CheckCircleOutlined
                  style={{
                    fontSize: typography.sizes.sm,
                    color: step.done ? colors.success : colors.border,
                  }}
                />
                <span style={{ fontFamily: '"Inter", system-ui, sans-serif' }}>
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
 * Main AgentActivityPanel component - shows only the latest activity
 */
export const AgentActivityPanel = memo(({ activity }: AgentActivityPanelProps) => {
  const { token } = theme.useToken();
  const { spacing, typography, colors } = useThemeTokens();

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
        {/* Header */}
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: spacing.sm,
            padding: `${spacing.md}px ${spacing.lg}px ${spacing.sm}px ${spacing.lg}px`,
          }}
        >
          <RobotOutlined style={{ color: token.colorPrimary, fontSize: typography.sizes.md }} />
          <span
            style={{
              fontSize: typography.sizes.xs,
              fontWeight: typography.weights.semiBold,
              fontFamily: '"JetBrains Mono", monospace',
              textTransform: "uppercase",
              letterSpacing: "1px",
              color: colors.textSecondary,
            }}
          >
            Latest Activity
          </span>
        </div>

        {/* Latest activity display */}
        <div style={{ padding: `0 ${spacing.lg}px ${spacing.md}px ${spacing.lg}px` }}>
          <LatestActivityDisplay activity={activity} />
        </div>
      </div>
    </>
  );
});

AgentActivityPanel.displayName = "AgentActivityPanel";
