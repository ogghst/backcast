import { useEffect } from "react";
import { Modal, Form } from "antd";
import type { AIAssistantPublic, AIAssistantCreate, AIAssistantUpdate } from "../types";
import { GeneralSection } from "./modal/GeneralSection";
import { ConfigurationSection } from "./modal/ConfigurationSection";
import { PlanningStrategySection } from "./modal/PlanningStrategySection";
import { ToolsOutputSection } from "./modal/ToolsOutputSection";
import { DelegationSection } from "./modal/DelegationSection";

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
  const isEdit = !!initialValues;
  const agentType = Form.useWatch("agent_type", form) ?? initialValues?.agent_type ?? "specialist";

  useEffect(() => {
    if (open) {
      if (initialValues) {
        const baseValues = {
          name: initialValues.name,
          description: initialValues.description,
          presentation_prompt: initialValues.presentation_prompt,
          system_prompt: initialValues.system_prompt,
          planner_prompt: initialValues.planner_prompt,
          supervisor_prompt: initialValues.supervisor_prompt,
          // default_role only for main agents — specialists inherit from their main assistant
          ...(initialValues.agent_type === "main" && { default_role: initialValues.default_role }),
          is_active: initialValues.is_active,
          agent_type: initialValues.agent_type,
          allowed_tools: initialValues.allowed_tools || [],
          structured_output_schema: initialValues.structured_output_schema,
          delegation_config: {
            direct_tools: initialValues.delegation_config?.direct_tools || [],
            allowed_specialists: initialValues.delegation_config?.allowed_specialists || [],
          },
        };
        form.setFieldsValue({
          ...baseValues,
          model_id: initialValues.model_id ?? "",
          temperature: initialValues.temperature,
          max_tokens: initialValues.max_tokens,
          ...(initialValues.agent_type === "main" && { recursion_limit: initialValues.recursion_limit }),
        });
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
        // Specialist agents inherit recursion_limit and default_role from main agent
        delete values.recursion_limit;
        delete values.default_role;
      }
      if (values.model_id === "") values.model_id = null;
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
      <Form form={form} layout="vertical" name="ai_assistant_form">
        <GeneralSection isEdit={isEdit} />
        <ConfigurationSection agentType={agentType} models={models} />
        {agentType === "main" && <PlanningStrategySection />}
        {agentType === "specialist" && <ToolsOutputSection />}
        {agentType === "main" && <DelegationSection specialists={specialists} />}
      </Form>
    </Modal>
  );
};
