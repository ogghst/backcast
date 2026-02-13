import { useEffect } from "react";
import { Modal, Form, Input } from "antd";
import type {
  DepartmentRead,
  DepartmentCreate,
  DepartmentUpdate,
} from "@/api/generated";

interface DepartmentModalProps {
  open: boolean;
  onCancel: () => void;
  onOk: (values: DepartmentCreate | DepartmentUpdate) => void;
  confirmLoading: boolean;
  initialValues?: DepartmentRead | null;
}

export const DepartmentModal = ({
  open,
  onCancel,
  onOk,
  confirmLoading,
  initialValues,
}: DepartmentModalProps) => {
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
    } catch (error) {
      console.error("Form submission error:", error);
    }
  };

  return (
    <Modal
      title={isEdit ? "Edit Department" : "Create Department"}
      open={open}
      onCancel={onCancel}
      onOk={handleSubmit}
      okText={isEdit ? "Save" : "Create"}
      confirmLoading={confirmLoading}
      destroyOnHidden
    >
      <Form form={form} layout="vertical" name="department_form">
        <Form.Item
          name="name"
          label="Department Name"
          rules={[{ required: true, message: "Please enter department name" }]}
        >
          <Input placeholder="Engineering" />
        </Form.Item>

        <Form.Item
          name="code"
          label="Department Code"
          rules={[{ required: true, message: "Please enter department code" }]}
        >
          <Input placeholder="ENG" />
        </Form.Item>

        <Form.Item name="description" label="Description">
          <Input.TextArea placeholder="Department description" rows={3} />
        </Form.Item>
      </Form>
    </Modal>
  );
};
