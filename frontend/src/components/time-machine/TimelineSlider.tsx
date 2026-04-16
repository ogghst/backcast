import { useMemo, useRef, useCallback } from "react";
import { Tooltip, theme } from "antd";
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
  const trackRef = useRef<HTMLDivElement>(null);
  const thumbRef = useRef<HTMLDivElement>(null);

  // Convert dates to timestamps for slider
  const minValue = minDate.getTime();
  const maxValue = maxDate.getTime();
  const currentValue = value?.getTime() ?? maxValue;

  // Calculate percentage for thumb position
  const getPercentage = useCallback(
    (timestamp: number) => {
      return ((timestamp - minValue) / (maxValue - minValue)) * 100;
    },
    [minValue, maxValue]
  );

  const percentage = getPercentage(currentValue);

  // Handle drag start
  const handleDragStart = useCallback(() => {
    if (disabled) return;
  }, [disabled]);

  // Handle drag end
  const handleDragEnd = useCallback(() => {
    if (disabled) return;
  }, [disabled]);

  // Handle track click/drag
  const handleTrackInteraction = useCallback(
    (e: React.MouseEvent<HTMLDivElement>) => {
      if (disabled || !trackRef.current) return;

      const rect = trackRef.current.getBoundingClientRect();
      const x = e.clientX - rect.left;
      const percentage = Math.max(0, Math.min(1, x / rect.width));
      const timestamp = minValue + percentage * (maxValue - minValue);

      onChange(new Date(timestamp));
    },
    [disabled, minValue, maxValue, onChange]
  );

  // Filter events to show as markers
  const visibleEvents = useMemo(() => {
    return events.filter((event) => {
      const timestamp = event.timestamp.getTime();
      return (
        timestamp > minValue + (maxValue - minValue) * 0.05 &&
        timestamp < maxValue - (maxValue - minValue) * 0.05
      );
    });
  }, [events, minValue, maxValue]);

  // Tooltip formatter
  const formatTooltip = useCallback(
    (timestamp: number) => {
      return formatDateTime(new Date(timestamp));
    },
    []
  );

  return (
    <div className="tm-slider-container">
      {/* Custom Slider */}
      <div
        ref={trackRef}
        className="tm-slider-track"
        onClick={handleTrackInteraction}
        onMouseDown={handleDragStart}
        onMouseUp={handleDragEnd}
        onMouseLeave={handleDragEnd}
        role="slider"
        aria-label="Timeline slider"
        aria-valuemin={minValue}
        aria-valuemax={maxValue}
        aria-valuenow={currentValue}
        aria-disabled={disabled}
        tabIndex={disabled ? -1 : 0}
        style={{
          cursor: disabled ? "not-allowed" : "pointer",
          opacity: disabled ? 0.5 : 1,
        }}
        onKeyDown={(e) => {
          if (disabled) return;
          const step = (maxValue - minValue) / 100;
          let newValue = currentValue;

          if (e.key === "ArrowLeft" || e.key === "ArrowDown") {
            newValue = Math.max(minValue, currentValue - step);
            e.preventDefault();
          } else if (e.key === "ArrowRight" || e.key === "ArrowUp") {
            newValue = Math.min(maxValue, currentValue + step);
            e.preventDefault();
          } else if (e.key === "Home") {
            newValue = minValue;
            e.preventDefault();
          } else if (e.key === "End") {
            newValue = maxValue;
            e.preventDefault();
          }

          if (newValue !== currentValue) {
            onChange(new Date(newValue));
          }
        }}
      >
        {/* Fill */}
        <div
          className="tm-slider-fill"
          style={{
            width: `${percentage}%`,
            background: token.colorPrimary,
          }}
        />

        {/* Thumb */}
        <Tooltip title={formatTooltip(currentValue)} placement="top">
          <div
            ref={thumbRef}
            className="tm-slider-thumb"
            style={{
              left: `${percentage}%`,
              background: token.colorBgContainer,
              borderColor: token.colorPrimary,
            }}
            onMouseDown={(e) => {
              e.stopPropagation();
              handleDragStart();
            }}
          />
        </Tooltip>

        {/* Event Markers */}
        {visibleEvents.map((event) => {
          const eventPercentage = getPercentage(event.timestamp.getTime());
          const eventColor = getEventColor(event.type, token);
          return (
            <Tooltip
              key={event.id}
              title={`${event.label} - ${formatDateTime(event.timestamp)}`}
              placement="top"
            >
              <div
                className="tm-slider-marker"
                style={{
                  left: `${eventPercentage}%`,
                  background: token.colorBorder,
                }}
                onClick={(e) => {
                  e.stopPropagation();
                  onChange(event.timestamp);
                }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.background = token.colorPrimary;
                  e.currentTarget.style.transform = "translate(-50%, -50%) scale(1.4)";
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.background = eventColor;
                  e.currentTarget.style.transform = "translate(-50%, -50%) scale(1)";
                }}
                aria-label={`Event: ${event.label}`}
              />
            </Tooltip>
          );
        })}
      </div>

      {/* Labels */}
      <div className="tm-slider-labels">
        <span>{formatShortDate(minDate)}</span>
        <span style={{ fontWeight: 600 }}>{formatShortDate(maxDate)}</span>
      </div>
    </div>
  );
}

// Helper functions
function formatShortDate(date: Date): string {
  return formatDate(date.toISOString(), { style: "short" });
}

function formatDateTime(date: Date): string {
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
