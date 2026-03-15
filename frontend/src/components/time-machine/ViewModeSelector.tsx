import { theme } from "antd";
import {
  useTimeMachineStore,
  type BranchMode,
} from "@/stores/useTimeMachineStore";
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
  const { token } = theme.useToken();
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
      label: "Merged",
    },
    {
      value: "isolated" as BranchMode,
      label: "Isolated",
    },
  ];

  const height = compact ? 32 : 36;

  return (
    <div
      className="tm-view-mode"
      role="radiogroup"
      aria-label="View mode"
      style={{
        display: "inline-flex",
        background: token.colorFillSecondary,
        padding: 2,
        borderRadius: token.borderRadiusSM,
        gap: 2,
        height,
      }}
    >
      {options.map((option) => (
        <button
          key={option.value}
          onClick={() => handleChange(option.value)}
          type="button"
          role="radio"
          aria-checked={viewMode === option.value}
          aria-label={option.label}
          style={{
            padding: `0 ${token.paddingSM}px`,
            border: "none",
            background:
              viewMode === option.value
                ? token.colorBgContainer
                : "transparent",
            color:
              viewMode === option.value
                ? token.colorPrimary
                : token.colorTextSecondary,
            fontSize: compact ? token.fontSizeSM : 12,
            fontWeight: 600,
            borderRadius: token.borderRadiusXS,
            cursor: "pointer",
            transition: "all 150ms ease",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            gap: token.marginXS,
            height: "100%",
            boxShadow:
              viewMode === option.value
                ? "0 1px 2px rgba(0, 0, 0, 0.05)"
                : "none",
          }}
          onMouseEnter={(e) => {
            if (viewMode !== option.value) {
              e.currentTarget.style.color = token.colorText;
            }
          }}
          onMouseLeave={(e) => {
            if (viewMode !== option.value) {
              e.currentTarget.style.color = token.colorTextSecondary;
            }
          }}
        >
          <span>{option.label}</span>
        </button>
      ))}
    </div>
  );
}

export default ViewModeSelector;
