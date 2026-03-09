/**
 * AssistantSelector Component
 *
 * Dropdown component for selecting an AI assistant configuration.
 * Filters to show only active assistants.
 */

import { Select, Empty } from "antd";
import type { SelectProps } from "antd";
import { useAIAssistants } from "@/features/ai/api/useAIAssistants";
import type { AIAssistantPublic } from "@/features/ai/types";

export interface AssistantSelectorProps
  extends Omit<SelectProps<string>, "options" | "loading"> {
  value?: string;
  onChange: (assistantId: string) => void;
  disabled?: boolean;
}

export const AssistantSelector = ({
  value,
  onChange,
  disabled = false,
  ...selectProps
}: AssistantSelectorProps) => {
  // Fetch only active assistants
  const { data: assistants, isLoading } = useAIAssistants(false, {
    enabled: !disabled,
  });

  // Filter to active assistants only
  const activeAssistants = assistants?.filter((a) => a.is_active) ?? [];

  const options: SelectProps["options"] = activeAssistants.map(
    (assistant: AIAssistantPublic) => ({
      label: assistant.name,
      value: assistant.id,
      title: assistant.description || undefined,
    })
  );

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
