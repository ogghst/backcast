import { Spin, theme } from "antd";
import { BranchesOutlined } from "@ant-design/icons";
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
  const { token } = theme.useToken();

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

  return (
    <div
      className="tm-branch-selector"
      style={{
        position: "relative",
        minWidth: compact ? 160 : 200,
      }}
    >
      <select
        value={selectedBranch}
        onChange={(e) => handleBranchChange(e.target.value)}
        disabled={disabled || isLoading}
        aria-label="Select branch"
        style={{
          width: "100%",
          height: compact ? 32 : 36,
          padding: `0 ${token.paddingSM}px`,
          border: `1px solid ${token.colorBorder}`,
          borderRadius: token.borderRadiusSM,
          background: token.colorBgContainer,
          color: token.colorText,
          fontSize: compact ? token.fontSizeSM : 13,
          fontWeight: 500,
          cursor: "pointer",
          transition: "all 150ms ease",
          appearance: "none",
          WebkitAppearance: "none",
        }}
        onMouseEnter={(e) => {
          if (!disabled && !isLoading) {
            e.currentTarget.style.borderColor = token.colorPrimary;
          }
        }}
        onMouseLeave={(e) => {
          e.currentTarget.style.borderColor = token.colorBorder;
        }}
      >
        {options.map((branch) => (
          <option key={branch.value} value={branch.value}>
            {branch.isChangeOrderBranch && branch.changeOrderStatus
              ? `[${branch.changeOrderStatus}] ${branch.label}`
              : branch.label}
            {branch.isDefault ? " (default)" : ""}
          </option>
        ))}
      </select>
      {isLoading && options.length === 0 && (
        <Spin
          size="small"
          style={{
            position: "absolute",
            right: 16,
            top: "50%",
            transform: "translateY(-50%)",
          }}
        />
      )}
      {!isLoading && (
        <BranchesOutlined
          className="tm-branch-icon"
          style={{
            position: "absolute",
            right: token.paddingSM,
            top: "50%",
            transform: "translateY(-50%)",
            pointerEvents: "none",
            color: token.colorTextQuaternary,
            fontSize: 12,
          }}
        />
      )}
    </div>
  );
}

export default BranchSelector;
