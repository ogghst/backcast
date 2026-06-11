import { Form, Input, InputNumber, Select, Slider, theme } from "antd";
import { CollapsibleCard } from "@/components/common/CollapsibleCard";
import { AI_ROLE_OPTIONS } from "../../types";

interface ConfigurationSectionProps {
  agentType: "main" | "specialist";
  models: Array<{ id: string; display_name: string; provider_name?: string }>;
}

export const ConfigurationSection = ({ agentType, models }: ConfigurationSectionProps) => {
  const { token } = theme.useToken();

  return (
    <CollapsibleCard
      id="assistant-config"
      collapsed={false}
      title={
        <span style={{ fontSize: token.fontSizeLG, fontWeight: token.fontWeightStrong, color: token.colorText }}>
          Configuration
        </span>
      }
      style={{
        marginBottom: token.marginSM,
        borderRadius: token.borderRadiusLG,
        border: `1px solid ${token.colorBorder}`,
      }}
    >
      <div style={{ padding: token.paddingMD }}>
        {agentType === "specialist" && (
          <Form.Item
            name="presentation_prompt"
            label="Presentation Prompt"
            tooltip="Text shown to planner and supervisor agents to describe what this specialist can do. This is how other AI agents decide whether to delegate work here. Falls back to description if empty."
            rules={[{ max: 5000, message: "Presentation prompt must be 5000 characters or less" }]}
          >
            <Input.TextArea
              rows={3}
              placeholder="Describe this specialist's capabilities for the AI orchestrator..."
            />
          </Form.Item>
        )}

        <Form.Item
          name="system_prompt"
          label="System Prompt"
          tooltip="Internal instructions that define this agent's behavior, expertise, and operating rules"
          rules={[{ max: 10000, message: "System prompt must be 10000 characters or less" }]}
        >
          <Input.TextArea rows={4} placeholder="You are a helpful assistant..." />
        </Form.Item>

        <Form.Item
          name="default_role"
          label="Role"
          tooltip="The RBAC role determines which tools this assistant can use"
          rules={[{ required: true, message: "Please select a role" }]}
        >
          <Select placeholder="Select a role" allowClear>
            {AI_ROLE_OPTIONS.map((role) => (
              <Select.Option key={role.value} value={role.value}>
                <div>
                  <strong>{role.label}</strong>
                  <div style={{ fontSize: token.fontSizeSM, color: token.colorTextTertiary }}>
                    {role.description}
                  </div>
                </div>
              </Select.Option>
            ))}
          </Select>
        </Form.Item>

        <>
          <Form.Item
            name="model_id"
            label="Model"
            rules={agentType === "main" ? [{ required: true, message: "Please select a model" }] : undefined}
          >
            <Select placeholder="Select a model" allowClear={agentType === "specialist"}>
              {agentType === "specialist" && (
                <Select.Option value="">Use supervisor default</Select.Option>
              )}
              {models.map((model) => (
                <Select.Option key={model.id} value={model.id}>
                  {model.provider_name ? `${model.provider_name} / ${model.display_name}` : model.display_name}
                </Select.Option>
              ))}
            </Select>
          </Form.Item>

          {agentType === "main" ? (
            <>
              <Form.Item
                name="temperature"
                label="Temperature"
                initialValue={0.7}
                rules={[{ type: "number", min: 0, max: 2, message: "Temperature must be between 0 and 2" }]}
              >
                <Slider min={0} max={2} step={0.1} marks={{ 0: "Precise", 1: "Balanced", 2: "Creative" }} />
              </Form.Item>

              <Form.Item
                name="max_tokens"
                label="Max Tokens"
                initialValue={2048}
                rules={[{ type: "number", min: 1, max: 200000, message: "Max tokens must be between 1 and 200000" }]}
              >
                <Slider min={1} max={200000} step={100} marks={{ 1: "1", 100000: "100K", 200000: "200K" }} />
              </Form.Item>
            </>
          ) : (
            <>
              <Form.Item
                name="temperature"
                label="Temperature"
                tooltip="Override the supervisor's temperature for this specialist. Leave empty to inherit."
                rules={[{ type: "number", min: 0, max: 2, message: "Temperature must be between 0 and 2" }]}
              >
                <InputNumber min={0} max={2} step={0.1} placeholder="Inherit from supervisor" style={{ width: "100%" }} />
              </Form.Item>

              <Form.Item
                name="max_tokens"
                label="Max Tokens"
                tooltip="Override the supervisor's max tokens for this specialist. Leave empty to inherit."
                rules={[{ type: "number", min: 1, max: 200000, message: "Max tokens must be between 1 and 200000" }]}
              >
                <InputNumber min={1} max={200000} step={100} placeholder="Inherit from supervisor" style={{ width: "100%" }} />
              </Form.Item>
            </>
          )}

          {agentType === "main" && (
            <Form.Item
              name="recursion_limit"
              label="Recursion Limit"
              initialValue={25}
              tooltip="Maximum number of agent iterations (LangGraph default is 25)"
              rules={[{ type: "number", min: 1, max: 100, message: "Recursion limit must be between 1 and 100" }]}
            >
              <Slider min={1} max={100} step={5} marks={{ 1: "1", 25: "25 (default)", 50: "50", 100: "100" }} />
            </Form.Item>
          )}
        </>
      </div>
    </CollapsibleCard>
  );
};
