import { Segmented } from "antd";
import { MergeCellsOutlined, SplitCellsOutlined } from "@ant-design/icons";
import { useTimeMachineStore, type BranchMode } from "@/stores/useTimeMachineStore";
import { useTimeMachine } from "@/contexts/TimeMachineContext";

interface ViewModeSelectorProps {
  /** Compact mode for smaller displays */
  compact?: boolean;
}

/**
 * View mode selector for branch isolation control.
 *
 * Allows users to choose between:
 * - "merged": Combine current branch with main (current branch takes precedence)
 * - "isolated": Only return entities from current branch
 *
 * @example
 * ```tsx
 * <ViewModeSelector compact />
 * ```
 */
export function ViewModeSelector({ compact = false }: ViewModeSelectorProps) {
  const viewMode = useTimeMachineStore((state) => state.getViewMode());
  const selectViewMode = useTimeMachineStore((state) => state.selectViewMode);
  const { invalidateQueries } = useTimeMachine();

  const handleChange = (value: BranchMode) => {
    selectViewMode(value);
    // Invalidate queries to refresh data with new mode
    invalidateQueries();
  };

  const options = [
    {
      value: "merged" as BranchMode,
      icon: <MergeCellsOutlined />,
      label: compact ? undefined : "Merged",
    },
    {
      value: "isolated" as BranchMode,
      icon: <SplitCellsOutlined />,
      label: compact ? undefined : "Isolated",
    },
  ];

  return (
    <Segmented
      value={viewMode}
      onChange={handleChange}
      options={options}
      size={compact ? "small" : "middle"}
      style={{ fontSize: compact ? 12 : 13 }}
    />
  );
}

export default ViewModeSelector;
