import { Select, Badge, Space } from "antd";
import { BranchesOutlined } from "@ant-design/icons";
import type { BranchOption } from "./types";

interface BranchSelectorProps {
  /** Currently selected branch */
  value: string;
  /** Available branches */
  branches: BranchOption[];
  /** Called when branch selection changes */
  onChange: (branch: string) => void;
  /** Disable selector */
  disabled?: boolean;
  /** Compact mode for header */
  compact?: boolean;
}

// Status badge colors for change orders
const STATUS_BADGE_COLOR: Record<string, string> = {
  Draft: "default",
  Submitted: "blue",
  "Under Review": "processing",
  Approved: "success",
  Rejected: "error",
  Implemented: "purple",
  Closed: "default",
};

const STATUS_DOT_COLOR: Record<string, string> = {
  Draft: "#faad14", // Amber (F59E0B equivalent)
  Submitted: "#1890ff",
  "Under Review": "#52c41a",
  Approved: "#52c41a",
  Rejected: "#ff4d4f",
  Implemented: "#722ed1",
  Closed: "#8c8c8c",
};

/**
 * Branch selector dropdown for switching between branches.
 *
 * Displays status badges for change order branches (co-{code} pattern).
 *
 * @example
 * ```tsx
 * <BranchSelector
 *   value="main"
 *   branches={[
 *     { value: 'main', label: 'main', isDefault: true },
 *     { value: 'co-CO-2026-001', label: 'co-CO-2026-001', isChangeOrderBranch: true, changeOrderStatus: 'Draft' },
 *   ]}
 *   onChange={handleBranchChange}
 * />
 * ```
 */
export function BranchSelector({
  value,
  branches,
  onChange,
  disabled = false,
  compact = false,
}: BranchSelectorProps) {
  return (
    <Select
      value={value}
      onChange={onChange}
      disabled={disabled}
      style={{ minWidth: compact ? 120 : 180 }}
      size={compact ? "small" : "middle"}
      suffixIcon={<BranchesOutlined />}
      options={branches.map((branch) => ({
        value: branch.value,
        label: (
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
            <Space size="small">
              {branch.isChangeOrderBranch ? (
                <Badge
                  color={STATUS_DOT_COLOR[branch.changeOrderStatus || "Draft"]}
                  text={
                    <span style={{ fontSize: compact ? 12 : 13 }}>
                      {branch.label}
                    </span>
                  }
                />
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
            {branch.isChangeOrderBranch && branch.changeOrderStatus && (
              <Badge
                status={STATUS_BADGE_COLOR[branch.changeOrderStatus] as any}
                text={
                  <span style={{ fontSize: compact ? 11 : 12, color: "#888" }}>
                    {branch.changeOrderStatus}
                  </span>
                }
              />
            )}
          </div>
        ),
      }))}
    />
  );
}

export default BranchSelector;
