/**
 * Portfolio date range picker.
 *
 * Wraps antd `DatePicker.RangePicker` with two preset buttons (Current Year,
 * YTD) plus manual range selection.
 *
 * RANGE → AS-OF MAPPING (locked decision, functional-analysis.md §13):
 *   The portfolio EVM query takes a single `control_date` (as-of), NOT a
 *   range. The range END is the as-of date. If the end is in the future or
 *   is "now", the as-of is TODAY (calendar year Jan–Dec semantics). A null /
 *   cleared range also resolves to today.
 *
 * Emits the derived as-of ISO date via `onChange(controlDate)`.
 */

import { useMemo } from "react";
import { DatePicker } from "antd";
import type { RangePickerProps } from "antd/es/date-picker";
import dayjs, { type Dayjs } from "dayjs";

const { RangePicker } = DatePicker;

export interface PortfolioDateRangePickerProps {
  /** Current as-of control date (ISO); null = today. */
  controlDate: string | null;
  /** Emitted when the user picks a range / preset (ISO date or null). */
  onChange: (controlDate: string | null) => void;
}

type RangeValue = [Dayjs | null, Dayjs | null] | null;
type RangePreset = NonNullable<RangePickerProps["presets"]>[number];

/** Build the antd presets for the current calendar year. */
function useYearPresets(): RangePreset[] {
  return useMemo(() => {
    const now = dayjs();
    const yearStart = now.startOf("year");
    const yearEnd = now.endOf("year");
    return [
      {
        label: "Current Year",
        value: [yearStart, yearEnd] as [Dayjs, Dayjs],
      },
      {
        label: "YTD",
        value: [yearStart, now] as [Dayjs, Dayjs],
      },
    ];
  }, []);
}

/**
 * Derive the EVM as-of control date from a picked range.
 *
 * Rules (see file docstring): end-of-range wins; future/now end → today;
 * null range → today (null).
 */
function rangeToControlDate(range: RangeValue): string | null {
  if (!range) return null;
  const end = range[1];
  if (!end) return null;
  const now = dayjs();
  // End in the future (inclusive of "now") → today.
  if (!end.isBefore(now, "day")) {
    return now.format("YYYY-MM-DD");
  }
  return end.format("YYYY-MM-DD");
}

export function PortfolioDateRangePicker({
  controlDate,
  onChange,
}: PortfolioDateRangePickerProps): React.JSX.Element {
  const presets = useYearPresets();

  // Render the RangePicker value from the current control date: show a
  // YTD-like window ending at the control date so the UI reflects state.
  const value: RangeValue = useMemo(() => {
    if (!controlDate) return null;
    const end = dayjs(controlDate);
    const start = end.startOf("year");
    return [start, end];
  }, [controlDate]);

  const handleChange = (range: RangeValue) => {
    onChange(rangeToControlDate(range));
  };

  return (
    <RangePicker
      value={value}
      onChange={handleChange}
      presets={presets}
      allowClear
      aria-label="Portfolio date range"
    />
  );
}
