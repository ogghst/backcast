import React, { useMemo, useCallback } from "react";
import { theme, DatePicker, Divider, Space } from "antd";
import {
  CloseOutlined,
  UndoOutlined,
  CalendarOutlined,
  HistoryOutlined,
} from "@ant-design/icons";
import dayjs from "dayjs";

import { useTimeMachineStore } from "@/stores/useTimeMachineStore";
import { useTimeMachine } from "@/contexts/TimeMachineContext";
import { TimelineSlider } from "./TimelineSlider";
import { QuickJumpButtons, calculateDateFromPreset } from "./QuickJumpButtons";
import { BranchSelector } from "./BranchSelector";
import { ViewModeSelector } from "./ViewModeSelector";
import type { QuickJumpPreset, ProjectTimelineData } from "./types";
import "./TimeMachine.styles.css";
import { formatDate, formatTime } from "@/utils/formatters";

interface TimeMachineExpandedProps {
  /** Project ID */
  projectId: string;
  /** Project name for display */
  projectName?: string;
  /** Timeline data (start/end dates, branches, events) */
  timelineData?: ProjectTimelineData;
  /** Loading state */
  isLoading?: boolean;
}

/**
 * Expanded Time Machine panel - integrated control deck.
 *
 * All time navigation controls in one cohesive panel:
 * - Status indicator (historical/current)
 * - Branch and view mode selectors
 * - Timeline slider with event markers
 * - Quick jump buttons
 * - Precise date/time picker
 * - Reset to now button
 *
 * @example
 * ```tsx
 * {isExpanded && (
 *   <TimeMachineExpanded
 *     projectId={projectId}
 *     projectName="Project Alpha"
 *     timelineData={{
 *       startDate: new Date('2025-01-01'),
 *       endDate: null,
 *       branches: ['main', 'BR-001'],
 *       events: [],
 *     }}
 *   />
 * )}
 * ```
 */
