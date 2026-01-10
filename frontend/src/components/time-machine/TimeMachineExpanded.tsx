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
import {
  CloseOutlined,
  ReloadOutlined,
  CalendarOutlined,
} from "@ant-design/icons";
import dayjs from "dayjs";

import { useTimeMachineStore } from "@/stores/useTimeMachineStore";
import { useTimeMachine } from "@/contexts/TimeMachineContext";
import { TimelineSlider } from "./TimelineSlider";
import { BranchSelector } from "./BranchSelector";
import { QuickJumpButtons, calculateDateFromPreset } from "./QuickJumpButtons";
import type {
  TimelineEvent,
  BranchOption,
  QuickJumpPreset,
  ProjectTimelineData,
} from "./types";

const { Text, Title } = Typography;

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
 * - Branch selector
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
 *       branches: ['main', 'co-001'],
 *       events: [],
 *     }}
 *   />
 * )}
 * ```
 */
export function TimeMachineExpanded({
  projectId,
  projectName,
  timelineData,
  isLoading = false,
}: TimeMachineExpandedProps) {
  const { isHistorical, invalidateQueries } = useTimeMachine();
  const {
    toggleExpanded,
    getSelectedTime,
    getSelectedBranch,
    selectTime,
    selectBranch,
    resetToNow,
  } = useTimeMachineStore();

  const selectedTime = getSelectedTime();
  const selectedBranchValue = getSelectedBranch();

  // Parse selected time
  const selectedDate = useMemo(
    () => (selectedTime ? new Date(selectedTime) : null),
    [selectedTime]
  );

  // Default date range if not provided
  const minDate =
    timelineData?.startDate || new Date(Date.now() - 365 * 24 * 60 * 60 * 1000);
  const maxDate = timelineData?.endDate || new Date();

  // Convert branches to options
  const branchOptions: BranchOption[] = useMemo(() => {
    const branches = timelineData?.branches || ["main"];
    return branches.map((branch) => ({
      value: branch,
      label: branch,
      isDefault: branch === "main",
    }));
  }, [timelineData?.branches]);

  // Handle time selection with query invalidation
  const handleSelectTime = useCallback(
    (date: Date | null) => {
      selectTime(date);
      invalidateQueries();
    },
    [selectTime, invalidateQueries]
  );

  // Handle branch selection with query invalidation
  const handleSelectBranch = useCallback(
    (branch: string) => {
      selectBranch(branch);
      invalidateQueries();
    },
    [selectBranch, invalidateQueries]
  );

  // Handle quick jump
  const handleQuickJump = useCallback(
    (preset: QuickJumpPreset) => {
      const date = calculateDateFromPreset(preset, timelineData?.startDate);
      handleSelectTime(date);
    },
    [timelineData?.startDate, handleSelectTime]
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
        {/* Left: Branch selector + Quick jumps */}
        <Space>
          <BranchSelector
            value={selectedBranchValue}
            branches={branchOptions}
            onChange={handleSelectBranch}
            disabled={isLoading}
          />

          <Divider type="vertical" />

          <QuickJumpButtons onJump={handleQuickJump} disabled={isLoading} />
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
