/**
 * AssistantSelector Component
 *
 * Dropdown component for selecting an AI assistant configuration.
 * Mobile-optimized with flexible sizing and cleaner locked state.
 *
 * Design: Industrial Technical Minimalism
 * - Flexible width for mobile layouts
 * - Monospace font for technical feel
 * - Subtle locked state with icon
 * - Clear visual hierarchy
 */

import { Select, Empty, Tooltip } from "antd";
import type { SelectProps } from "antd";
import { LockOutlined } from "@ant-design/icons";
import { useAIAssistants } from "@/features/ai/api/useAIAssistants";
import type { AIAssistantPublic } from "@/features/ai/types";
import { useThemeTokens } from "@/hooks/useThemeTokens";

export interface AssistantSelectorProps
  extends Omit<SelectProps<string>, "options" | "loading"> {
  value?: string;
  onChange: (assistantId: string) => void;
  disabled?: boolean;
  /** Whether to show the locked state with visual feedback */
  locked?: boolean;
}

export const AssistantSelector = ({
  value,
  onChange,
  disabled = false,
  locked = false,
  ...selectProps
}: AssistantSelectorProps) => {
  const { spacing, typography } = useThemeTokens();

  // Fetch only active assistants
  const { data: assistants, isLoading } = useAIAssistants(false, {
    enabled: !disabled,
  });

  // Filter to active assistants only
  const activeAssistants = assistants?.filter((a) => a.is_active) ?? [];

  // Find the current assistant for locked state display
  const currentAssistant = activeAssistants.find((a) => a.id === value);

  const options: SelectProps["options"] = activeAssistants.map(
    (assistant: AIAssistantPublic) => ({
      label: assistant.name,
      value: assistant.id,
      title: assistant.description || undefined,
    })
  );

  // When locked, show visual feedback
  if (locked && value && currentAssistant) {
    return (
      <Tooltip title="Cannot change assistant during active conversation. Start a new chat to switch assistants.">
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: spacing.xs,
            padding: `${spacing.xs}px ${spacing.sm}px`,
            backgroundColor: disabled ? "rgba(0, 0, 0, 0.04)" : undefined,
            border: `1px solid rgba(0, 0, 0, 0.08)`,
            borderRadius: 8,
            cursor: "not-allowed",
            height: 36,
            boxSizing: "border-box",
          }}
        >
          <LockOutlined
            style={{
              fontSize: typography.sizes.sm,
              color: "rgba(0, 0, 0, 0.4)",
            }}
          />
          <span
            style={{
              fontSize: typography.sizes.sm,
              fontWeight: typography.weights.medium,
              color: "rgba(0, 0, 0, 0.85)",
              overflow: "hidden",
              textOverflow: "ellipsis",
              whiteSpace: "nowrap",
            }}
          >
            {currentAssistant.name}
          </span>
        </div>
      </Tooltip>
    );
  }

  return (
    <Select
      value={value}
      onChange={onChange}
      disabled={disabled || isLoading}
      loading={isLoading}
      placeholder="Select AI Assistant"
      options={options}
      notFoundContent={<Empty description="No active assistants" image={Empty.PRESENTED_IMAGE_SIMPLE} />}
      filterOption={(input, option) =>
        (option?.label as string ?? "").toLowerCase().includes(input.toLowerCase())
      }
      showSearch
      allowClear={false}
      {...selectProps}
      style={{
        fontSize: typography.sizes.sm,
        ...selectProps.style,
      }}
    />
  );
};