export function TimeMachineExpanded({
  projectId,
  timelineData,
  isLoading = false,
}: TimeMachineExpandedProps) {
  const { token } = theme.useToken();
  const { isHistorical, invalidateQueries } = useTimeMachine();
  const { toggleExpanded, getSelectedTime, selectTime, resetToNow } =
    useTimeMachineStore();

  const selectedTime = getSelectedTime();

  // Parse selected time
  const selectedDate = useMemo(
    () => (selectedTime ? new Date(selectedTime) : null),
    [selectedTime]
  );

  // Default date range if not provided
  const now = useMemo(() => new Date(), []);
  const minDate = timelineData?.startDate || now;
  const maxDate = timelineData?.endDate || now;

  // Handle time selection with query invalidation
  const handleSelectTime = useCallback(
    (date: Date | null) => {
      selectTime(date);
      invalidateQueries();
    },
    [selectTime, invalidateQueries]
  );

  // Handle quick jump
  const handleQuickJump = useCallback(
    (preset: QuickJumpPreset) => {
      const baseDate = selectedDate || new Date();
      const date = calculateDateFromPreset(preset, baseDate);
      handleSelectTime(date);
    },
    [selectedDate, handleSelectTime]
  );

  // Handle reset to now
  const handleResetToNow = useCallback(() => {
    resetToNow();
    invalidateQueries();
  }, [resetToNow, invalidateQueries]);

  // Handle date picker change
  const handleDatePickerChange = useCallback(
    (date: dayjs.Dayjs | null) => {
      handleSelectTime(date?.toDate() || null);
    },
    [handleSelectTime]
  );

  return (
    <div
      style={{
        background: token.colorBgContainer,
        borderRadius: token.borderRadiusLG,
        boxShadow: token.boxShadowTertiary,
        padding: token.paddingLG,
        animation: "tm-slide-down 280ms cubic-bezier(0.34, 1.56, 0.64, 1)",
        maxWidth: "100%",
      }}
    >
      {/* Header Row */}
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          marginBottom: token.marginMD,
        }}
      >
        {/* Left: Status indicator */}
        <div
          style={{
            display: "inline-flex",
            alignItems: "center",
            gap: token.marginXS,
            padding: `${token.paddingXS}px ${token.paddingSM}px`,
            background: isHistorical
              ? token.colorPrimaryBg
              : token.colorFillSecondary,
            color: isHistorical ? token.colorPrimary : token.colorTextSecondary,
            borderRadius: token.borderRadiusSM,
            fontSize: token.fontSizeSM,
            fontWeight: token.fontWeightStrong,
          }}
        >
          <HistoryOutlined />
          <span
            style={{
              display: "flex",
              alignItems: "center",
              gap: token.marginXS,
            }}
          >
            {isHistorical ? (
              <>
                Viewing History:{" "}
                <strong>
                  {selectedDate ? formatDate(selectedDate.toISOString()) : ""}
                </strong>
                {" at "}
                <strong>
                  {selectedDate ? formatTime(selectedDate.toISOString()) : ""}
                </strong>
              </>
            ) : (
              "Viewing Current State"
            )}
          </span>
        </div>

        {/* Right: Close button */}
        <button
          onClick={toggleExpanded}
          aria-label="Close time machine"
          type="button"
          style={{
            padding: token.paddingXS,
            background: "transparent",
            color: token.colorTextSecondary,
            cursor: "pointer",
            borderRadius: token.borderRadiusSM,
            transition: "all 150ms ease",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            width: 28,
            height: 28,
            fontSize: token.fontSizeSM,
          }}
          onMouseEnter={(e) => {
            e.currentTarget.style.background = token.colorFillSecondary;
            e.currentTarget.style.color = token.colorText;
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.background = "transparent";
            e.currentTarget.style.color = token.colorTextSecondary;
          }}
        >
          <CloseOutlined />
        </button>
      </div>

      {/* Branch and View Mode Row */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: token.marginMD,
          marginBottom: token.marginMD,
        }}
      >
        <BranchSelector projectId={projectId} />
        <ViewModeSelector />
      </div>

      <Divider style={{ margin: `${token.marginMD}px 0` }} />

      {/* Timeline Slider */}
      <div style={{ margin: `${token.marginLG}px 0` }}>
        <TimelineSlider
          minDate={minDate}
          maxDate={maxDate}
          value={selectedDate}
          onChange={handleSelectTime}
          events={timelineData?.events || []}
          disabled={isLoading}
        />
      </div>

      {/* Quick Actions Row */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: token.marginMD,
          flexWrap: "wrap",
        }}
      >
        {/* Quick Jump Buttons */}
        <QuickJumpButtons
          onJump={handleQuickJump}
          disabled={isLoading}
          currentDate={selectedDate}
          minDate={minDate}
          maxDate={maxDate}
        />

        {/* Spacer */}
        <div style={{ flex: 1, minWidth: token.marginLG }} />

        {/* Precise Date Picker + Reset */}
        <Space>
          <DatePicker
            value={selectedDate ? dayjs(selectedDate) : null}
            onChange={handleDatePickerChange}
            showTime
            format="YYYY-MM-DD HH:mm"
            placeholder="Select exact date"
            style={{ width: 180 }}
            disabled={isLoading}
            size="middle"
            suffixIcon={<CalendarOutlined />}
          />

          <button
            onClick={handleResetToNow}
            disabled={isLoading || !isHistorical}
            type="button"
            style={{
              display: "inline-flex",
              alignItems: "center",
              gap: token.marginXS,
              padding: `${token.paddingXS}px ${token.paddingSM}px`,
              background: isLoading || !isHistorical
                ? token.colorFillTertiary
                : token.colorFillSecondary,
              color: token.colorText,
              fontSize: token.fontSizeSM,
              fontWeight: token.fontWeightStrong,
              borderRadius: token.borderRadiusSM,
              cursor: isLoading || !isHistorical ? "not-allowed" : "pointer",
              transition: "all 150ms ease",
              height: 32,
            }}
            onMouseEnter={(e) => {
              if (!isLoading && isHistorical) {
                e.currentTarget.style.background = token.colorFill;
              }
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.background = isHistorical
                ? token.colorFillSecondary
                : token.colorFillTertiary;
            }}
          >
            <UndoOutlined />
            <span>Now</span>
          </button>
        </Space>
      </div>
    </div>
  );
}

export default TimeMachineExpanded;
