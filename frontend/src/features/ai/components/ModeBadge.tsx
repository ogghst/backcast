/**
 * ModeBadge Component
 *
 * Visual indicator for AI tool execution mode.
 * Color-coded badge showing current execution mode.
 */

import type { ExecutionMode } from "../chat/types";

interface ModeBadgeProps {
  mode: ExecutionMode;
}

/**
 * Color scheme for execution modes
 * - Safe: Green (restricted, secure)
 * - Standard: Blue (balanced, default)
 * - Expert: Orange (unrestricted, powerful)
 */
const MODE_CONFIG = {
  safe: {
    label: "Safe",
    color: "#52c41a", // Ant Design green-6
    bgColor: "#f6ffed", // Ant Design green-1
    borderColor: "#b7eb8f", // Ant Design green-3
  },
  standard: {
    label: "Standard",
    color: "#1890ff", // Ant Design blue-6
    bgColor: "#e6f7ff", // Ant Design blue-1
    borderColor: "#91d5ff", // Ant Design blue-3
  },
  expert: {
    label: "Expert",
    color: "#fa8c16", // Ant Design orange-6
    bgColor: "#fff7e6", // Ant Design orange-1
    borderColor: "#ffd591", // Ant Design orange-3
  },
} as const;

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
