import { useEffect } from "react";
import { Modal, Form, Input, InputNumber, DatePicker } from "antd";
import dayjs from "dayjs";
import type {
  ProjectRead,
  ProjectCreate,
  ProjectUpdate,
} from "@/api/generated";

interface ProjectModalProps {
  open: boolean;
  onCancel: () => void;
  onOk: (values: ProjectCreate | ProjectUpdate) => void;
  confirmLoading: boolean;
  initialValues?: ProjectRead | null;
}

export const ProjectModal = ({
  open,
  onCancel,
  onOk,
  confirmLoading,
  initialValues,
}: ProjectModalProps) => {
  const [form] = Form.useForm();
  const isEdit = !!initialValues;

  useEffect(() => {
    if (open) {
      if (initialValues) {
        // Transform API date strings to dayjs objects for DatePicker
        form.setFieldsValue({
          ...initialValues,
          start_date: initialValues.start_date
            ? dayjs(initialValues.start_date)
            : null,
          end_date: initialValues.end_date
            ? dayjs(initialValues.end_date)
            : null,
        });
      } else {
        form.resetFields();
      }
    }
  }, [open, initialValues, form]);

  const handleSubmit = async () => {
    try {
      const values = await form.validateFields();

      // Transform dayjs objects back to strings for API
      const formattedValues = {
        ...values,
        start_date: values.start_date
          ? values.start_date.format("YYYY-MM-DD")
          : null,
        end_date: values.end_date ? values.end_date.format("YYYY-MM-DD") : null,
      };

      await onOk(formattedValues);
    } catch (error) {
      console.error("Form submission error:", error);
    }
  };

  return (
    <Modal
      title={isEdit ? "Edit Project" : "Create Project"}
      open={open}
      onCancel={onCancel}
      onOk={handleSubmit}
      okText={isEdit ? "Save" : "Create"}
      confirmLoading={confirmLoading}
      destroyOnHidden
      width={600}
    >
      <Form form={form} layout="vertical" name="project_form">
        <Form.Item
          name="name"
          label="Project Name"
          rules={[{ required: true, message: "Please enter project name" }]}
        >
          <Input placeholder="Enter project name" />
        </Form.Item>

        <Form.Item
          name="code"
          label="Project Code"
          rules={[{ required: true, message: "Please enter project code" }]}
        >
          <Input placeholder="PRJ-001" disabled={isEdit} />
        </Form.Item>

        <div style={{ display: "flex", gap: "16px" }}>
          <Form.Item
            name="budget"
            label="Budget"
            style={{ flex: 1 }}
            rules={[{ required: true, message: "Please enter budget" }]}
          >
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

          <Form.Item
            name="contract_value"
            label="Contract Value"
            style={{ flex: 1 }}
          >
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
        </div>

        <div style={{ display: "flex", gap: "16px" }}>
          <Form.Item name="start_date" label="Start Date" style={{ flex: 1 }}>
            <DatePicker style={{ width: "100%" }} />
          </Form.Item>

          <Form.Item name="end_date" label="End Date" style={{ flex: 1 }}>
            <DatePicker style={{ width: "100%" }} />
          </Form.Item>
        </div>

        <Form.Item name="description" label="Description">
          <Input.TextArea placeholder="Project description" rows={3} />
        </Form.Item>
      </Form>
    </Modal>
  );
};
