/**
 * BriefingPanel Component
 *
 * Displays the compiled briefing document from the briefing room orchestrator.
 * Shows specialist contributions, completion status, and markdown findings.
 *
 * Replaces AgentActivityPanel with richer situational awareness of agent state.
 */

import { memo, useState, useCallback } from "react";
import { theme, Grid, Tag } from "antd";
import {
  FileTextOutlined,
  UpOutlined,
  DownOutlined,
  UserOutlined,
} from "@ant-design/icons";
import { useThemeTokens } from "@/hooks/useThemeTokens";
import { MarkdownRenderer } from "./MarkdownRenderer";

export interface BriefingState {
  markdown: string;
  completedSpecialists: string[];
  lastSpecialist: string;
}

interface BriefingPanelProps {
  briefing: BriefingState | null;
  isStreaming: boolean;
}

const SpecialistBadge = memo(
  ({ name, completed }: { name: string; completed: boolean }) => {
    const { token } = theme.useToken();
    return (
      <Tag
        icon={<UserOutlined />}
        color={completed ? token.colorSuccess : undefined}
        style={{
          fontSize: 11,
          borderRadius: 4,
          fontFamily: "'JetBrains Mono', 'SF Mono', 'Fira Code', monospace",
        }}
      >
        {name.replace(/_/g, " ")}
      </Tag>
    );
  },
);
SpecialistBadge.displayName = "SpecialistBadge";

export const BriefingPanel = memo(
  ({ briefing, isStreaming }: BriefingPanelProps) => {
    const { token } = theme.useToken();
    const { spacing } = useThemeTokens();
    const screens = Grid.useBreakpoint();
    const isMobile = !screens.md;

    const [isExpanded, setIsExpanded] = useState(false);
    const [prevSpecialist, setPrevSpecialist] = useState<string>("");
    const [autoExpanded, setAutoExpanded] = useState(false);

    // Auto-expand when new specialist contributes
    const specialistChanged =
      briefing &&
      briefing.lastSpecialist &&
      briefing.lastSpecialist !== prevSpecialist;

    if (specialistChanged) {
      setPrevSpecialist(briefing.lastSpecialist);
      setAutoExpanded(true);
    }

    const toggleExpanded = useCallback(() => {
      setAutoExpanded(false);
      setIsExpanded((prev) => !prev);
    }, []);

    if (!briefing) return null;

    const completedCount = briefing.completedSpecialists.length;
    const effectivelyExpanded = autoExpanded || isExpanded;

    return (
      <>
        <style>{`
          @keyframes briefing-pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.6; }
          }
          .briefing-toggle:active {
            opacity: 0.8;
          }
          .briefing-scroll::-webkit-scrollbar {
            width: 4px;
          }
          .briefing-scroll::-webkit-scrollbar-thumb {
            background: ${token.colorBorderSecondary};
            border-radius: 2px;
          }
        `}</style>

        <div
          style={{
            borderTop: `1px solid ${token.colorBorderSecondary}`,
            borderBottom: `1px solid ${token.colorBorderSecondary}`,
            background: token.colorBgLayout,
          }}
        >
          {/* Header bar */}
          <button
            type="button"
            className="briefing-toggle"
            onClick={toggleExpanded}
            style={{
              display: "flex",
              alignItems: "center",
              width: "100%",
              padding: `${spacing.xs}px ${isMobile ? spacing.sm : spacing.md}px`,
              background: "transparent",
              border: "none",
              cursor: "pointer",
              color: token.colorTextSecondary,
              fontFamily:
                "'JetBrains Mono', 'SF Mono', 'Fira Code', monospace",
              fontSize: 11,
              textTransform: "uppercase" as const,
              letterSpacing: "0.5px",
              gap: spacing.xs,
              outline: "none",
            }}
            aria-expanded={effectivelyExpanded}
            aria-label={effectivelyExpanded ? "Collapse briefing" : "Expand briefing"}
          >
            <FileTextOutlined
              style={{
                fontSize: 13,
                color: isStreaming ? token.colorPrimary : token.colorTextSecondary,
                ...(isStreaming && { animation: "briefing-pulse 1.5s infinite" }),
              }}
            />
            <span style={{ flex: 1, textAlign: "left" }}>
              Briefing
              {completedCount > 0 && (
                <span style={{ opacity: 0.7, marginLeft: 6 }}>
                  {completedCount} specialist{completedCount !== 1 ? "s" : ""}
                </span>
              )}
            </span>

            {/* Specialist badges in collapsed header */}
            {!effectivelyExpanded && (
              <span
                style={{
                  display: "flex",
                  gap: 4,
                  marginRight: spacing.xs,
                  overflow: "hidden",
                }}
              >
                {briefing.completedSpecialists.slice(0, 3).map((name) => (
                  <SpecialistBadge
                    key={name}
                    name={name}
                    completed={true}
                  />
                ))}
                {briefing.completedSpecialists.length > 3 && (
                  <span style={{ fontSize: 10, opacity: 0.6 }}>
                    +{briefing.completedSpecialists.length - 3}
                  </span>
                )}
              </span>
            )}

            {effectivelyExpanded ? (
              <UpOutlined style={{ fontSize: 10 }} />
            ) : (
              <DownOutlined style={{ fontSize: 10 }} />
            )}
          </button>

          {/* Expandable content */}
          <div
            style={{
              maxHeight: effectivelyExpanded ? 280 : 0,
              overflow: "hidden",
              transition: "max-height 0.25s ease-out",
            }}
          >
            <div
              className="briefing-scroll"
              style={{
                maxHeight: 260,
                overflowY: "auto",
                padding: `${spacing.xs}px ${isMobile ? spacing.sm : spacing.md}px ${spacing.md}px`,
                borderTop: `1px solid ${token.colorBorderSecondary}`,
              }}
            >
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
            </div>
          </div>
        </div>
      </>
    );
  },
);

BriefingPanel.displayName = "BriefingPanel";
