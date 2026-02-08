import React, { useMemo, useCallback } from "react";
import {
  Card,
  Space,
  Button,
  DatePicker,
  Divider,
  Typography,
  Alert,
} from "antd";
import { CloseOutlined, ReloadOutlined } from "@ant-design/icons";
import dayjs from "dayjs";

import { useTimeMachineStore } from "@/stores/useTimeMachineStore";
import { useTimeMachine } from "@/contexts/TimeMachineContext";
import { TimelineSlider } from "./TimelineSlider";

import { QuickJumpButtons, calculateDateFromPreset } from "./QuickJumpButtons";
import type { QuickJumpPreset, ProjectTimelineData } from "./types";

const { Text } = Typography;

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
 * Expanded Time Machine panel showing full timeline controls.
 *
 * Features:
 * - Timeline slider with event markers

 * - Quick jump buttons (1D, 1W, 1M, 3M, All)
 * - Date picker for precise selection
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
  timelineData,
  isLoading = false,
}: TimeMachineExpandedProps) {
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
  // eslint-disable-next-line
  const now = React.useRef(Date.now()).current;
  // Use timeline start date if provided, otherwise default to current time
  // (no historical viewing possible if project has no valid_time or start_date)
  const minDate = timelineData?.startDate || new Date(now);
  const maxDate = timelineData?.endDate || new Date(now);

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
    <Card
      size="small"
      style={{
        margin: "0 16px 16px 16px",
        borderTop: "none",
        borderTopLeftRadius: 0,
        borderTopRightRadius: 0,
      }}
      extra={
        <Button
          type="text"
          icon={<CloseOutlined />}
          onClick={toggleExpanded}
          aria-label="Close time machine"
        />
      }
    >
      {/* Historical mode warning */}
      {isHistorical && (
        <Alert
          type="info"
          showIcon
          message={
            <Text>
              Viewing project state as of{" "}
              <Text strong>{selectedDate?.toLocaleString()}</Text>
            </Text>
          }
          style={{ marginBottom: 16 }}
        />
      )}

      {/* Timeline Slider */}
      <TimelineSlider
        minDate={minDate}
        maxDate={maxDate}
        value={selectedDate}
        onChange={handleSelectTime}
        events={timelineData?.events || []}
        disabled={isLoading}
      />

      <Divider style={{ margin: "12px 0" }} />

      {/* Controls Row */}
      <Space
        style={{
          display: "flex",
          justifyContent: "space-between",
          flexWrap: "wrap",
          gap: 12,
        }}
      >
        {/* Left: Quick jumps */}
        <Space>
          <QuickJumpButtons
            onJump={handleQuickJump}
            disabled={isLoading}
            currentDate={selectedDate}
            minDate={minDate}
            maxDate={maxDate}
          />
        </Space>

        {/* Right: Date picker + Reset */}
        <Space>
          <DatePicker
            value={selectedDate ? dayjs(selectedDate) : null}
            onChange={handleDatePickerChange}
            showTime
            format="YYYY-MM-DD HH:mm"
            placeholder="Select exact date"
            style={{ width: 180 }}
            disabled={isLoading}
          />

          <Button
            icon={<ReloadOutlined />}
            onClick={handleResetToNow}
            disabled={isLoading || !isHistorical}
          >
            Now
          </Button>
        </Space>
      </Space>
    </Card>
  );
}

export default TimeMachineExpanded;
