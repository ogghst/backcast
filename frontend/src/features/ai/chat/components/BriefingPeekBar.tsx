import { memo, CSSProperties } from "react";
import { theme } from "antd";
import {
  FileTextOutlined,
  DownOutlined,
  CloseOutlined,
} from "@ant-design/icons";
import { useThemeTokens } from "@/hooks/useThemeTokens";
import { MarkdownRenderer } from "./MarkdownRenderer";
import { BriefingSectionCard } from "./BriefingSectionCard";
import {
  BriefingState,
  SpecialistBadge,
  BRIEFING_KEYFRAMES,
} from "./BriefingContent";
import { PlanStepIndicator } from "./PlanStepIndicator";

interface BriefingPeekBarProps {
  briefing: BriefingState | null;
  isStreaming: boolean;
  isOpen: boolean;
  onToggle: () => void;
}

const PEEK_BAR_HEIGHT = 44;
const SHEET_HEIGHT_VH = 60;
const DRAG_HANDLE_WIDTH = 40;
const DRAG_HANDLE_HEIGHT = 4;

const MONO_FONT =
  "'JetBrains Mono', 'SF Mono', 'Fira Code', monospace";

export const BriefingPeekBar = memo(
  ({ briefing, isStreaming, isOpen, onToggle }: BriefingPeekBarProps) => {
    const { token } = theme.useToken();
    const { spacing, borderRadius } = useThemeTokens();

    if (!briefing) return null;

    const specialistCount = briefing.completedSpecialists.length;
    const lastSpecialist = briefing.lastSpecialist
      ? briefing.lastSpecialist.replace(/_/g, " ")
      : "";
    const lastSpecialistPreview =
      lastSpecialist.length > 10
        ? lastSpecialist.slice(0, 10) + "…"
        : lastSpecialist;

    const peekBarStyle: CSSProperties = {
      height: PEEK_BAR_HEIGHT,
      minHeight: PEEK_BAR_HEIGHT,
      display: "flex",
      alignItems: "center",
      padding: `0 ${spacing.sm}px`,
      background: token.colorBgLayout,
      borderTop: `1px solid ${token.colorBorderSecondary}`,
      cursor: "pointer",
      gap: spacing.xs,
      fontFamily: MONO_FONT,
      fontSize: 11,
      textTransform: "uppercase" as const,
      letterSpacing: "0.5px",
      color: token.colorTextSecondary,
      userSelect: "none",
    };

    const badgeStyle: CSSProperties = {
      display: "inline-flex",
      alignItems: "center",
      justifyContent: "center",
      minWidth: 18,
      height: 18,
      borderRadius: "50%",
      background: token.colorPrimary,
      color: "#fff",
      fontSize: 10,
      fontWeight: 600,
      padding: "0 4px",
    };

    const dragHandleStyle: CSSProperties = {
      width: DRAG_HANDLE_WIDTH,
      height: DRAG_HANDLE_HEIGHT,
      background: token.colorTextTertiary,
      opacity: 0.4,
      borderRadius: 2,
      margin: `${spacing.xs}px auto`,
    };

    const sheetHeaderStyle: CSSProperties = {
      display: "flex",
      alignItems: "center",
      padding: `0 ${spacing.md}px`,
      height: 36,
      gap: spacing.sm,
      fontFamily: MONO_FONT,
      fontSize: 11,
      textTransform: "uppercase" as const,
      letterSpacing: "0.5px",
      color: token.colorTextSecondary,
    };

    const badgesRowStyle: CSSProperties = {
      display: "flex",
      flexWrap: "wrap" as const,
      gap: 4,
      padding: `0 ${spacing.md}px ${spacing.sm}px`,
    };

    const scrollAreaStyle: CSSProperties = {
      flex: 1,
      overflowY: "auto",
      padding: `0 ${spacing.md}px ${spacing.md}px`,
    };

    return (
      <>
        <style>{BRIEFING_KEYFRAMES}</style>
        <style>{`
          .briefing-peek-scroll::-webkit-scrollbar {
            width: 4px;
          }
          .briefing-peek-scroll::-webkit-scrollbar-thumb {
            background: ${token.colorBorderSecondary};
            border-radius: 2px;
          }
        `}</style>

        {!isOpen && (
          <button
            type="button"
            onClick={onToggle}
            style={peekBarStyle}
            aria-expanded={false}
            aria-label="Expand briefing"
          >
            <FileTextOutlined
              style={{
                fontSize: 13,
                color: isStreaming ? token.colorPrimary : token.colorTextSecondary,
                ...(isStreaming && {
                  animation: "briefing-pulse 1.5s infinite",
                }),
              }}
            />

            <span style={{ flex: 1, textAlign: "left" }}>Briefing & Planning</span>

            {isStreaming && (
              <span
                style={{
                  width: 6,
                  height: 6,
                  borderRadius: "50%",
                  background: token.colorPrimary,
                  animation: "briefing-pulse 1.5s infinite",
                }}
              />
            )}

            {briefing.plan ? (
              <span
                style={{
                  ...badgeStyle,
                  minWidth: 28,
                  padding: "0 5px",
                  borderRadius: 9,
                  fontSize: 9,
                }}
              >
                {briefing.plan.completedSteps}/{briefing.plan.totalSteps}
              </span>
            ) : (
              specialistCount > 0 && (
                <span style={badgeStyle}>{specialistCount}</span>
              )
            )}

            {lastSpecialistPreview && (
              <span
                style={{
                  opacity: 0.7,
                  maxWidth: 80,
                  overflow: "hidden",
                  textOverflow: "ellipsis",
                  whiteSpace: "nowrap",
                  fontWeight: 400,
                }}
              >
                {lastSpecialistPreview}
              </span>
            )}

            <span style={{ marginLeft: "auto", display: "flex" }}>
              {briefing.plan ? (
                <span style={{ opacity: 0.5, marginRight: spacing.xs }}>
                  {briefing.plan.completedSteps}/{briefing.plan.totalSteps} steps |
                </span>
              ) : (
                specialistCount > 0 && (
                  <span style={{ opacity: 0.5, marginRight: spacing.xs }}>
                    specialist{specialistCount !== 1 ? "s" : ""} |
                  </span>
                )
              )}
              <DownOutlined style={{ fontSize: 10 }} />
            </span>
          </button>
        )}

        {isOpen && (
          <div
            style={{
              height: `${SHEET_HEIGHT_VH}vh`,
              background: token.colorBgContainer,
              borderTop: `1px solid ${token.colorBorderSecondary}`,
              borderRadius: `${borderRadius.xl}px ${borderRadius.xl}px 0 0`,
              boxShadow: "0 -4px 12px rgba(0,0,0,0.1)",
              display: "flex",
              flexDirection: "column",
              overflow: "hidden",
            }}
          >
            <div style={dragHandleStyle} />
            <div style={sheetHeaderStyle}>
              <FileTextOutlined
                style={{
                  fontSize: 13,
                  color: isStreaming
                    ? token.colorPrimary
                    : token.colorTextSecondary,
                  ...(isStreaming && {
                    animation: "briefing-pulse 1.5s infinite",
                  }),
                }}
              />
              <span style={{ flex: 1 }}>Briefing & Planning</span>
              <button
                type="button"
                onClick={onToggle}
                style={{
                  background: "transparent",
                  border: "none",
                  cursor: "pointer",
                  color: token.colorTextSecondary,
                  display: "flex",
                  alignItems: "center",
                  padding: spacing.xs,
                }}
                aria-label="Collapse briefing"
              >
                <CloseOutlined style={{ fontSize: 12 }} />
              </button>
            </div>
            {briefing.completedSpecialists.length > 0 && (
              <div style={badgesRowStyle}>
                {briefing.completedSpecialists.map((name) => (
                  <SpecialistBadge
                    key={name}
                    name={name}
                    completed={true}
                  />
                ))}
              </div>
            )}
            {briefing.plan && (
              <div style={{ padding: `0 ${spacing.md}px ${spacing.xs}px` }}>
                <PlanStepIndicator
                  steps={briefing.plan.steps}
                  totalSteps={briefing.plan.totalSteps}
                  completedSteps={briefing.plan.completedSteps}
                  complexity={briefing.plan.complexity}
                  isStreaming={isStreaming}
                />
              </div>
            )}
            <div
              className="briefing-peek-scroll"
              style={scrollAreaStyle}
            >
              <div
                style={{
                  fontSize: 12,
                  lineHeight: 1.6,
                  color: token.colorText,
                }}
              >
                {briefing.document?.sections.length ? (
                  briefing.document.sections.map((section) => (
                    <BriefingSectionCard
                      key={`${section.specialist_name}-${section.step_index ?? 0}`}
                      section={section}
                      isStreaming={isStreaming && section.specialist_name === briefing.lastSpecialist}
                    />
                  ))
                ) : (
                  <MarkdownRenderer
                    content={briefing.markdown}
                    isStreaming={isStreaming}
                  />
                )}
              </div>
            </div>
          </div>
        )}
      </>
    );
  },
);

BriefingPeekBar.displayName = "BriefingPeekBar";
