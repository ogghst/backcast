import { memo, useCallback, type CSSProperties } from "react";
import { theme } from "antd";
import { FileTextOutlined } from "@ant-design/icons";
import { useThemeTokens } from "@/hooks/useThemeTokens";

interface BriefingRailToggleTabProps {
  specialistCount: number;
  /** When a plan exists, show step progress badge instead of specialist count */
  planStepBadge?: string; // e.g. "2/4"
  isStreaming: boolean;
  hasBriefing: boolean;
  onClick: () => void;
}

const MONO_FONT = "'JetBrains Mono', 'SF Mono', 'Fira Code', monospace";

export const BriefingRailToggleTab = memo(
  ({
    specialistCount,
    planStepBadge,
    isStreaming,
    hasBriefing,
    onClick,
  }: BriefingRailToggleTabProps) => {
    const { token } = theme.useToken();
    const { colors } = useThemeTokens();

    const handleKeyDown = useCallback(
      (e: React.KeyboardEvent) => {
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          onClick();
        }
      },
      [onClick],
    );

    if (!hasBriefing) return null;

    return (
      <>
        <style>{`
          @keyframes briefing-pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.6; }
          }
        `}</style>

        <div
          role="button"
          aria-expanded="false"
          aria-label="Open briefing panel"
          tabIndex={0}
          onClick={onClick}
          onKeyDown={handleKeyDown}
          style={
            {
              width: 36,
              height: "100%",
              display: "flex",
              flexDirection: "column",
              alignItems: "center",
              justifyContent: "center",
              gap: 6,
              background: token.colorBgContainer,
              borderLeft: `1px solid ${token.colorBorderSecondary}`,
              cursor: "pointer",
              transition: "background 0.2s ease",
              outline: "none",
              "--hover-bg": token.colorFillQuaternary,
              "--hover-color": token.colorText,
            } as CSSProperties
          }
          className="briefing-rail-toggle-tab"
        >
          <style>{`
            .briefing-rail-toggle-tab:hover {
              background: var(--hover-bg) !important;
            }
            .briefing-rail-toggle-tab:hover .briefing-rail-label {
              color: var(--hover-color) !important;
            }
            .briefing-rail-toggle-tab:hover .briefing-rail-icon {
              color: var(--hover-color) !important;
            }
          `}</style>

          <FileTextOutlined
            className="briefing-rail-icon"
            style={{
              fontSize: 13,
              color: colors.textSecondary,
              ...(isStreaming && {
                animation: "briefing-pulse 1.5s infinite",
              }),
            }}
          />

          <span
            className="briefing-rail-label"
            style={{
              fontSize: 11,
              textTransform: "uppercase",
              letterSpacing: "0.5px",
              fontFamily: MONO_FONT,
              color: colors.textSecondary,
              writingMode: "vertical-rl",
              textOrientation: "mixed",
              transform: "rotate(180deg)",
              whiteSpace: "nowrap",
              lineHeight: 1,
            }}
          >
            BRIEFING
          </span>

          {(planStepBadge ?? (specialistCount > 0 ? String(specialistCount) : null)) && (
            <span
              style={{
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                minWidth: planStepBadge ? 22 : 18,
                height: 18,
                padding: planStepBadge ? "0 4px" : undefined,
                borderRadius: planStepBadge ? 9 : "50%",
                width: planStepBadge ? undefined : 18,
                background: token.colorPrimary,
                color: token.colorTextLightSolid,
                fontSize: planStepBadge ? 9 : 10,
                fontWeight: 700,
                fontFamily: MONO_FONT,
                lineHeight: 1,
                ...(isStreaming && {
                  animation: "briefing-pulse 1.5s infinite",
                }),
              }}
            >
              {planStepBadge ?? specialistCount}
            </span>
          )}
        </div>
      </>
    );
  },
);

BriefingRailToggleTab.displayName = "BriefingRailToggleTab";
