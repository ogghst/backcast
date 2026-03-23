import { useEffect } from "react";
import { Modal, Form, Input, Select, Slider, Switch } from "antd";
import type { AIAssistantPublic, AIAssistantCreate, AIAssistantUpdate } from "../types";
import { ToolSelectorPanel } from "./ToolSelectorPanel";

interface AIAssistantModalProps {
  open: boolean;
  onCancel: () => void;
  onOk: (values: AIAssistantCreate | AIAssistantUpdate) => void | Promise<void>;
  confirmLoading: boolean;
  initialValues?: AIAssistantPublic | null;
  models?: Array<{ id: string; display_name: string; provider_name?: string }>;
}

export const AIAssistantModal = ({
  open,
  onCancel,
  onOk,
  confirmLoading,
  initialValues,
  models = [],
}: AIAssistantModalProps) => {
  const [form] = Form.useForm();
  const isEdit = !!initialValues;

  useEffect(() => {
    if (open) {
      if (initialValues) {
        form.setFieldsValue({
          name: initialValues.name,
          description: initialValues.description,
          model_id: initialValues.model_id,
          system_prompt: initialValues.system_prompt,
          temperature: initialValues.temperature,
          max_tokens: initialValues.max_tokens,
          recursion_limit: initialValues.recursion_limit,
          allowed_tools: initialValues.allowed_tools,
          is_active: initialValues.is_active,
        });
      } else {
        form.resetFields();
      }
    }
  }, [open, initialValues, form]);

  const handleSubmit = async () => {
    try {
      const values = await form.validateFields();
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
      destroyOnClose
      width={700}
    >
      <Form form={form} layout="vertical" name="ai_assistant_form">
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
          name="system_prompt"
          label="System Prompt"
          rules={[{ max: 10000, message: "System prompt must be 10000 characters or less" }]}
        >
          <Input.TextArea rows={4} placeholder="You are a helpful assistant..." />
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
          rules={[{ type: "number", min: 1, max: 500, message: "Recursion limit must be between 1 and 500" }]}
        >
          <Slider min={1} max={500} step={5} marks={{1: "1", 25: "25 (default)", 50: "50", 100: "100", 200: "200", 500: "500"}} />
        </Form.Item>

        <Form.Item name="allowed_tools" label="Allowed Tools">
          <ToolSelectorPanel />
        </Form.Item>

        {isEdit && (
          <Form.Item name="is_active" label="Active" valuePropName="checked">
            <Switch />
          </Form.Item>
        )}
      </Form>
    </Modal>
  );
};
