import { useEffect } from "react";
import { Modal, Form, Input, Switch } from "antd";
import type { AIModelPublic, AIModelCreate } from "../types";

interface AIModelModalProps {
  open: boolean;
  onCancel: () => void;
  onOk: (values: AIModelCreate) => void | Promise<void>;
  confirmLoading: boolean;
  initialValues?: AIModelPublic | null;
}

export const AIModelModal = ({
  open,
  onCancel,
  onOk,
  confirmLoading,
  initialValues,
}: AIModelModalProps) => {
  const [form] = Form.useForm();
  const isEdit = !!initialValues;

  useEffect(() => {
    if (open) {
      if (initialValues) {
        form.setFieldsValue({
          model_id: initialValues.model_id,
          display_name: initialValues.display_name,
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
      // Form reset and modal close handled by parent onSuccess callback
    } catch (error) {
      // Validation failed or onOk threw - don't close modal
      console.error("Form submission error:", error);
    }
  };

  return (
    <Modal
      title={isEdit ? "Edit AI Model" : "Create AI Model"}
      open={open}
      onCancel={onCancel}
      onOk={handleSubmit}
      okText={isEdit ? "Save" : "Create"}
      okButtonProps={{ "data-testid": "submit-model-btn" }}
      confirmLoading={confirmLoading}
      destroyOnHidden
    >
      <Form form={form} layout="vertical" name="ai_model_form">
        <Form.Item
          name="model_id"
          label="Model ID"
          rules={[
            { required: true, message: "Please enter a model ID" },
            { max: 100, message: "Model ID must be 100 characters or less" },
          ]}
        >
          <Input placeholder="e.g., gpt-4" />
        </Form.Item>

        <Form.Item
          name="display_name"
          label="Display Name"
          rules={[
            { required: true, message: "Please enter a display name" },
            { max: 255, message: "Display name must be 255 characters or less" },
          ]}
        >
          <Input placeholder="e.g., GPT-4" />
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
