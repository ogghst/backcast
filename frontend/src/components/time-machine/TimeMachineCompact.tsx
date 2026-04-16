import React, { useState, useEffect } from "react";
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
  BranchesOutlined,
} from "@ant-design/icons";
import { useTimeMachineStore } from "@/stores/useTimeMachineStore";
import { useTimeMachine } from "@/contexts/TimeMachineContext";
import { useProject, useProjectBranches } from "@/features/projects/api/useProjects";
import { formatDate } from "@/utils/formatters";

// Mobile breakpoint for compact display
const MOBILE_BREAKPOINT = 600;

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
  const [isMobile, setIsMobile] = useState(false);
  const {
    isExpanded,
    toggleExpanded,
    getSelectedTime,
    getSelectedBranch,
    getViewMode,
    setCurrentProject,
  } = useTimeMachineStore();

  // Detect mobile screen size for compact display
  useEffect(() => {
    const checkMobile = () => {
      setIsMobile(window.innerWidth < MOBILE_BREAKPOINT);
    };

    checkMobile();
    window.addEventListener("resize", checkMobile);
    return () => window.removeEventListener("resize", checkMobile);
  }, []);

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
      return <CheckCircleOutlined style={{ color: token.colorSuccess, fontSize: token.fontSize }} />;
    }

    if (status === "Pending") {
      return <ExclamationCircleOutlined style={{ color: token.colorWarning, fontSize: token.fontSize }} />;
    }

    if (status === "Rejected") {
      return <CloseCircleOutlined style={{ color: token.colorError, fontSize: token.fontSize }} />;
    }

    return null;
  }, [currentBranch?.change_order_status, token]);

  // Format display date
  const displayDate = selectedTime
    ? formatDate(selectedTime, { style: "medium" })
    : "Now";

  return (
    <Space size={isMobile ? token.marginXS : "small"} style={{ marginRight: isMobile ? token.marginXS : token.marginMD }}>
      {/* Time label */}
      <Tooltip title={isMobile ? displayDate : undefined}>
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: isMobile ? token.marginXXS : token.marginXS,
            color: isHistorical ? token.colorPrimary : token.colorText,
            fontSize: isMobile ? token.fontSizeSM : token.fontSize,
          }}
        >
          <ClockCircleOutlined style={{ fontSize: isMobile ? token.fontSizeSM : token.fontSize }} />
          {!isMobile && (
            <span style={{ fontVariantNumeric: "tabular-nums" }}>
              {displayDate}
            </span>
          )}
          {/* Pulsing indicator for historical mode */}
          {isHistorical && (
            <span
              className="tm-pulse-indicator"
              style={{
                width: isMobile ? 4 : 6,
                height: isMobile ? 4 : 6,
                borderRadius: "50%",
                background: token.colorPrimary,
                animation: "tm-pulse 2s ease-in-out infinite",
              }}
              aria-hidden="true"
            />
          )}
        </div>
      </Tooltip>

      {/* Branch label with icon and status indicator */}
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
            gap: isMobile ? token.marginXXS : token.marginXS,
            color: token.colorText,
            fontSize: isMobile ? token.fontSizeSM : token.fontSize,
            cursor: "default",
          }}
        >
          <BranchesOutlined style={{ fontSize: isMobile ? token.fontSizeSM : token.fontSize }} />
          {!isMobile && <span>{selectedBranch}</span>}
          {getStatusIcon}
        </div>
      </Tooltip>

      {/* View mode label with icon */}
      {viewMode === "merged" ? (
        <Tooltip title="Merged view: See data from current branch combined with main">
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: isMobile ? token.marginXXS : token.marginXS,
              color: token.colorText,
              fontSize: isMobile ? token.fontSizeSM : token.fontSize,
            }}
          >
            <MergeCellsOutlined style={{ fontSize: isMobile ? token.fontSizeSM : token.fontSize }} />
            {!isMobile && <span>Merged</span>}
          </div>
        </Tooltip>
      ) : (
        <Tooltip title="Isolated view: See only data from current branch">
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: isMobile ? token.marginXXS : token.marginXS,
              color: token.colorText,
              fontSize: isMobile ? token.fontSizeSM : token.fontSize,
            }}
          >
            <SplitCellsOutlined style={{ fontSize: isMobile ? token.fontSizeSM : token.fontSize }} />
            {!isMobile && <span>Isolated</span>}
          </div>
        </Tooltip>
      )}

      {/* Separate expand button */}
      <button
        onClick={toggleExpanded}
        aria-label="Toggle time machine panel"
        type="button"
        style={{
          padding: isMobile ? token.paddingXXS : token.paddingXS,
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
