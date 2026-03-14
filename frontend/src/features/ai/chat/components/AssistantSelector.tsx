/**
 * AssistantSelector Component
 *
 * Dropdown component for selecting an AI assistant configuration.
 * Filters to show only active assistants.
 *
 * When locked (disabled), shows visual feedback with a lock icon
 * and displays the current assistant name prominently.
 */

import { Select, Empty, Tooltip } from "antd";
import type { SelectProps } from "antd";
import { LockOutlined } from "@ant-design/icons";
import { useAIAssistants } from "@/features/ai/api/useAIAssistants";
import type { AIAssistantPublic } from "@/features/ai/types";

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
            gap: 8,
            padding: "4px 12px",
            backgroundColor: disabled ? "rgba(0, 0, 0, 0.04)" : undefined,
            border: `1px solid rgba(0, 0, 0, 0.06)`,
            borderRadius: 6,
            cursor: "not-allowed",
            minWidth: 200,
          }}
        >
          <LockOutlined style={{ fontSize: 12, color: "rgba(0, 0, 0, 0.45)" }} />
          <span
            style={{
              fontSize: 14,
              fontWeight: 500,
              color: "rgba(0, 0, 0, 0.88)",
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
      placeholder="Select an AI assistant"
      options={options}
      notFoundContent={<Empty description="No active assistants available" />}
      filterOption={(input, option) =>
        (option?.label as string ?? "").toLowerCase().includes(input.toLowerCase())
      }
      showSearch
      allowClear={false}
      {...selectProps}
    />
  );
};
