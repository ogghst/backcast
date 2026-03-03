import { Select, Space, Spin } from "antd";
import {
  BranchesOutlined,
  EditOutlined,
  SendOutlined,
  SearchOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  PlayCircleOutlined,
  StopOutlined,
} from "@ant-design/icons";
import React from "react";
import { useProjectBranches } from "@/features/projects/api/useProjects";
import { useTimeMachineStore } from "@/stores/useTimeMachineStore";
import type { BranchOption } from "./types";

interface BranchSelectorProps {
  /** Project ID to fetch branches for */
  projectId: string;
  /** Called when branch selection changes (optional) */
  onChange?: (branch: string) => void;
  /** Disable selector */
  disabled?: boolean;
  /** Compact mode for header */
  compact?: boolean;
}

// Map status to Ant Design Icon
const STATUS_ICON: Record<string, React.ReactNode> = {
  Draft: <EditOutlined style={{ color: "#faad14" }} />, // Amber
  Submitted: <SendOutlined style={{ color: "#1890ff" }} />, // Blue
  "Under Review": <SearchOutlined style={{ color: "#52c41a" }} />, // Green
  Approved: <CheckCircleOutlined style={{ color: "#52c41a" }} />, // Green
  Rejected: <CloseCircleOutlined style={{ color: "#ff4d4f" }} />, // Red
  Implemented: <PlayCircleOutlined style={{ color: "#722ed1" }} />, // Purple
  Closed: <StopOutlined style={{ color: "#8c8c8c" }} />, // Gray
};

/**
 * Project-aware Branch selector dropdown for switching between branches.
 *
 * Fetches branches automatically for the given projectId and persists
 * selection to the TimeMachineStore.
 *
 * Displays status badges for change order branches (BR-{code} pattern).
 *
 * @example
 * ```tsx
 * <BranchSelector projectId="proj-123" />
 * ```
 */
export function BranchSelector({
  projectId,
  onChange,
  disabled = false,
  compact = false,
}: BranchSelectorProps) {
  // Fetch branches for this project
  const { data: branches = [], isLoading } = useProjectBranches(projectId);

  // Get selected branch and action from store
  const selectedBranch = useTimeMachineStore(
    (state) => state.projectSettings[projectId]?.selectedBranch ?? "main",
  );
  const selectBranch = useTimeMachineStore((state) => state.selectBranch);

  const handleBranchChange = (value: string) => {
    selectBranch(value);
    if (onChange) {
      onChange(value);
    }
  };

  const options: BranchOption[] = branches.map((b) => ({
    value: b.name,
    label: b.name,
    isDefault: b.is_default,
    isChangeOrderBranch: b.type === "change_order",
    changeOrderStatus:
      b.change_order_status as BranchOption["changeOrderStatus"],
  }));

  if (isLoading && options.length === 0) {
    return (
      <Select
        disabled
        value={selectedBranch}
        style={{ minWidth: compact ? 180 : 240 }}
        size={compact ? "small" : "middle"}
        suffixIcon={<Spin size="small" />}
        options={[{ value: selectedBranch, label: selectedBranch }]}
      />
    );
  }

  return (
    <Select
      value={selectedBranch}
      onChange={handleBranchChange}
      disabled={disabled}
      style={{ minWidth: compact ? 180 : 240 }}
      size={compact ? "small" : "middle"}
      suffixIcon={<BranchesOutlined />}
      options={options.map((branch) => ({
        value: branch.value,
        label: (
          <Space size="small">
            {branch.isChangeOrderBranch ? (
              <Space size="small" align="center">
                {STATUS_ICON[branch.changeOrderStatus || "Draft"] || (
                  <EditOutlined style={{ color: "#faad14" }} />
                )}
                <span style={{ fontSize: compact ? 12 : 13 }}>
                  {branch.label}
                </span>
              </Space>
            ) : (
              <span style={{ fontSize: compact ? 12 : 13 }}>
                {branch.label}
              </span>
            )}
            {branch.isDefault && (
              <span style={{ color: "#888", marginLeft: 4, fontSize: 11 }}>
                (default)
              </span>
            )}
          </Space>
        ),
      }))}
    />
  );
}

export default BranchSelector;
