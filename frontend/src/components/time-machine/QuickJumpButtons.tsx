import { Tooltip, theme } from "antd";
import type { QuickJumpPreset } from "./types";

interface QuickJumpButtonsProps {
  /** Called when a preset is clicked */
  onJump: (preset: QuickJumpPreset) => void;
  /** Current selected date (reference for relative jumps) */
  currentDate: Date | null;
  /** Minimum allowed date (project start) */
  minDate?: Date | null;
  /** Maximum allowed date (project end/now) */
  maxDate?: Date | null;
  /** Disable all buttons */
  disabled?: boolean;
}

const PRESETS: { key: QuickJumpPreset; label: string; tooltip: string }[] = [
  { key: "-1M", label: "-1M", tooltip: "Go back 1 month" },
  { key: "-1W", label: "-1W", tooltip: "Go back 1 week" },
  { key: "-1D", label: "-1D", tooltip: "Go back 1 day" },
  { key: "+1D", label: "+1D", tooltip: "Go forward 1 day" },
  { key: "+1W", label: "+1W", tooltip: "Go forward 1 week" },
  { key: "+1M", label: "+1M", tooltip: "Go forward 1 month" },
];

/**
 * Quick jump buttons for common time navigation.
 * Jumps are relative to the currently selected date.
 */
export function QuickJumpButtons({
  onJump,
  currentDate,
  minDate,
  maxDate,
  disabled = false,
}: QuickJumpButtonsProps) {
  const { token } = theme.useToken();

  // Use current date or now as reference
  const baseDate = currentDate || new Date();

  return (
    <div className="tm-quick-jumps">
      {PRESETS.map(({ key, label, tooltip }) => {
        // Check if jump would go out of bounds
        const targetDate = calculateDateFromPreset(key, baseDate);
        let isOutOfRange = false;

        if (minDate && targetDate < minDate) isOutOfRange = true;
        if (maxDate && targetDate > maxDate) isOutOfRange = true;

        const isBaseDateNow = !currentDate;

        return (
          <Tooltip key={key} title={isOutOfRange ? "Out of range" : tooltip}>
            <button
              className="tm-quick-jump-button"
              onClick={() => onJump(key)}
              disabled={disabled || isOutOfRange}
              type="button"
              aria-label={tooltip}
              style={{
                height: 30,
                minWidth: 40,
                padding: `0 ${token.paddingSM}px`,
                border: "none",
                background:
                  isBaseDateNow && label.startsWith("+")
                    ? token.colorFillTertiary
                    : token.colorFillSecondary,
                color: token.colorText,
                fontSize: 12,
                fontWeight: 600,
                borderRadius: token.borderRadiusSM,
                cursor:
                  disabled || isOutOfRange ? "not-allowed" : "pointer",
                transition: "all 150ms ease",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                letterSpacing: "0.02em",
                opacity:
                  isBaseDateNow && label.startsWith("+") ? 0.35 : undefined,
              }}
              onMouseEnter={(e) => {
                if (!disabled && !isOutOfRange && !(isBaseDateNow && label.startsWith("+"))) {
                  e.currentTarget.style.background = token.colorFill;
                  e.currentTarget.style.transform = "translateY(-1px)";
                }
              }}
              onMouseLeave={(e) => {
                if (isBaseDateNow && label.startsWith("+")) {
                  e.currentTarget.style.background = token.colorFillTertiary;
                } else {
                  e.currentTarget.style.background = token.colorFillSecondary;
                }
                e.currentTarget.style.transform = "translateY(0)";
              }}
            >
              {label}
            </button>
          </Tooltip>
        );
      })}
    </div>
  );
}

/* eslint-disable react-refresh/only-export-components */
/**
 * Calculate a date based on quick jump preset relative to a base date.
 *
 * @param preset - The preset to calculate from
 * @param baseDate - The reference date
 * @returns The calculated date
 */
export function calculateDateFromPreset(
  preset: QuickJumpPreset,
  baseDate: Date
): Date {
  const date = new Date(baseDate);

  switch (preset) {
    case "-1D":
      date.setDate(date.getDate() - 1);
      break;
    case "-1W":
      date.setDate(date.getDate() - 7);
      break;
    case "-1M":
      date.setMonth(date.getMonth() - 1);
      break;
    case "+1D":
      date.setDate(date.getDate() + 1);
      break;
    case "+1W":
      date.setDate(date.getDate() + 7);
      break;
    case "+1M":
      date.setMonth(date.getMonth() + 1);
      break;
  }

  return date;
}

export default QuickJumpButtons;
