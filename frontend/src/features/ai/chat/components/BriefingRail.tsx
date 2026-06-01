import { memo, useCallback, useRef, useEffect } from "react";
import { theme } from "antd";
import { FileTextOutlined, LeftOutlined } from "@ant-design/icons";
import { useThemeTokens } from "@/hooks/useThemeTokens";
import { MarkdownRenderer } from "./MarkdownRenderer";
import {
  BriefingState,
  SpecialistBadge,
  BRIEFING_KEYFRAMES,
} from "./BriefingContent";
import { PlanStepIndicator } from "./PlanStepIndicator";

interface BriefingRailProps {
  briefing: BriefingState | null;
  isStreaming: boolean;
  isOpen: boolean;
  onClose: () => void;
  width: number;
  onWidthChange: (width: number) => void;
}

const MONO_FONT = "'JetBrains Mono', 'SF Mono', 'Fira Code', monospace";

const MIN_WIDTH = 280;

export const BriefingRail = memo(
  ({
    briefing,
    isStreaming,
    isOpen,
    onClose,
    width,
    onWidthChange,
  }: BriefingRailProps) => {
    const { token } = theme.useToken();
    const { spacing, colors } = useThemeTokens();
    const isDragging = useRef(false);
    const railRef = useRef<HTMLDivElement>(null);

    const maxViewportWidth = useCallback(
      () => Math.floor(window.innerWidth * 0.5),
      [],
    );

    const handleMouseDown = useCallback(
      (e: React.MouseEvent) => {
        e.preventDefault();
        isDragging.current = true;
        const startX = e.clientX;
        const startWidth = width;

        const onMouseMove = (ev: MouseEvent) => {
          if (!isDragging.current) return;
          const dx = startX - ev.clientX;
          const nextWidth = Math.max(
            MIN_WIDTH,
            Math.min(maxViewportWidth(), startWidth + dx),
          );
          requestAnimationFrame(() => onWidthChange(nextWidth));
        };

        const onMouseUp = () => {
          isDragging.current = false;
          document.removeEventListener("mousemove", onMouseMove);
          document.removeEventListener("mouseup", onMouseUp);
          document.body.style.cursor = "";
          document.body.style.userSelect = "";
        };

        document.body.style.cursor = "col-resize";
        document.body.style.userSelect = "none";
        document.addEventListener("mousemove", onMouseMove);
        document.addEventListener("mouseup", onMouseUp);
      },
      [width, onWidthChange, maxViewportWidth],
    );

    useEffect(() => {
      return () => {
        document.body.style.cursor = "";
        document.body.style.userSelect = "";
      };
    }, []);

    if (!isOpen) return null;

    return (
      <>
        <style>{BRIEFING_KEYFRAMES}</style>
        <style>{`
          .briefing-rail-scroll::-webkit-scrollbar {
            width: 4px;
          }
          .briefing-rail-scroll::-webkit-scrollbar-thumb {
            background: ${token.colorBorderSecondary};
            border-radius: 2px;
          }
        `}</style>

        <div
          ref={railRef}
          style={{
            position: "relative",
            display: "flex",
            flexDirection: "column",
            height: "100%",
            width,
            minWidth: MIN_WIDTH,
            maxWidth: maxViewportWidth(),
            borderLeft: `1px solid ${token.colorBorderSecondary}`,
            background: token.colorBgContainer,
            flexShrink: 0,
          }}
        >
          {/* Resize handle */}
          <div
            role="separator"
            aria-orientation="vertical"
            aria-valuenow={width}
            aria-valuemin={MIN_WIDTH}
            aria-valuemax={maxViewportWidth()}
            onMouseDown={handleMouseDown}
            style={{
              position: "absolute",
              top: 0,
              left: 0,
              bottom: 0,
              width: 6,
              cursor: "col-resize",
              zIndex: 1,
              transition: "background 0.15s",
            }}
            onMouseEnter={(e) => {
              (e.currentTarget as HTMLDivElement).style.background = `${token.colorPrimary}33`;
            }}
            onMouseLeave={(e) => {
              if (!isDragging.current) {
                (e.currentTarget as HTMLDivElement).style.background = "transparent";
              }
            }}
          />

          {/* Header */}
          <div
            style={{
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between",
              padding: `${spacing.sm}px ${spacing.sm}px ${spacing.xs}px`,
              borderBottom: `1px solid ${token.colorBorderSecondary}`,
              flexShrink: 0,
            }}
          >
            <div style={{ display: "flex", alignItems: "center", gap: spacing.xs }}>
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
              </span>
            </div>

            <button
              type="button"
              onClick={onClose}
              style={{
                display: "flex",
                alignItems: "center",
                gap: 4,
                background: "transparent",
                border: "none",
                cursor: "pointer",
                color: colors.textTertiary,
                fontSize: 11,
                padding: `${spacing.xs}px`,
                borderRadius: token.borderRadiusSM,
                fontFamily: MONO_FONT,
              }}
            >
              <LeftOutlined style={{ fontSize: 10 }} />
            </button>
          </div>

          {/* Specialist badges row */}
          {briefing && briefing.completedSpecialists.length > 0 && (
            <div
              style={{
                display: "flex",
                flexWrap: "wrap",
                gap: 4,
                padding: `${spacing.xs}px ${spacing.sm}px`,
                borderBottom: `1px solid ${token.colorBorderSecondary}`,
                flexShrink: 0,
              }}
            >
              {briefing.completedSpecialists.map((name) => (
                <SpecialistBadge key={name} name={name} completed={true} />
              ))}
            </div>
          )}

          {/* Plan step indicator */}
          {briefing?.plan && (
            <div
              style={{
                padding: `${spacing.xs}px ${spacing.sm}px`,
                borderBottom: `1px solid ${token.colorBorderSecondary}`,
                flexShrink: 0,
              }}
            >
              <PlanStepIndicator
                steps={briefing.plan.steps}
                totalSteps={briefing.plan.totalSteps}
                completedSteps={briefing.plan.completedSteps}
                complexity={briefing.plan.complexity}
                isStreaming={isStreaming}
              />
            </div>
          )}

          {/* Content */}
          <div
            className="briefing-rail-scroll"
            style={{
              flex: 1,
              overflowY: "auto",
              padding: `${spacing.xs}px ${spacing.xs}px ${spacing.md}px`,
            }}
          >
            {briefing ? (
              <div
                style={{
                  fontSize: 12,
                  lineHeight: 1.6,
                  color: token.colorText,
                }}
              >
                <MarkdownRenderer
                  content={briefing.markdown}
                  isStreaming={false}
                />
              </div>
            ) : (
              <div
                style={{
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  height: "100%",
                  color: colors.textTertiary,
                  fontSize: 12,
                  fontFamily: MONO_FONT,
                }}
              >
                No briefing available
              </div>
            )}
          </div>
        </div>
      </>
    );
  },
);

BriefingRail.displayName = "BriefingRail";
