import { useMemo, useCallback } from "react";
import { Slider, theme } from "antd";
import type { TimelineEvent } from "./types";
import "./TimeMachine.styles.css";
import { formatDate, formatDateTime as formatDateTimeUtil } from "@/utils/formatters";

interface TimelineSliderProps {
  /** Minimum date (project start) */
  minDate: Date;
  /** Maximum date (now or project end) */
  maxDate: Date;
  /** Currently selected date (null = now) */
  value: Date | null;
  /** Called when date changes */
  onChange: (date: Date | null) => void;
  /** Timeline events to display as markers */
  events?: TimelineEvent[];
  /** Disable slider */
  disabled?: boolean;
}

/**
 * Timeline slider for navigating through project history.
 *
 * Uses Ant Design Slider with custom marks for events.
 * The slider value is a timestamp, converted to/from Date.
 *
 * @example
 * ```tsx
 * <TimelineSlider
 *   minDate={projectStartDate}
 *   maxDate={new Date()}
 *   value={selectedTime}
 *   onChange={setSelectedTime}
 *   events={branchEvents}
 * />
 * ```
 */
export function TimelineSlider({
  minDate,
  maxDate,
  value,
  onChange,
  events = [],
  disabled = false,
}: TimelineSliderProps) {
  const { token } = theme.useToken();

  // Convert dates to timestamps for slider
  const minValue = minDate.getTime();
  const maxValue = maxDate.getTime();
  const currentValue = value?.getTime() ?? maxValue;

  // Filter events to show as markers (avoid edges)
  const visibleEvents = useMemo(() => {
    return events.filter((event) => {
      const ts = event.timestamp.getTime();
      return (
        ts > minValue + (maxValue - minValue) * 0.05 &&
        ts < maxValue - (maxValue - minValue) * 0.05
      );
    });
  }, [events, minValue, maxValue]);

  // Build marks for events
  const marks = useMemo(() => {
    const result: Record<number, { label: string; style?: React.CSSProperties }> = {};
    visibleEvents.forEach((event) => {
      const ts = event.timestamp.getTime();
      const color = getEventColor(event.type, token);
      result[ts] = {
        label: "",
        style: {
          // Small colored dot as mark label content via background
          width: 6,
          height: 6,
          borderRadius: "50%",
          background: color,
          position: "absolute" as const,
          top: -3,
          left: "50%",
          transform: "translateX(-50%)",
          zIndex: 1,
        },
      };
    });
    return result;
  }, [visibleEvents, token]);

  const handleChange = useCallback(
    (val: number) => {
      onChange(new Date(val));
    },
    [onChange]
  );

  const tooltipFormatter = useCallback(
    (val?: number) => {
      if (val == null) return "";
      return formatDateTime(new Date(val));
    },
    []
  );

  return (
    <div className="tm-slider-container">
      <Slider
        min={minValue}
        max={maxValue}
        value={currentValue}
        onChange={handleChange}
        disabled={disabled}
        tooltip={{ formatter: tooltipFormatter }}
        marks={Object.keys(marks).length > 0 ? marks : undefined}
        step={Math.max(1, Math.floor((maxValue - minValue) / 1000))}
        styles={{
          track: { background: token.colorPrimary },
          rail: { background: token.colorBorder },
          handle: {
            background: token.colorBgContainer,
            borderColor: token.colorPrimary,
          },
        }}
      />

      {/* Date labels */}
      <div className="tm-slider-labels">
        <span>{formatShortDate(minDate)}</span>
        <span style={{ fontWeight: 600 }}>{formatShortDate(maxDate)}</span>
      </div>
    </div>
  );
}

// Helper functions
function isValidDate(d: Date): boolean {
  return !isNaN(d.getTime());
}

function formatShortDate(date: Date): string {
  if (!isValidDate(date)) return "—";
  return formatDate(date.toISOString(), { style: "short" });
}

function formatDateTime(date: Date): string {
  if (!isValidDate(date)) return "";
  return formatDateTimeUtil(date.toISOString());
}

function getEventColor(
  type: TimelineEvent["type"],
  token: ReturnType<typeof theme.useToken>["token"]
): string {
  switch (type) {
    case "branch_created":
      return token.colorSuccess;
    case "branch_merged":
      return token.colorPrimary;
    default:
      return token.colorTextSecondary;
  }
}

export default TimelineSlider;
