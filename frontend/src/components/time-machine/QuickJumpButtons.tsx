import React from "react";
import { Button, Space, Tooltip } from "antd";
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
  // Use current date or now as reference
  const baseDate = currentDate || new Date();

  return (
    <Space size="small">
      {PRESETS.map(({ key, label, tooltip }) => {
        // Check if jump would go out of bounds
        const targetDate = calculateDateFromPreset(key, baseDate);
        let isOutOfRange = false;

        if (minDate && targetDate < minDate) isOutOfRange = true;
        if (maxDate && targetDate > maxDate) isOutOfRange = true;

        return (
          <Tooltip key={key} title={isOutOfRange ? "Out of range" : tooltip}>
            <Button
              size="small"
              onClick={() => onJump(key)}
              disabled={disabled || isOutOfRange}
            >
              {label}
            </Button>
          </Tooltip>
        );
      })}
    </Space>
  );
}

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
