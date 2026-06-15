import { memo } from "react";
import { theme } from "antd";
import { ScheduleOutlined } from "@ant-design/icons";
import { useThemeTokens } from "@/hooks/useThemeTokens";
import type { PlanStep } from "../types";

const MONO_FONT = "'JetBrains Mono', 'SF Mono', 'Fira Code', monospace";

export const PLAN_STEP_KEYFRAMES = `
@keyframes step-pulse {
  0%, 100% { opacity: 1; transform: scale(1); }
  50% { opacity: 0.5; transform: scale(1.15); }
}
`;

function getStatusColor(
  status: PlanStep["status"],
  colors: ReturnType<typeof useThemeTokens>["colors"],
  token: ReturnType<typeof theme.useToken>["token"],
): string {
  switch (status) {
    case "completed":
      return colors.success;
    case "in_progress":
      return token.colorPrimary;
    case "failed":
      return colors.error;
    case "skipped":
    case "pending":
    default:
      return colors.textTertiary;
  }
}

interface PlanStepIndicatorProps {
  steps: PlanStep[];
  totalSteps: number;
  completedSteps: number;
  complexity: "simple" | "moderate" | "complex";
  isStreaming: boolean;
}

/**
 * Displays execution plan steps with live status updates inside the briefing rail/panel.
 * Shows a vertical timeline for multi-step plans, or a single compact line for simple plans.
 */
