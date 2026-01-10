import React from "react";
import { Select } from "antd";
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

/**
 * Branch selector dropdown for switching between branches.
 *
 * @example
 * ```tsx
 * <BranchSelector
 *   value="main"
 *   branches={[
 *     { value: 'main', label: 'main', isDefault: true },
 *     { value: 'co-001', label: 'Change Order 001' },
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
      style={{ minWidth: compact ? 100 : 150 }}
      size={compact ? "small" : "middle"}
      suffixIcon={<BranchesOutlined />}
      options={branches.map((branch) => ({
        value: branch.value,
        label: (
          <span>
            {branch.label}
            {branch.isDefault && (
              <span style={{ color: "#888", marginLeft: 8, fontSize: 12 }}>
                (default)
              </span>
            )}
          </span>
        ),
      }))}
    />
  );
}

export default BranchSelector;
