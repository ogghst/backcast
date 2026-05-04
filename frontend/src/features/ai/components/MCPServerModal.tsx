import { useEffect } from "react";
import { Modal, Form, Input, Switch } from "antd";
import type { MCPServerPublic, MCPServerCreate, MCPServerUpdate } from "../types";

const CONFIG_PLACEHOLDER = JSON.stringify(
  {
    transport: "stdio",
    command: "npx",
    args: ["-y", "@ericthered926/duckduckgo-mcp-server"],
    env: {},
  },
  null,
  2
);

interface MCPServerModalProps {
  open: boolean;
  onCancel: () => void;
  onOk: (values: MCPServerCreate | MCPServerUpdate) => void | Promise<void>;
  confirmLoading: boolean;
  initialValues?: MCPServerPublic | null;
}

export const MCPServerModal = ({
  open,
  onCancel,
  onOk,
  confirmLoading,
  initialValues,
}: MCPServerModalProps) => {
  const [form] = Form.useForm();
  const isEdit = !!initialValues;

  useEffect(() => {
    if (open) {
      if (initialValues) {
        form.setFieldsValue({
          name: initialValues.name,
          config: JSON.stringify(initialValues.config, null, 2),
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
      // Parse JSON config string into object
      const parsedConfig = JSON.parse(values.config);
      await onOk({
        ...values,
        config: parsedConfig,
      });
    } catch (error) {
      if (error instanceof SyntaxError) {
        form.setFields([
          {
            name: "config",
            errors: ["Invalid JSON format"],
          },
        ]);
      }
    }
  };

  return (
    <Modal
      title={isEdit ? "Edit MCP Server" : "Create MCP Server"}
      open={open}
      onCancel={onCancel}
      onOk={handleSubmit}
      okText={isEdit ? "Save" : "Create"}
      confirmLoading={confirmLoading}
      destroyOnHidden
    >
      <Form form={form} layout="vertical" name="mcp_server_form">
        <Form.Item
          name="name"
          label="Name"
          rules={[
            { required: true, message: "Please enter a server name" },
            { max: 255, message: "Name must be 255 characters or less" },
          ]}
        >
          <Input placeholder="My MCP Server" />
        </Form.Item>

        <Form.Item
          name="config"
          label="Configuration (JSON)"
          rules={[
            { required: true, message: "Please enter server configuration" },
            {
              validator: (_, value) => {
                if (!value) return Promise.resolve();
                try {
                  JSON.parse(value);
                  return Promise.resolve();
                } catch {
                  return Promise.reject(new Error("Invalid JSON format"));
                }
              },
            },
          ]}
        >
          <Input.TextArea
            rows={10}
            placeholder={CONFIG_PLACEHOLDER}
            style={{ fontFamily: "monospace", fontSize: 13 }}
          />
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
