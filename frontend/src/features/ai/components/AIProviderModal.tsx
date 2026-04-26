import { useEffect } from "react";
import { Modal, Form, Input, Select, Switch, Button, Space, Divider } from "antd";
import { DatabaseOutlined, SettingOutlined } from "@ant-design/icons";
import type { AIProviderPublic, AIProviderCreate, AIProviderUpdate } from "../types";

interface AIProviderModalProps {
  open: boolean;
  onCancel: () => void;
  onOk: (values: AIProviderCreate | AIProviderUpdate) => void | Promise<void>;
  confirmLoading: boolean;
  initialValues?: AIProviderPublic | null;
  onOpenModels?: () => void;
  onOpenConfiguration?: () => void;
}

export const AIProviderModal = ({
  open,
  onCancel,
  onOk,
  confirmLoading,
  initialValues,
  onOpenModels,
  onOpenConfiguration,
}: AIProviderModalProps) => {
  const [form] = Form.useForm();
  const isEdit = !!initialValues;

  useEffect(() => {
    if (open) {
      if (initialValues) {
        form.setFieldsValue({
          provider_type: initialValues.provider_type,
          name: initialValues.name,
          base_url: initialValues.base_url,
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
      title={isEdit ? "Edit AI Provider" : "Create AI Provider"}
      open={open}
      onCancel={onCancel}
      onOk={handleSubmit}
      okText={isEdit ? "Save" : "Create"}
      okButtonProps={{ "data-testid": "submit-provider-btn" }}
      confirmLoading={confirmLoading}
      destroyOnHidden
      footer={
        <>
          {isEdit && (
            <div style={{ marginBottom: 16 }}>
              <Space>
                <Button
                  icon={<DatabaseOutlined />}
                  onClick={onOpenModels}
                  data-testid="models-btn"
                >
                  Models
                </Button>
                <Button
                  icon={<SettingOutlined />}
                  onClick={onOpenConfiguration}
                  data-testid="configuration-btn"
                >
                  Configuration
                </Button>
              </Space>
              <Divider style={{ margin: "12px 0" }} />
            </div>
          )}
          <div style={{ display: "flex", justifyContent: "flex-end", gap: 8 }}>
            <Button onClick={onCancel}>Cancel</Button>
            <Button
              type="primary"
              onClick={handleSubmit}
              loading={confirmLoading}
              data-testid="submit-provider-btn"
            >
              {isEdit ? "Save" : "Create"}
            </Button>
          </div>
        </>
      }
    >
      <Form form={form} layout="vertical" name="ai_provider_form">
        <Form.Item
          name="provider_type"
          label="Provider Type"
          rules={[{ required: true, message: "Please select a provider type" }]}
        >
          <Select placeholder="Select a provider type">
            <Select.Option value="openai">OpenAI</Select.Option>
            <Select.Option value="azure">Azure OpenAI</Select.Option>
            <Select.Option value="ollama">Ollama</Select.Option>
          </Select>
        </Form.Item>

        <Form.Item
          name="name"
          label="Name"
          rules={[
            { required: true, message: "Please enter a name" },
            { max: 255, message: "Name must be 255 characters or less" },
          ]}
        >
          <Input placeholder="My AI Provider" />
        </Form.Item>

        <Form.Item
          name="base_url"
          label="Base URL (Optional)"
          rules={[{ max: 500, message: "Base URL must be 500 characters or less" }]}
        >
          <Input placeholder="https://api.example.com/v1" />
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
