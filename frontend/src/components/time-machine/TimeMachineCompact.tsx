import React from "react";
import { theme, Space, Tooltip } from "antd";
import {
  ClockCircleOutlined,
  CaretDownOutlined,
  CaretUpOutlined,
  MergeCellsOutlined,
  SplitCellsOutlined,
  CheckCircleOutlined,
  ExclamationCircleOutlined,
  CloseCircleOutlined,
} from "@ant-design/icons";
import { useTimeMachineStore } from "@/stores/useTimeMachineStore";
import { useTimeMachine } from "@/contexts/TimeMachineContext";
import { useProject, useProjectBranches } from "@/features/projects/api/useProjects";

interface TimeMachineCompactProps {
  /** Project ID for context */
  projectId: string;
}

/**
 * Ultra-compact Time Machine display for the application header.
 *
 * Shows labels (no borders/backgrounds):
 * - Time with icon
 * - Branch name with icon
 * - View mode with icon (merged/isolated)
 * - Separate expand/collapse button
 *
 * All detailed controls are hidden until the user expands the panel.
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
  const { token } = theme.useToken();
  const { isHistorical } = useTimeMachine();
  const {
    isExpanded,
    toggleExpanded,
    getSelectedTime,
    getSelectedBranch,
    getViewMode,
    setCurrentProject,
  } = useTimeMachineStore();

  // Fetch project data and branches
  useProject(projectId);
  const { data: branches = [] } = useProjectBranches(projectId);

  // Ensure store knows about current project
  React.useEffect(() => {
    setCurrentProject(projectId, null);
    return () => setCurrentProject(null);
  }, [projectId, setCurrentProject]);

  const selectedTime = getSelectedTime();
  const selectedBranch = getSelectedBranch?.() ?? "main";
  const viewMode = getViewMode();

  // Find current branch with status info (for tooltip)
  const currentBranch = React.useMemo(() => {
    return branches.find((b) => b.name === selectedBranch);
  }, [branches, selectedBranch]);

  // Get status icon and color based on change order status
  const getStatusIcon = React.useMemo(() => {
    const status = currentBranch?.change_order_status;

    if (!status || status === "Draft") {
      return null; // No icon for Draft or main branch
    }

    if (status === "Approved") {
      return <CheckCircleOutlined style={{ color: token.colorSuccess, fontSize: 12 }} />;
    }

    if (status === "Pending") {
      return <ExclamationCircleOutlined style={{ color: token.colorWarning, fontSize: 12 }} />;
    }

    if (status === "Rejected") {
      return <CloseCircleOutlined style={{ color: token.colorError, fontSize: 12 }} />;
    }

    return null;
  }, [currentBranch?.change_order_status, token]);

  // Format display date
  const displayDate = selectedTime
    ? new Date(selectedTime).toLocaleDateString(undefined, {
        month: "short",
        day: "numeric",
      })
    : "Now";

  return (
    <Space size="small" style={{ marginRight: token.marginMD }}>
      {/* Time label */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: token.marginXS,
          color: isHistorical ? token.colorPrimary : token.colorTextSecondary,
          fontSize: token.fontSizeSM,
          fontWeight: isHistorical ? token.fontWeightStrong : undefined,
        }}
      >
        <ClockCircleOutlined style={{ fontSize: 12 }} />
        <span style={{ fontVariantNumeric: "tabular-nums" }}>
          {displayDate}
        </span>
        {/* Pulsing indicator for historical mode */}
        {isHistorical && (
          <span
            className="tm-pulse-indicator"
            style={{
              width: 6,
              height: 6,
              borderRadius: "50%",
              background: token.colorPrimary,
              animation: "tm-pulse 2s ease-in-out infinite",
            }}
            aria-hidden="true"
          />
        )}
      </div>

      {/* Branch label with status icon */}
      <Tooltip
        title={
          currentBranch?.change_order_status
            ? `${selectedBranch} (${currentBranch.change_order_status})`
            : selectedBranch
        }
      >
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: token.marginXS,
            color: token.colorText,
            fontSize: token.fontSizeSM,
            cursor: "default",
          }}
        >
          <span>{selectedBranch}</span>
          {getStatusIcon}
        </div>
      </Tooltip>

      {/* View mode label with icon */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: token.marginXS,
          color: token.colorTextSecondary,
          fontSize: token.fontSizeSM,
        }}
      >
        {viewMode === "merged" ? (
          <Tooltip title="Merged view: See data from current branch combined with main">
            <MergeCellsOutlined style={{ fontSize: 12 }} />
          </Tooltip>
        ) : (
          <Tooltip title="Isolated view: See only data from current branch">
            <SplitCellsOutlined style={{ fontSize: 12 }} />
          </Tooltip>
        )}
        <span>{viewMode === "merged" ? "Merged" : "Isolated"}</span>
      </div>

      {/* Separate expand button */}
      <button
        onClick={toggleExpanded}
        aria-label="Toggle time machine panel"
        type="button"
        style={{
          padding: token.paddingXS,
          border: "none",
          background: "transparent",
          color: token.colorTextSecondary,
          cursor: "pointer",
          borderRadius: token.borderRadiusSM,
          transition: "all 150ms ease",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
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
        {isExpanded ? <CaretUpOutlined /> : <CaretDownOutlined />}
      </button>
    </Space>
  );
}

export default TimeMachineCompact;
