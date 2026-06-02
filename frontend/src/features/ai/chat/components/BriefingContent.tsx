import { memo } from "react";
import { theme, Tag } from "antd";
import { FileTextOutlined, UserOutlined } from "@ant-design/icons";
import { useThemeTokens } from "@/hooks/useThemeTokens";
import { MarkdownRenderer } from "./MarkdownRenderer";
import { PlanStepIndicator } from "./PlanStepIndicator";
import type { PlanStep } from "../types";

export interface BriefingState {
  markdown: string;
  completedSpecialists: string[];
  lastSpecialist: string;
  /** Execution plan with live step status — null if no plan was created */
  plan: {
    steps: PlanStep[];
    totalSteps: number;
    completedSteps: number;
    complexity: "simple" | "moderate" | "complex";
  } | null;
}

export const BRIEFING_KEYFRAMES = `
@keyframes briefing-pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.6; }
}
`;

const MONO_FONT =
  "'JetBrains Mono', 'SF Mono', 'Fira Code', monospace";

export const SpecialistBadge = memo(
  ({ name, completed }: { name: string; completed: boolean }) => {
    const { token } = theme.useToken();
    return (
      <Tag
        icon={<UserOutlined />}
        color={completed ? token.colorSuccess : undefined}
        style={{
          fontSize: 11,
          borderRadius: 4,
          fontFamily: MONO_FONT,
        }}
      >
        {name.replace(/_/g, " ")}
      </Tag>
    );
  },
);
SpecialistBadge.displayName = "SpecialistBadge";

interface BriefingContentProps {
  briefing: BriefingState;
  isStreaming: boolean;
  maxHeight?: number | "none";
}

export const BriefingContent = memo(
  ({ briefing, isStreaming, maxHeight = "none" }: BriefingContentProps) => {
    const { token } = theme.useToken();
    const { spacing, colors } = useThemeTokens();

    const completedCount = briefing.completedSpecialists.length;

    return (
      <>
        <style>{BRIEFING_KEYFRAMES}</style>
        <style>{`
          .briefing-scroll::-webkit-scrollbar {
            width: 4px;
          }
          .briefing-scroll::-webkit-scrollbar-thumb {
            background: ${token.colorBorderSecondary};
            border-radius: 2px;
          }
        `}</style>

        <div>
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: spacing.xs,
              padding: spacing.xs,
            }}
          >
            <FileTextOutlined
              style={{
                fontSize: 13,
                color: isStreaming ? token.colorPrimary : colors.textSecondary,
                ...(isStreaming && {
                  animation: "briefing-pulse 1.5s infinite",
                }),
              }}
            />
            <span
              style={{
                fontFamily: MONO_FONT,
                fontSize: 11,
                textTransform: "uppercase" as const,
                letterSpacing: "0.5px",
                color: colors.textSecondary,
              }}
            >
              Briefing & Planning
              {completedCount > 0 && (
                <span style={{ opacity: 0.7, marginLeft: 6 }}>
                  {completedCount} specialist{completedCount !== 1 ? "s" : ""}
                </span>
              )}
            </span>

            <span
              style={{
                display: "flex",
                gap: 4,
                marginLeft: "auto",
                overflow: "hidden",
              }}
            >
              {briefing.completedSpecialists.slice(0, 3).map((name) => (
                <SpecialistBadge key={name} name={name} completed={true} />
              ))}
              {briefing.completedSpecialists.length > 3 && (
                <span style={{ fontSize: 10, opacity: 0.6 }}>
                  +{briefing.completedSpecialists.length - 3}
                </span>
              )}
            </span>
          </div>

          <div
            className="briefing-scroll"
            style={{
              maxHeight: maxHeight === "none" ? undefined : maxHeight,
              overflowY: maxHeight === "none" ? undefined : "auto",
              padding: `${spacing.xs}px 0 ${spacing.md}px`,
              borderTop: `1px solid ${colors.borderSecondary}`,
            }}
          >
            {briefing.plan && (
              <PlanStepIndicator
                steps={briefing.plan.steps}
                totalSteps={briefing.plan.totalSteps}
                completedSteps={briefing.plan.completedSteps}
                complexity={briefing.plan.complexity}
                isStreaming={isStreaming}
              />
            )}
            <div
              style={{
                fontSize: 12,
                lineHeight: 1.6,
                color: colors.text,
              }}
            >
              <MarkdownRenderer
                content={briefing.markdown}
                isStreaming={false}
              />
            </div>
          </div>
        </div>
      </>
    );
  },
);
BriefingContent.displayName = "BriefingContent";
