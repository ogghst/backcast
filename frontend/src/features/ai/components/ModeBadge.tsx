/**
 * ModeBadge Component
 *
 * Visual indicator for AI tool execution mode.
 * Color-coded badge showing current execution mode.
 */

import { theme } from "antd";

import type { ExecutionMode } from "../chat/types";

interface ModeBadgeProps {
  mode: ExecutionMode;
}

/**
 * Color scheme for execution modes using antd theme tokens
 * - Safe: Green (restricted, secure)
 * - Standard: Blue (balanced, default)
 * - Expert: Orange (unrestricted, powerful)
 */
const getModeConfig = (token: ReturnType<typeof theme.useToken>["token"]) => ({
  safe: {
    label: "Safe",
    color: token.colorSuccess,
    bgColor: token.colorSuccessBg,
    borderColor: token.colorSuccessBorder,
  },
  standard: {
    label: "Standard",
    color: token.colorPrimary,
    bgColor: token.colorPrimaryBg,
    borderColor: token.colorPrimaryBorder,
  },
  expert: {
    label: "Expert",
    color: token.colorWarning,
    bgColor: token.colorWarningBg,
    borderColor: token.colorWarningBorder,
  },
});

/**
 * Badge component showing the current execution mode
 *
 * @param mode - The execution mode to display
 *
 * @example
 * ```tsx
 * <ModeBadge mode="safe" />
 * <ModeBadge mode="standard" />
 * <ModeBadge mode="expert" />
 * ```
 */
export const ModeBadge = ({ mode }: ModeBadgeProps) => {
  const { token } = theme.useToken();
  const MODE_CONFIG = getModeConfig(token);
  const config = MODE_CONFIG[mode];

  return (
    <span
      className={`execution-mode-badge mode-${mode}`}
      style={{
        display: "inline-flex",
        alignItems: "center",
        padding: "2px 8px",
        borderRadius: "4px",
        fontSize: "12px",
        fontWeight: 500,
        color: config.color,
        backgroundColor: config.bgColor,
        border: `1px solid ${config.borderColor}`,
        textTransform: "capitalize",
      }}
      aria-label={`Execution mode: ${config.label}`}
    >
      {config.label}
    </span>
  );
};
