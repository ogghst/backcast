import { useEffect } from "react";
import { Modal, Form, Input, InputNumber } from "antd";
import type { WBERead, WBECreate, WBEUpdate } from "@/api/generated";

interface WBEModalProps {
  open: boolean;
  onCancel: () => void;
  onOk: (values: WBECreate | WBEUpdate) => void;
  confirmLoading: boolean;
  initialValues?: WBERead | null;
  projectId?: string;
}

export const WBEModal = ({
  open,
  onCancel,
  onOk,
  confirmLoading,
  initialValues,
  projectId,
}: WBEModalProps) => {
  const [form] = Form.useForm();
  const isEdit = !!initialValues;

  useEffect(() => {
    if (open) {
      if (initialValues) {
        form.setFieldsValue(initialValues);
      } else {
        form.resetFields();
        if (projectId) {
          form.setFieldValue("project_id", projectId);
        }
      }
    }
  }, [open, initialValues, projectId, form]);

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
      title={isEdit ? "Edit WBE" : "Create WBE"}
      open={open}
      onCancel={onCancel}
      onOk={handleSubmit}
      okText={isEdit ? "Save" : "Create"}
      confirmLoading={confirmLoading}
      destroyOnHidden
    >
      <Form form={form} layout="vertical" name="wbe_form">
        {!projectId && !isEdit && (
          <Form.Item
            name="project_id"
            label="Project ID"
            rules={[{ required: true, message: "Please enter Project ID" }]}
          >
            <Input placeholder="Project ID" />
          </Form.Item>
        )}

        {/* Hidden field for projectId when passed as prop */}
        {projectId && !isEdit && (
          <Form.Item name="project_id" hidden>
            <Input />
          </Form.Item>
        )}

        <Form.Item
          name="name"
          label="WBE Name"
          rules={[{ required: true, message: "Please enter WBE name" }]}
        >
          <Input placeholder="Foundations" />
        </Form.Item>

        <Form.Item
          name="code"
          label="WBE Code"
          rules={[{ required: true, message: "Please enter WBE code" }]}
        >
          <Input placeholder="1.1" disabled={isEdit} />
        </Form.Item>

        <Form.Item name="budget_allocation" label="Budget Allocation">
          <InputNumber
            style={{ width: "100%" }}
            formatter={(value) =>
              `€ ${value}`.replace(/\B(?=(\d{3})+(?!\d))/g, ",")
            }
            parser={(value) =>
              value?.replace(/€\s?|(,*)/g, "") as unknown as number
            }
            placeholder="0.00"
          />
        </Form.Item>

        <Form.Item name="level" label="Level">
          <InputNumber style={{ width: "100%" }} min={1} />
        </Form.Item>

        <Form.Item
          name="parent_wbe_id"
          label="Parent WBE ID"
          tooltip="ID of the parent WBE if applicable"
        >
          <Input placeholder="Parent WBE ID (Optional)" />
        </Form.Item>

        <Form.Item name="description" label="Description">
          <Input.TextArea placeholder="WBE description" rows={3} />
        </Form.Item>
      </Form>
    </Modal>
  );
};
