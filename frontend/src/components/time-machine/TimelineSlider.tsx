import React, { useMemo } from "react";
import { Slider, Tooltip } from "antd";
import type { SliderMarks } from "antd/es/slider";
import type { TimelineEvent } from "./types";

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
  // Convert dates to timestamps for slider
  const minValue = minDate.getTime();
  const maxValue = maxDate.getTime();
  const currentValue = value?.getTime() ?? maxValue;

  // Generate marks for events and key dates
  const marks = useMemo<SliderMarks>(() => {
    const result: SliderMarks = {};

    // Add start date mark
    result[minValue] = {
      label: formatShortDate(minDate),
      style: { fontSize: 10, whiteSpace: "nowrap" },
    };

    // Add end date mark
    result[maxValue] = {
      label: formatShortDate(maxDate),
      style: { fontSize: 10, fontWeight: "bold", whiteSpace: "nowrap" },
    };

    // Add event markers
    events.forEach((event) => {
      const timestamp = event.timestamp.getTime();
      // Only add if within range and not too close to edges
      if (
        timestamp > minValue + (maxValue - minValue) * 0.05 &&
        timestamp < maxValue - (maxValue - minValue) * 0.05
      ) {
        result[timestamp] = {
          label: (
            <Tooltip
              title={`${event.label} - ${formatDateTime(event.timestamp)}`}
            >
              <span style={{ fontSize: 10, color: getEventColor(event.type) }}>
                {getEventIcon(event.type)}
              </span>
            </Tooltip>
          ),
        };
      }
    });

    return result;
  }, [minDate, maxDate, minValue, maxValue, events]);

  // Handle slider change
  const handleChange = (timestamp: number) => {
    onChange(new Date(timestamp));
  };

  // Tooltip formatter
  const tipFormatter = (timestamp?: number): string => {
    if (!timestamp) return "";
    return formatDateTime(new Date(timestamp));
  };

  return (
    <Slider
      min={minValue}
      max={maxValue}
      value={currentValue}
      onChange={handleChange}
      marks={marks}
      tooltip={{ formatter: tipFormatter }}
      disabled={disabled}
      style={{ marginTop: 16, marginBottom: 24 }}
    />
  );
}

// Helper functions
function formatShortDate(date: Date): string {
  return date.toLocaleDateString(undefined, {
    month: "short",
    year: "2-digit",
  });
}

function formatDateTime(date: Date): string {
  return date.toLocaleString(undefined, {
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function getEventColor(type: TimelineEvent["type"]): string {
  switch (type) {
    case "branch_created":
      return "#52c41a"; // Green
    case "branch_merged":
      return "#1890ff"; // Blue
    default:
      return "#888";
  }
}

function getEventIcon(type: TimelineEvent["type"]): string {
  switch (type) {
    case "branch_created":
      return "⑂"; // Branch icon
    case "branch_merged":
      return "⤴"; // Merge icon
    default:
      return "●";
  }
}

export default TimelineSlider;