export const PlanStepIndicator = memo(
  ({
    steps,
    totalSteps,
    completedSteps: completedStepsProp,
    complexity,
    isStreaming,
  }: PlanStepIndicatorProps) => {
    const { token } = theme.useToken();
    const { spacing, colors, borderRadius } = useThemeTokens();

    // Derive completedSteps from step statuses as the primary source.
    // This ensures the counter always matches the rendered step states,
    // even if the parent's completedSteps prop is stale or zero.
    const completedSteps = steps.filter(
      (s) => s.status === "completed",
    ).length || completedStepsProp;

    // Single-step compact render
    if (steps.length === 1) {
      const step = steps[0];
      const statusColor = getStatusColor(step.status, colors, token);
      return (
        <>
          <style>{PLAN_STEP_KEYFRAMES}</style>
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: spacing.xs,
              padding: `${spacing.xs}px 0`,
            }}
          >
            <span
              style={{
                color: statusColor,
                fontSize: 10,
                lineHeight: 1,
                ...(step.status === "in_progress" && {
                  animation: "step-pulse 1.5s infinite",
                }),
              }}
            >
              {step.status === "completed"
                ? "●"
                : step.status === "in_progress"
                  ? "●"
                  : step.status === "failed"
                    ? "●"
                    : step.status === "skipped"
                      ? "◌"
                      : "○"}
            </span>
            <span
              style={{
                fontFamily: MONO_FONT,
                fontSize: 11,
                textTransform: "uppercase",
                letterSpacing: "0.5px",
                color: colors.textSecondary,
                flex: 1,
              }}
            >
              {step.specialist.replace(/_/g, " ")}
            </span>
            {step.result_summary && (
              <span
                style={{
                  fontSize: 11,
                  color: colors.textTertiary,
                  overflow: "hidden",
                  textOverflow: "ellipsis",
                  whiteSpace: "nowrap",
                  maxWidth: 120,
                }}
              >
                {step.result_summary}
              </span>
            )}
          </div>
        </>
      );
    }

    return (
      <>
        <style>{PLAN_STEP_KEYFRAMES}</style>

        {/* Header */}
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: spacing.xs,
            padding: `${spacing.xs}px 0`,
          }}
        >
          <ScheduleOutlined
            style={{
              fontSize: 13,
              color: isStreaming ? token.colorPrimary : colors.textSecondary,
              ...(isStreaming && {
                animation: "step-pulse 1.5s infinite",
              }),
            }}
          />
          <span
            style={{
              fontFamily: MONO_FONT,
              fontSize: 11,
              textTransform: "uppercase",
              letterSpacing: "0.5px",
              color: colors.textSecondary,
            }}
          >
            Plan
          </span>

          <span style={{ flex: 1 }} />

          <span
            style={{
              fontFamily: MONO_FONT,
              fontSize: 11,
              color: colors.textTertiary,
            }}
          >
            {completedSteps}/{totalSteps}
          </span>

          <span
            style={{
              fontSize: 10,
              fontFamily: MONO_FONT,
              lineHeight: "16px",
              padding: "0 5px",
              borderRadius: borderRadius.sm,
              color: "#fff",
              background:
                complexity === "simple"
                  ? colors.success
                  : complexity === "moderate"
                    ? colors.warning
                    : colors.error,
              opacity:
                complexity === "simple" ? 0.85 : complexity === "moderate" ? 0.8 : 0.85,
            }}
          >
            {complexity}
          </span>
        </div>

        {/* Divider */}
        <div
          style={{
            borderTop: `1px solid ${colors.borderSecondary}`,
            margin: `${spacing.xs / 2}px 0 ${spacing.xs}px`,
          }}
        />

        {/* Step timeline */}
        <div style={{ padding: `0 0 ${spacing.xs}px` }}>
          {steps.map((step, i) => {
            const isLast = i === steps.length - 1;
            const statusColor = getStatusColor(step.status, colors, token);
            const isCompleted = step.status === "completed";
            const isInProgress = step.status === "in_progress";
            const isReplanned = !!step.replanned;

            return (
              <div
                key={`${step.step_index}-${step.specialist}`}
                style={{ position: "relative", paddingLeft: 18 }}
              >
                {/* Connecting line */}
                {!isLast && (
                  <div
                    style={{
                      position: "absolute",
                      left: 4,
                      top: 10,
                      bottom: 0,
                      width: 1,
                      background: isCompleted ? colors.success : colors.borderSecondary,
                      transition: "background 0.3s",
                    }}
                  />
                )}

                {/* Status indicator dot */}
                <span
                  style={{
                    position: "absolute",
                    left: 0,
                    top: 3,
                    color: statusColor,
                    fontSize: 10,
                    lineHeight: 1,
                    ...(isInProgress && {
                      animation: "step-pulse 1.5s infinite",
                    }),
                    ...(step.status === "skipped" && {
                      opacity: 0.5,
                      textDecoration: "line-through",
                    }),
                    transition: "color 0.3s",
                  }}
                >
                  {step.status === "completed"
                    ? "●"
                    : step.status === "in_progress"
                      ? "●"
                      : step.status === "failed"
                        ? "●"
                        : step.status === "skipped"
                          ? "◌"
                          : "○"}
                </span>

                {/* Step content */}
                <div
                  style={{
                    paddingBottom: isLast ? 0 : spacing.xs,
                    paddingLeft: isReplanned ? spacing.xs : 0,
                    marginLeft: isReplanned ? -4 : 0,
                    borderLeft: isReplanned
                      ? `2px solid ${token.colorWarning}`
                      : "2px solid transparent",
                    borderRadius: borderRadius.sm,
                    background: isReplanned ? token.colorWarningBg : "transparent",
                    transition: "opacity 0.3s, background 0.3s",
                    opacity: step.status === "skipped" ? 0.5 : 1,
                  }}
                >
                  {/* Specialist name */}
                  <div
                    style={{
                      fontFamily: MONO_FONT,
                      fontSize: 11,
                      textTransform: "uppercase",
                      letterSpacing: "0.3px",
                      color:
                        step.status === "pending"
                          ? colors.textTertiary
                          : isCompleted
                            ? colors.success
                            : colors.textSecondary,
                      transition: "color 0.3s",
                    }}
                  >
                    {step.specialist.replace(/_/g, " ")}
                    {isCompleted && (
                      <span style={{ marginLeft: 6, opacity: 0.7 }}>&#10003;</span>
                    )}
                    {isInProgress && (
                      <span style={{ marginLeft: 6, opacity: 0.7 }}>&#10227;</span>
                    )}
                    {isReplanned && (
                      <span
                        style={{
                          marginLeft: 6,
                          color: token.colorWarning,
                          opacity: 0.9,
                        }}
                        title="Step added or revised by replan"
                      >
                        &#8635; replanned
                      </span>
                    )}
                  </div>

                  {/* Task description */}
                  <div
                    style={{
                      fontSize: 12,
                      lineHeight: 1.5,
                      color: colors.text,
                      display: "-webkit-box",
                      WebkitLineClamp: 2,
                      WebkitBoxOrient: "vertical",
                      overflow: "hidden",
                    }}
                  >
                    {step.task_description}
                  </div>

                  {/* Result summary for completed steps */}
                  {isCompleted && step.result_summary && (
                    <div
                      style={{
                        fontSize: 11,
                        lineHeight: 1.4,
                        color: colors.textTertiary,
                        marginTop: 2,
                        overflow: "hidden",
                        textOverflow: "ellipsis",
                        whiteSpace: "nowrap",
                      }}
                    >
                      {step.result_summary}
                    </div>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      </>
    );
  },
);

PlanStepIndicator.displayName = "PlanStepIndicator";
