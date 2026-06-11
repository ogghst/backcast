import { memo, useState } from "react";
import { theme, Tag } from "antd";
import {
  UserOutlined,
  BulbOutlined,
  QuestionCircleOutlined,
  RightOutlined,
} from "@ant-design/icons";
import { useThemeTokens } from "@/hooks/useThemeTokens";
import { MarkdownRenderer } from "./MarkdownRenderer";
import type { BriefingSectionData } from "../types";

const MONO_FONT = "'JetBrains Mono', 'SF Mono', 'Fira Code', monospace";

interface BriefingSectionCardProps {
  section: BriefingSectionData;
  isStreaming?: boolean;
}

export const BriefingSectionCard = memo(
  ({ section, isStreaming = false }: BriefingSectionCardProps) => {
    const { token } = theme.useToken();
    const { spacing, colors, borderRadius } = useThemeTokens();
    const [notesExpanded, setNotesExpanded] = useState(false);

    const displayName = section.specialist_name.replace(/_/g, " ");

    const hasFindings = section.key_findings.length > 0;
    const hasQuestions = section.open_questions.length > 0;
    const hasNotes = section.delegation_notes.length > 0;

    return (
      <div
        style={{
          marginBottom: spacing.sm,
          borderRadius: borderRadius.md,
          border: `1px solid ${token.colorBorderSecondary}`,
          background: token.colorBgContainer,
          overflow: "hidden",
        }}
      >
        {/* Header */}
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: spacing.xs,
            padding: `${spacing.xs}px ${spacing.sm}px`,
            borderBottom: `1px solid ${token.colorBorderSecondary}`,
            background: token.colorBgLayout,
            ...(isStreaming && {
              animation: "briefing-pulse 1.5s infinite",
            }),
          }}
        >
          <UserOutlined style={{ fontSize: 11, color: colors.textSecondary }} />
          <span
            style={{
              fontFamily: MONO_FONT,
              fontSize: 11,
              fontWeight: 500,
              textTransform: "uppercase" as const,
              letterSpacing: "0.3px",
              color: colors.textSecondary,
            }}
          >
            {displayName}
          </span>
          {section.step_index != null && (
            <Tag
              style={{
                marginLeft: "auto",
                fontSize: 10,
                lineHeight: "16px",
                padding: "0 4px",
                borderRadius: 3,
                fontFamily: MONO_FONT,
                border: "none",
                background: `${token.colorPrimary}18`,
                color: token.colorPrimary,
              }}
            >
              {section.step_index + 1}
            </Tag>
          )}
        </div>

        {/* Summary */}
        <div
          style={{
            padding: `${spacing.xs}px ${spacing.sm}px`,
            fontSize: 12,
            lineHeight: 1.6,
            color: colors.text,
          }}
        >
          <MarkdownRenderer content={section.summary} isStreaming={false} />
        </div>

        {/* Key Findings */}
        {hasFindings && (
          <div
            style={{
              padding: `${spacing.xs}px ${spacing.sm}px`,
              borderTop: `1px solid ${token.colorBorderSecondary}`,
            }}
          >
            {section.key_findings.map((finding, i) => (
              <div
                key={i}
                style={{
                  display: "flex",
                  alignItems: "flex-start",
                  gap: spacing.xs,
                  marginBottom: i < section.key_findings.length - 1 ? 2 : 0,
                  fontSize: 12,
                  lineHeight: 1.5,
                }}
              >
                <BulbOutlined
                  style={{
                    fontSize: 10,
                    color: token.colorPrimary,
                    marginTop: 4,
                    flexShrink: 0,
                  }}
                />
                <span style={{ color: colors.text }}>
                  <MarkdownRenderer content={finding} isStreaming={false} />
                </span>
              </div>
            ))}
          </div>
        )}

        {/* Open Questions */}
        {hasQuestions && (
          <div
            style={{
              padding: `${spacing.xs}px ${spacing.sm}px`,
              borderTop: `1px solid ${token.colorBorderSecondary}`,
            }}
          >
            {section.open_questions.map((question, i) => (
              <div
                key={i}
                style={{
                  display: "flex",
                  alignItems: "flex-start",
                  gap: spacing.xs,
                  marginBottom:
                    i < section.open_questions.length - 1 ? 2 : 0,
                  fontSize: 12,
                  lineHeight: 1.5,
                }}
              >
                <QuestionCircleOutlined
                  style={{
                    fontSize: 10,
                    color: token.colorWarning,
                    marginTop: 4,
                    flexShrink: 0,
                  }}
                />
                <span style={{ color: colors.text }}>
                  <MarkdownRenderer content={question} isStreaming={false} />
                </span>
              </div>
            ))}
          </div>
        )}

        {/* Delegation Notes (collapsible) */}
        {hasNotes && (
          <div
            style={{
              borderTop: `1px solid ${token.colorBorderSecondary}`,
            }}
          >
            <button
              type="button"
              onClick={() => setNotesExpanded((prev) => !prev)}
              style={{
                display: "flex",
                alignItems: "center",
                gap: spacing.xs,
                width: "100%",
                padding: `${spacing.xs}px ${spacing.sm}px`,
                background: "transparent",
                border: "none",
                cursor: "pointer",
                color: colors.textTertiary,
                fontFamily: MONO_FONT,
                fontSize: 10,
                textTransform: "uppercase" as const,
                letterSpacing: "0.3px",
              }}
            >
              <RightOutlined
                style={{
                  fontSize: 8,
                  transition: "transform 0.15s",
                  transform: notesExpanded ? "rotate(90deg)" : "rotate(0deg)",
                }}
              />
              Delegation Notes
            </button>
            {notesExpanded && (
              <div
                style={{
                  padding: `0 ${spacing.sm}px ${spacing.xs}px`,
                  fontSize: 11,
                  lineHeight: 1.5,
                  color: colors.textSecondary,
                }}
              >
                <MarkdownRenderer
                  content={section.delegation_notes}
                  isStreaming={false}
                />
              </div>
            )}
          </div>
        )}
      </div>
    );
  },
);
BriefingSectionCard.displayName = "BriefingSectionCard";
