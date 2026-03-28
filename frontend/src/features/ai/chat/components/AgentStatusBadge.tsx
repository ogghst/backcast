/**
 * AgentStatusBadge Component
 *
 * Compact status indicator showing the current Deep Agent activity.
 * Displays only the latest update (not history) with industrial-technical aesthetic.
 *
 * States:
 * - thinking: Agent is processing
 * - planning: Agent is creating a plan
 * - delegating: Agent has delegated to a subagent
 * - executing: Agent is running a tool
 */

import { memo } from "react";
import { RobotOutlined, ClockCircleOutlined, ThunderboltOutlined } from "@ant-design/icons";
import { useThemeTokens } from "@/hooks/useThemeTokens";

import type { AgentActivity } from "./AgentActivityPanel";

// Subagent display names - colors will be applied from theme
const SUBAGENT_STYLES: Record<string, { name: string; icon: string; colorKey: keyof ReturnType<typeof useThemeTokens>['colors'] }> = {
  evm_analyst: { name: "EVM Analyst", icon: "📊", colorKey: "info" },
  change_order_manager: { name: "Change Order", icon: "📋", colorKey: "warning" },
  forecast_analyst: { name: "Forecast", icon: "📈", colorKey: "success" },
  project_admin: { name: "Project Admin", icon: "📁", colorKey: "primary" },
  advanced_analyst: { name: "Advanced Analyst", icon: "🔬", colorKey: "error" },
};

interface AgentStatusBadgeProps {
  /** Current agent activity (latest only) */
  activity: AgentActivity | null;
  /** Whether to show compact mode (for smaller screens) */
  compact?: boolean;
}

/**
 * Get display configuration for an activity type
 */
function getActivityConfig(activity: AgentActivity, colors: ReturnType<typeof useThemeTokens>['colors']) {
  switch (activity.type) {
    case "planning":
      return {
        icon: <ClockCircleOutlined />,
        label: "Planning",
        color: colors.warning,
        bgGradient: `linear-gradient(135deg, ${colors.warning}20 0%, ${colors.warning}10 100%)`,
      };
    case "delegating": {
      const subagentStyle = SUBAGENT_STYLES[activity.subagent || ""] || {
        name: activity.subagent || "Specialist",
        icon: "🤖",
        colorKey: "primary" as const,
      };
      const color = colors[subagentStyle.colorKey];
      return {
        icon: <span style={{ fontSize: 12 }}>{subagentStyle.icon}</span>,
        label: subagentStyle.name,
        message: activity.message,
        color,
        bgGradient: `linear-gradient(135deg, ${color}20 0%, ${color}10 100%)`,
      };
    }
    case "executing":
      return {
        icon: <ThunderboltOutlined />,
        label: activity.toolName ? `${activity.toolName}` : "Executing",
        color: colors.info,
        bgGradient: `linear-gradient(135deg, ${colors.info}20 0%, ${colors.info}10 100%)`,
      };
    default: // thinking
      return {
        icon: <RobotOutlined />,
        label: "Thinking",
        color: colors.textSecondary,
        bgGradient: `linear-gradient(135deg, ${colors.textSecondary}15 0%, ${colors.textSecondary}08 100%)`,
      };
  }
}

/**
 * Animated dots for active states
 */
function LoadingDots({ color }: { color: string }) {
  return (
    <span style={{ display: "inline-flex", gap: 3, marginLeft: 6, alignItems: "center" }}>
      <span
        style={{
          width: 4,
          height: 4,
          borderRadius: "50%",
          background: color,
          animation: "dot-flash 1.4s infinite ease-in-out both",
        }}
      />
      <span
        style={{
          width: 4,
          height: 4,
          borderRadius: "50%",
          background: color,
          animation: "dot-flash 1.4s infinite ease-in-out both 0.2s",
        }}
      />
      <span
        style={{
          width: 4,
          height: 4,
          borderRadius: "50%",
          background: color,
          animation: "dot-flash 1.4s infinite ease-in-out both 0.4s",
        }}
      />
    </span>
  );
}

export const AgentStatusBadge = memo(({ activity, compact = false }: AgentStatusBadgeProps) => {
  const { spacing, typography, colors, borderRadius } = useThemeTokens();

  if (!activity) {
    return null;
  }

  const config = getActivityConfig(activity, colors);

  return (
    <>
      <style>
        {`
          @keyframes dot-flash {
            0% { opacity: 0.3; transform: scale(0.8); }
            50% { opacity: 1; transform: scale(1); }
            100% { opacity: 0.3; transform: scale(0.8); }
          }

          @keyframes status-pulse {
            0%, 100% { box-shadow: 0 0 0 0 ${config.color}40; }
            50% { box-shadow: 0 0 0 4px ${config.color}20; }
          }

          @keyframes slide-in {
            from {
              opacity: 0;
              transform: translateY(-8px) scale(0.95);
            }
            to {
              opacity: 1;
              transform: translateY(0) scale(1);
            }
          }
        `}
      </style>

      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: compact ? spacing.xs : spacing.sm,
          padding: compact ? `${spacing.xs}px ${spacing.sm + spacing.xs}px` : `${spacing.xs}px ${spacing.md}px`,
          background: config.bgGradient,
          border: `1px solid ${config.color}40`,
          borderRadius: compact ? borderRadius.xl : borderRadius.lg,
          animation: "slide-in 0.3s cubic-bezier(0.4, 0, 0.2, 1), status-pulse 2s ease-in-out infinite",
          maxWidth: compact ? 180 : 280,
        }}
      >
        {/* Icon */}
        <div
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            width: compact ? 18 : 22,
            height: compact ? 18 : 22,
            borderRadius: "50%",
            background: config.color,
            color: "#fff",
            fontSize: compact ? typography.sizes.xs : typography.sizes.sm,
            flexShrink: 0,
          }}
        >
          {config.icon}
        </div>

        {/* Label */}
        <span
          style={{
            fontSize: compact ? typography.sizes.xs : typography.sizes.sm,
            fontWeight: typography.weights.semiBold,
            color: config.color,
            fontFamily: '"JetBrains Mono", "SF Mono", monospace',
            textTransform: "uppercase",
            letterSpacing: "0.5px",
            whiteSpace: "nowrap",
          }}
        >
          {config.label}
        </span>

        {/* Loading dots for active states */}
        {activity.type === "thinking" || activity.type === "executing" ? (
          <LoadingDots color={config.color} />
        ) : null}

        {/* Optional message for subagent delegation (non-compact only) */}
        {!compact && activity.type === "delegating" && config.message && (
          <span
            style={{
              fontSize: typography.sizes.xs,
              color: colors.textSecondary,
              maxWidth: 120,
              overflow: "hidden",
              textOverflow: "ellipsis",
              whiteSpace: "nowrap",
            }}
          >
            {config.message}
          </span>
        )}
      </div>
    </>
  );
});

AgentStatusBadge.displayName = "AgentStatusBadge";
