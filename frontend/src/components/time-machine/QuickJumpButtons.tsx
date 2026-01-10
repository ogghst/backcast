import React from "react";
import { Button, Space, Tooltip } from "antd";
import type { QuickJumpPreset } from "./types";

interface QuickJumpButtonsProps {
  /** Called when a preset is clicked */
  onJump: (preset: QuickJumpPreset) => void;
  /** Currently active preset (for highlighting) */
  activePreset?: QuickJumpPreset | null;
  /** Disable all buttons */
  disabled?: boolean;
}

const PRESETS: { key: QuickJumpPreset; label: string; tooltip: string }[] = [
  { key: "1D", label: "1D", tooltip: "Go back 1 day" },
  { key: "1W", label: "1W", tooltip: "Go back 1 week" },
  { key: "1M", label: "1M", tooltip: "Go back 1 month" },
  { key: "3M", label: "3M", tooltip: "Go back 3 months" },
  { key: "ALL", label: "All", tooltip: "Go to project start" },
];

/**
 * Quick jump buttons for common time navigation.
 *
 * @example
 * ```tsx
 * <QuickJumpButtons
 *   onJump={(preset) => {
 *     const date = calculateDateFromPreset(preset);
 *     selectTime(date);
 *   }}
 * />
 * ```
 */
export function QuickJumpButtons({
  onJump,
  activePreset,
  disabled = false,
}: QuickJumpButtonsProps) {
  return (
    <Space size="small">
      {PRESETS.map(({ key, label, tooltip }) => (
        <Tooltip key={key} title={tooltip}>
          <Button
            size="small"
            type={activePreset === key ? "primary" : "default"}
            onClick={() => onJump(key)}
            disabled={disabled}
          >
            {label}
          </Button>
        </Tooltip>
      ))}
    </Space>
  );
}

/**
 * Calculate a date based on quick jump preset.
 *
 * @param preset - The preset to calculate from
 * @param projectStartDate - Optional project start date for "ALL" preset
 * @returns The calculated date
 */
export function calculateDateFromPreset(
  preset: QuickJumpPreset,
  projectStartDate?: Date | null
): Date {
  const now = new Date();

  switch (preset) {
    case "1D":
      return new Date(now.getTime() - 24 * 60 * 60 * 1000);
    case "1W":
      return new Date(now.getTime() - 7 * 24 * 60 * 60 * 1000);
    case "1M":
      return new Date(now.setMonth(now.getMonth() - 1));
    case "3M":
      return new Date(now.setMonth(now.getMonth() - 3));
    case "ALL":
      return (
        projectStartDate || new Date(now.setFullYear(now.getFullYear() - 1))
      );
  }
}

export default QuickJumpButtons;
