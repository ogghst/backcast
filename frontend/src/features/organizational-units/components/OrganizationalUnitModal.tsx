import { useEffect } from "react";
import { Modal, Form, Input } from "antd";
import type {
  OrganizationalUnitRead,
  OrganizationalUnitCreate,
  OrganizationalUnitUpdate,
} from "@/api/generated";

interface OrganizationalUnitModalProps {
  open: boolean;
  onCancel: () => void;
  onOk: (values: OrganizationalUnitCreate | OrganizationalUnitUpdate) => void;
  confirmLoading: boolean;
  initialValues?: OrganizationalUnitRead | null;
}

export const OrganizationalUnitModal = ({
  open,
  onCancel,
  onOk,
  confirmLoading,
  initialValues,
}: OrganizationalUnitModalProps) => {
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
      title={isEdit ? "Edit Organizational Unit" : "Create Organizational Unit"}
      open={open}
      onCancel={onCancel}
      onOk={handleSubmit}
      okText={isEdit ? "Save" : "Create"}
      confirmLoading={confirmLoading}
      destroyOnHidden
    >
      <Form form={form} layout="vertical" name="organizational_unit_form">
        <Form.Item
          name="name"
          label="Unit Name"
          rules={[{ required: true, message: "Please enter unit name" }]}
        >
          <Input placeholder="Engineering" />
        </Form.Item>

        <Form.Item
          name="code"
          label="Unit Code"
          rules={[{ required: true, message: "Please enter unit code" }]}
        >
          <Input placeholder="ENG" />
        </Form.Item>

        <Form.Item name="description" label="Description">
          <Input.TextArea placeholder="Organizational unit description" rows={3} />
        </Form.Item>
      </Form>
    </Modal>
  );
};
