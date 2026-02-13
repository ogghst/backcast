import { useEffect } from "react";
import { Modal, Form, Input, Select, Switch } from "antd";
import { User, CreateUserPayload, UpdateUserPayload } from "@/types/user";

interface UserModalProps {
  open: boolean;
  onCancel: () => void;
  onOk: (values: CreateUserPayload | UpdateUserPayload) => void;
  confirmLoading: boolean;
  initialValues?: User | null;
}

export const UserModal = ({
  open,
  onCancel,
  onOk,
  confirmLoading,
  initialValues,
}: UserModalProps) => {
  const [form] = Form.useForm();
  const isEdit = !!initialValues;

  useEffect(() => {
    if (open) {
      if (initialValues) {
        form.setFieldsValue(initialValues);
      } else {
        form.resetFields();
      }
    }
  }, [open, initialValues, form]);

  const handleSubmit = async () => {
    try {
      const values = await form.validateFields();
      await onOk(values);
      // Only close modal on SUCCESS - error will be handled by caller
    } catch (error) {
      // If validation failed or onOk threw, don't close modal
      // The error will be displayed by the useCrud mutation
      console.error("Form submission error:", error);
    }
  };

  return (
    <Modal
      title={isEdit ? "Edit User" : "Create User"}
      open={open}
      onCancel={onCancel}
      onOk={handleSubmit}
      okText={isEdit ? "Save" : "Create"}
      okButtonProps={{ "data-testid": "submit-user-btn" }}
      confirmLoading={confirmLoading}
      destroyOnHidden
    >
      <Form form={form} layout="vertical" name="user_form">
        <Form.Item
          name="full_name"
          label="Full Name"
          rules={[{ required: true, message: "Please enter full name" }]}
        >
          <Input placeholder="John Doe" />
        </Form.Item>

        <Form.Item
          name="email"
          label="Email"
          rules={[
            { required: true, message: "Please enter email" },
            { type: "email", message: "Please enter a valid email" },
          ]}
        >
          <Input placeholder="john@example.com" />
        </Form.Item>

        {!isEdit && (
          <Form.Item
            name="password"
            label="Password"
            rules={[{ required: true, message: "Please enter password" }]}
          >
            <Input.Password placeholder="Password" />
          </Form.Item>
        )}

        <Form.Item
          name="role"
          label="Role"
          rules={[{ required: true, message: "Please select a role" }]}
        >
          <Select placeholder="Select a role">
            <Select.Option value="admin">Admin</Select.Option>
            <Select.Option value="project_manager">
              Project Manager
            </Select.Option>
            <Select.Option value="department_manager">
              Department Manager
            </Select.Option>
            <Select.Option value="viewer">Viewer</Select.Option>
          </Select>
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
