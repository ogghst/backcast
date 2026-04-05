/**
 * TokenUsageBar Component
 *
 * Compact telemetry readout showing token usage metrics after
 * an assistant response completes. Renders as a subtle inline bar
 * with monospaced numbers, pipe separators, and a fade-in animation.
 *
 * Design: "Mission Control Telemetry" - industrial monitoring aesthetic
 * that blends into the existing "Industrial Technical Minimalism" of the chat.
 */

import { useMemo } from "react";
import type { TokenUsage } from "../types";
import { useThemeTokens } from "@/hooks/useThemeTokens";

interface TokenUsageBarProps {
  token_usage: TokenUsage;
}

/** CSS keyframe name for the fade-in animation (defined inline) */
const FADE_ANIMATION_CLASS = "token-usage-fade-in";

/**
 * Formats a number with locale-aware thousands separators.
 * Returns "0" for falsy/zero values instead of empty string.
 */
function formatTokenCount(n: number): string {
  return n.toLocaleString();
}

/**
 * Renders a compact horizontal bar with input/output/total token metrics.
 *
 * Appears at the bottom of the message list after a response completes,
 * fading in with a subtle animation. Uses monospace font for the numeric
 * readouts to match the industrial telemetry aesthetic.
 */
export const TokenUsageBar = ({ token_usage }: TokenUsageBarProps) => {
  const { spacing, typography, colors, borderRadius } = useThemeTokens();

  const prompt = token_usage.prompt_tokens ?? 0;
  const completion = token_usage.completion_tokens ?? 0;
  const total = token_usage.total_tokens ?? 0;

  // Skip rendering if there's nothing to show
  const hasData = useMemo(() => prompt > 0 || completion > 0 || total > 0, [prompt, completion, total]);
  if (!hasData) return null;

  const valueFont = "'Ubuntu', monospace";

  const dividerStyle = {
    width: 1,
    height: typography.sizes.sm,
    backgroundColor: colors.borderSecondary,
    flexShrink: 0,
  } as const;

  const metricStyle = {
    display: "flex",
    alignItems: "center",
    gap: spacing.xs,
    whiteSpace: "nowrap" as const,
  };

  const labelStyle = {
    fontSize: typography.sizes.xs,
    color: colors.textTertiary,
    letterSpacing: 0.5,
    textTransform: "uppercase" as const,
  };

  const valueStyle = {
    fontSize: typography.sizes.xs,
    fontFamily: valueFont,
    color: colors.textSecondary,
    fontVariantNumeric: "tabular-nums" as const,
  };

  return (
    <>
      <div
        className={FADE_ANIMATION_CLASS}
        style={{
          display: "flex",
          alignItems: "center",
          gap: spacing.sm,
          padding: `${spacing.xs}px ${spacing.sm}px`,
          margin: `${spacing.xs}px ${spacing.md}px`,
          backgroundColor: colors.bgContainer,
          borderRadius: borderRadius.md,
          border: `1px solid ${colors.borderSecondary}`,
          opacity: 0,
          animation: `${FADE_ANIMATION_CLASS} 0.6s ease-out forwards`,
          animationDelay: "0.15s",
        }}
      >
        {/* Marker symbol */}
        <span
          style={{
            fontSize: typography.sizes.xs,
            color: colors.textTertiary,
            fontFamily: valueFont,
            lineHeight: 1,
          }}
        >
          &#9656;
        </span>

        {/* Input tokens */}
        <div style={metricStyle}>
          <span style={labelStyle}>in</span>
          <span style={valueStyle}>{formatTokenCount(prompt)}</span>
        </div>

        <div style={dividerStyle} />

        {/* Output tokens */}
        <div style={metricStyle}>
          <span style={labelStyle}>out</span>
          <span style={valueStyle}>{formatTokenCount(completion)}</span>
        </div>

        <div style={dividerStyle} />

        {/* Total tokens */}
        <div style={metricStyle}>
          <span style={labelStyle}>total</span>
          <span style={{ ...valueStyle, color: colors.textSecondary }}>
            {formatTokenCount(total)}
          </span>
        </div>
      </div>

      <style>{`
        @keyframes ${FADE_ANIMATION_CLASS} {
          from {
            opacity: 0;
            transform: translateY(2px);
          }
          to {
            opacity: 1;
            transform: translateY(0);
          }
        }
      `}</style>
    </>
  );
};
