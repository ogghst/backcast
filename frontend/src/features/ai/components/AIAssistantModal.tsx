import { useEffect } from "react";
import { Alert, Checkbox, Modal, Form, Input, Radio, Select, Slider, Space, Switch, theme } from "antd";
import { LockOutlined } from "@ant-design/icons";
import type { AIAssistantPublic, AIAssistantCreate, AIAssistantUpdate } from "../types";
import { AI_ROLE_OPTIONS } from "../types";
import { CollapsibleCard } from "@/components/common/CollapsibleCard";
import { ToolSelectorPanel } from "./ToolSelectorPanel";

interface AIAssistantModalProps {
  open: boolean;
  onCancel: () => void;
  onOk: (values: AIAssistantCreate | AIAssistantUpdate) => void | Promise<void>;
  confirmLoading: boolean;
  initialValues?: AIAssistantPublic | null;
  models?: Array<{ id: string; display_name: string; provider_name?: string }>;
  specialists?: AIAssistantPublic[];
}

export const AIAssistantModal = ({
  open,
  onCancel,
  onOk,
  confirmLoading,
  initialValues,
  models = [],
  specialists = [],
}: AIAssistantModalProps) => {
  const [form] = Form.useForm();
  const { token } = theme.useToken();
  const isEdit = !!initialValues;
  const agentType = Form.useWatch("agent_type", form) ?? initialValues?.agent_type ?? "specialist";

  useEffect(() => {
    if (open) {
      if (initialValues) {
        const baseValues = {
          name: initialValues.name,
          description: initialValues.description,
          system_prompt: initialValues.system_prompt,
          planner_prompt: initialValues.planner_prompt,
          supervisor_prompt: initialValues.supervisor_prompt,
          default_role: initialValues.default_role,
          is_active: initialValues.is_active,
          agent_type: initialValues.agent_type,
          allowed_tools: initialValues.allowed_tools || [],
          structured_output_schema: initialValues.structured_output_schema,
          delegation_config: {
            direct_tools: initialValues.delegation_config?.direct_tools || [],
            allowed_specialists: initialValues.delegation_config?.allowed_specialists || [],
          },
        };
        // Provider-related fields only for main agents
        if (initialValues.agent_type === "main") {
          form.setFieldsValue({
            ...baseValues,
            model_id: initialValues.model_id,
            temperature: initialValues.temperature,
            max_tokens: initialValues.max_tokens,
            recursion_limit: initialValues.recursion_limit,
          });
        } else {
          form.setFieldsValue(baseValues);
        }
      } else {
        form.resetFields();
      }
    }
  }, [open, initialValues, form]);

  const handleSubmit = async () => {
    try {
      const values = await form.validateFields();
      // Clean up fields based on agent type
      if (values.agent_type === "main") {
        delete values.allowed_tools;
        delete values.structured_output_schema;
      } else {
        delete values.delegation_config;
        // Specialist agents inherit provider settings from main agent
        delete values.model_id;
        delete values.temperature;
        delete values.max_tokens;
        delete values.recursion_limit;
      }
      await onOk(values);
    } catch (error) {
      console.error("Form submission error:", error);
    }
  };

  return (
    <Modal
      title={isEdit ? "Edit AI Assistant" : "Create AI Assistant"}
      open={open}
      onCancel={onCancel}
      onOk={handleSubmit}
      okText={isEdit ? "Save" : "Create"}
      okButtonProps={{ "data-testid": "submit-assistant-btn" }}
      confirmLoading={confirmLoading}
      destroyOnHidden
      width={800}
    >
      {isEdit && initialValues?.is_system && (
        <Alert
          message="System Assistant"
          description="This is a system-defined assistant. It cannot be deleted, only disabled."
          type="info"
          showIcon
          icon={<LockOutlined />}
          style={{ marginBottom: 16 }}
          banner
        />
      )}
      <Form form={form} layout="vertical" name="ai_assistant_form">
        {/* Section 1: General */}
        <CollapsibleCard
          id="assistant-general"
          collapsed={false}
          title={
            <span style={{ fontSize: token.fontSizeLG, fontWeight: token.fontWeightStrong, color: token.colorText }}>
              General
            </span>
          }
          style={{
            marginBottom: token.marginSM,
            borderRadius: token.borderRadiusLG,
            border: `1px solid ${token.colorBorder}`,
          }}
        >
          <div style={{ padding: token.paddingMD }}>
            <Form.Item
              name="name"
              label="Name"
              rules={[
                { required: true, message: "Please enter a name" },
                { max: 255, message: "Name must be 255 characters or less" },
              ]}
            >
              <Input placeholder="My AI Assistant" />
            </Form.Item>

            <Form.Item
              name="description"
              label="Description"
              rules={[{ max: 2000, message: "Description must be 2000 characters or less" }]}
            >
              <Input.TextArea rows={2} placeholder="What does this assistant do?" />
            </Form.Item>

            <Form.Item
              name="agent_type"
              label="Agent Type"
              initialValue="specialist"
              tooltip="Main agents orchestrate specialist agents. Specialist agents focus on specific tasks."
              rules={[{ required: true, message: "Please select an agent type" }]}
            >
              <Radio.Group disabled={isEdit}>
                <Radio value="main">Main Agent</Radio>
                <Radio value="specialist">Specialist Agent</Radio>
              </Radio.Group>
            </Form.Item>

            {isEdit && (
              <Form.Item name="is_active" label="Active" valuePropName="checked">
                <Switch />
              </Form.Item>
            )}
          </div>
        </CollapsibleCard>

        {/* Section 2: Configuration */}
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
            <Form.Item
              name="system_prompt"
              label="System Prompt"
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

            {agentType === "main" && (
              <>
                <Form.Item
                  name="model_id"
                  label="Model"
                  rules={[{ required: true, message: "Please select a model" }]}
                >
                  <Select placeholder="Select a model">
                    {models.map((model) => (
                      <Select.Option key={model.id} value={model.id}>
                        {model.display_name} {model.provider_name ? `(${model.provider_name})` : ""}
                      </Select.Option>
                    ))}
                  </Select>
                </Form.Item>

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

                <Form.Item
                  name="recursion_limit"
                  label="Recursion Limit"
                  initialValue={25}
                  tooltip="Maximum number of agent iterations (LangGraph default is 25)"
                  rules={[{ type: "number", min: 1, max: 100, message: "Recursion limit must be between 1 and 100" }]}
                >
                  <Slider min={1} max={100} step={5} marks={{ 1: "1", 25: "25 (default)", 50: "50", 100: "100" }} />
                </Form.Item>
              </>
            )}
          </div>
        </CollapsibleCard>

        {/* Section 3: Planning Strategy (main only) */}
        {agentType === "main" && (
          <CollapsibleCard
            id="assistant-planning"
            collapsed={true}
            title={
              <span style={{ fontSize: token.fontSizeLG, fontWeight: token.fontWeightStrong, color: token.colorText }}>
                Planning Strategy
              </span>
            }
            style={{
              marginBottom: token.marginSM,
              borderRadius: token.borderRadiusLG,
              border: `1px solid ${token.colorBorder}`,
            }}
          >
            <div style={{ padding: token.paddingMD }}>
              <Alert
                message="Advanced"
                description="Customize how the AI plans and decomposes requests into specialist tasks. Leave blank to use the default planner. The {specialist_section} placeholder is replaced with the dynamic specialist list."
                type="info"
                showIcon
                style={{ marginBottom: 16 }}
              />
              <Form.Item
                name="planner_prompt"
                label="Planner Prompt"
                tooltip="Controls how the AI decomposes user requests into specialist tasks. Include {specialist_section} for the dynamic specialist list."
                rules={[{ max: 10000, message: "Planner prompt must be 10000 characters or less" }]}
              >
                <Input.TextArea
                  rows={8}
                  placeholder="Leave blank to use the default planner strategy..."
                />
              </Form.Item>
              <Form.Item
                name="supervisor_prompt"
                label="Supervisor Prompt"
                tooltip="Controls how the supervisor agent coordinates specialist delegation. Include {specialist_section} for the dynamic specialist list. Leave blank to use the system prompt or default."
                rules={[{ max: 10000, message: "Supervisor prompt must be 10000 characters or less" }]}
              >
                <Input.TextArea
                  rows={8}
                  placeholder="Leave blank to use the system prompt or default supervisor..."
                />
              </Form.Item>
            </div>
          </CollapsibleCard>
        )}

        {/* Section 4a: Tools & Output (specialist only) */}
        {agentType === "specialist" && (
          <CollapsibleCard
            id="assistant-tools"
            collapsed={true}
            title={
              <span style={{ fontSize: token.fontSizeLG, fontWeight: token.fontWeightStrong, color: token.colorText }}>
                Tools &amp; Output
              </span>
            }
            style={{
              marginBottom: token.marginSM,
              borderRadius: token.borderRadiusLG,
              border: `1px solid ${token.colorBorder}`,
            }}
          >
            <div style={{ padding: token.paddingMD }}>
              <Form.Item
                name="allowed_tools"
                label="Allowed Tools"
                tooltip="Tools this specialist can use directly. Leave empty for all tools."
              >
                <ToolSelectorPanel />
              </Form.Item>
              <Form.Item
                name="structured_output_schema"
                label="Structured Output Schema"
                tooltip="Fully qualified class name of a Pydantic model (e.g. app.models.schemas.evm.EVMMetricsRead)"
                rules={[{ max: 100, message: "Schema must be 100 characters or less" }]}
              >
                <Input placeholder="app.models.schemas.evm.EVMMetricsRead" />
              </Form.Item>
            </div>
          </CollapsibleCard>
        )}

        {/* Section 4b: Delegation (main only) */}
        {agentType === "main" && (
          <CollapsibleCard
            id="assistant-delegation"
            collapsed={true}
            title={
              <span style={{ fontSize: token.fontSizeLG, fontWeight: token.fontWeightStrong, color: token.colorText }}>
                Delegation
              </span>
            }
            style={{
              marginBottom: token.marginSM,
              borderRadius: token.borderRadiusLG,
              border: `1px solid ${token.colorBorder}`,
            }}
          >
            <div style={{ padding: token.paddingMD }}>
              <Form.Item
                name={["delegation_config", "direct_tools"]}
                label="Direct Tools"
                tooltip="Tools the main agent can use directly without delegating to specialists"
              >
                <ToolSelectorPanel />
              </Form.Item>
              <Form.Item
                name={["delegation_config", "allowed_specialists"]}
                label="Allowed Specialists"
                tooltip="Specialists this main agent can delegate to. Leave empty for all specialists."
              >
                <Checkbox.Group
                  style={{ display: "flex", flexDirection: "column", gap: 8 }}
                >
                  {specialists
                    .filter(s => s.is_active)
                    .map(s => (
                      <Checkbox key={s.name} value={s.name}>
                        <Space>
                          <span>{s.name}</span>
                          {s.description && (
                            <span style={{ color: token.colorTextSecondary, fontSize: token.fontSizeSM }}>
                              — {s.description}
                            </span>
                          )}
                        </Space>
                      </Checkbox>
                    ))}
                </Checkbox.Group>
              </Form.Item>
            </div>
          </CollapsibleCard>
        )}

      </Form>
    </Modal>
  );
};
