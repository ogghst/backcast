import { useEffect } from "react";
import { Modal, Form, Input, Select, Switch } from "antd";
import type {
  CostEventTypeRead,
  CostEventTypeCreate,
  CostEventTypeUpdate,
} from "@/api/generated";

const COLOR_OPTIONS = [
  { value: "red", label: "Red" },
  { value: "blue", label: "Blue" },
  { value: "green", label: "Green" },
  { value: "orange", label: "Orange" },
  { value: "purple", label: "Purple" },
  { value: "cyan", label: "Cyan" },
  { value: "magenta", label: "Magenta" },
  { value: "volcano", label: "Volcano" },
  { value: "gold", label: "Gold" },
  { value: "lime", label: "Lime" },
];

interface CostEventTypeModalProps {
  open: boolean;
  onCancel: () => void;
  onOk: (values: CostEventTypeCreate | CostEventTypeUpdate) => void;
  confirmLoading: boolean;
  initialValues?: CostEventTypeRead | null;
}

export const CostEventTypeModal = ({
  open,
  onCancel,
  onOk,
  confirmLoading,
  initialValues,
}: CostEventTypeModalProps) => {
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
      title={isEdit ? "Edit Cost Event Type" : "Create Cost Event Type"}
      open={open}
      onCancel={onCancel}
      onOk={handleSubmit}
      okText={isEdit ? "Save" : "Create"}
      confirmLoading={confirmLoading}
      destroyOnHidden
    >
      <Form form={form} layout="vertical" name="cost_event_type_form">
        <Form.Item
          name="name"
          label="Name"
          rules={[{ required: true, message: "Please enter cost event type name" }]}
        >
          <Input placeholder="Preventive" />
        </Form.Item>

        <Form.Item
          name="code"
          label="Code"
          rules={[
            { required: true, message: "Please enter cost event type code" },
            {
              pattern: /^[A-Z0-9_-]+$/,
              message: "Code must be uppercase alphanumeric (with _ or -)",
            },
          ]}
        >
          <Input
            placeholder="PREVENTIVE"
            style={{ textTransform: "uppercase" }}
            onChange={(e) => {
              form.setFieldValue("code", e.target.value.toUpperCase());
            }}
          />
        </Form.Item>

        <Form.Item name="color" label="Color">
          <Select
            placeholder="Select Color"
            allowClear
            options={COLOR_OPTIONS}
          />
        </Form.Item>

        <Form.Item
          name="is_quality"
          label="Quality Type"
          valuePropName="checked"
          initialValue={false}
          tooltip="Enable for types that contribute to Cost of Quality (COQ) metrics"
        >
          <Switch checkedChildren="COQ" unCheckedChildren="--" />
        </Form.Item>

        <Form.Item name="description" label="Description">
          <Input.TextArea placeholder="Description" rows={3} />
        </Form.Item>
      </Form>
    </Modal>
  );
};
