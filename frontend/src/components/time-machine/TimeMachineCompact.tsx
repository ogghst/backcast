import React from "react";
import { Button, Space, Typography } from "antd";
import {
  ClockCircleOutlined,
  DownOutlined,
  UpOutlined,
} from "@ant-design/icons";
import { useTimeMachineStore } from "@/stores/useTimeMachineStore";
import { useTimeMachine } from "@/contexts/TimeMachineContext";
import { useProject } from "@/features/projects/api/useProjects";
import { ProjectBranchSelector } from "./ProjectBranchSelector";

const { Text } = Typography;

interface TimeMachineCompactProps {
  /** Project ID for context */
  projectId: string;
}

/**
 * Compact Time Machine display for the application header.
 *
 * Shows:
 * - Current selected date (or "Now")
 * - Current branch
 * - Expand button to open full timeline
 *
 * @example
 * ```tsx
 * // In AppLayout header
 * {currentProjectId && (
 *   <TimeMachineCompact projectId={currentProjectId} />
 * )}
 * ```
 */
export function TimeMachineCompact({ projectId }: TimeMachineCompactProps) {
  const { isHistorical } = useTimeMachine();
  const {
    isExpanded,
    toggleExpanded,
    getSelectedTime,
    resetToNow,
    setCurrentProject,
  } = useTimeMachineStore();

  // Fetch project data to get start_date
  // Note: Project data is fetched but not directly used here
  // It may be used by child components or for future enhancements
  useProject(projectId);

  // Ensure store knows about current project and initialize with start date
  // Note: We pass null for projectStartDate to initialize at "now" instead of project start date
  // This avoids issues where the project doesn't exist at its own start date in the bitemporal system
  // eslint-disable-next-line react-hooks/exhaustive-deps
  React.useEffect(() => {
    // Pass null to initialize at "now" instead of project's start_date
    setCurrentProject(projectId, null);
    return () => setCurrentProject(null);
  }, [projectId]); // Only depend on projectId, NOT on setCurrentProject (prevents infinite loop)

  const selectedTime = getSelectedTime();

  // Format display date
  const displayDate = selectedTime
    ? new Date(selectedTime).toLocaleDateString(undefined, {
        year: "numeric",
        month: "short",
        day: "numeric",
      })
    : "Now";

  const displayTime = selectedTime
    ? new Date(selectedTime).toLocaleTimeString(undefined, {
        hour: "2-digit",
        minute: "2-digit",
      })
    : "";

  return (
    <Space style={{ marginRight: 16 }}>
      {/* Time indicator */}
      <Button
        type={isHistorical ? "primary" : "text"}
        icon={<ClockCircleOutlined />}
        onClick={toggleExpanded}
        style={{
          display: "flex",
          alignItems: "center",
          gap: 8,
        }}
      >
        <Space size={4}>
          <Text strong={isHistorical}>{displayDate}</Text>
          {displayTime && (
            <Text type="secondary" style={{ fontSize: 12 }}>
              {displayTime}
            </Text>
          )}
          {isExpanded ? <UpOutlined /> : <DownOutlined />}
        </Space>
      </Button>

      {/* Branch Selector */}
      <ProjectBranchSelector projectId={projectId} />

      {/* Quick reset to now (only shown when viewing history) */}
      {isHistorical && (
        <Button size="small" onClick={resetToNow}>
          Reset to Now
        </Button>
      )}
    </Space>
  );
}

export default TimeMachineCompact;
