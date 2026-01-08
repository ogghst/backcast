import { useEffect, useState } from "react";
import { Modal, Form, Input, Select } from "antd";
import type {
  CostElementTypeRead,
  CostElementTypeCreate,
  CostElementTypeUpdate,
  DepartmentRead,
} from "@/api/generated";
import { DepartmentsService } from "@/api/generated";

interface CostElementTypeModalProps {
  open: boolean;
  onCancel: () => void;
  onOk: (values: CostElementTypeCreate | CostElementTypeUpdate) => void;
  confirmLoading: boolean;
  initialValues?: CostElementTypeRead | null;
}

export const CostElementTypeModal = ({
  open,
  onCancel,
  onOk,
  confirmLoading,
  initialValues,
}: CostElementTypeModalProps) => {
  const [form] = Form.useForm();
  const isEdit = !!initialValues;
  const [departments, setDepartments] = useState<DepartmentRead[]>([]);
  const [loadingDepts, setLoadingDepts] = useState(false);

  useEffect(() => {
    if (open) {
      if (initialValues) {
        form.setFieldsValue(initialValues);
      } else {
        form.resetFields();
      }

      // Fetch departments for dropdown
      const fetchDepts = async () => {
        try {
          setLoadingDepts(true);
          // Fetch all departments (limit 100 for dropdown)
          const res = await DepartmentsService.getDepartments(1, 100);
          const items = Array.isArray(res) ? res : (res as any).items || [];
          setDepartments(items);
        } catch (err) {
          console.error("Failed to fetch departments", err);
        } finally {
          setLoadingDepts(false);
        }
      };

      fetchDepts();
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
      title={isEdit ? "Edit Cost Element Type" : "Create Cost Element Type"}
      open={open}
      onCancel={onCancel}
      onOk={handleSubmit}
      okText={isEdit ? "Save" : "Create"}
      confirmLoading={confirmLoading}
      destroyOnHidden
    >
      <Form form={form} layout="vertical" name="cost_element_type_form">
        <Form.Item
          name="name"
          label="Name"
          rules={[{ required: true, message: "Please enter type name" }]}
        >
          <Input placeholder="Labor" />
        </Form.Item>

        <Form.Item
          name="code"
          label="Code"
          rules={[
            { required: true, message: "Please enter type code" },
            {
              pattern: /^[A-Z0-9_-]+$/,
              message: "Code must be uppercase alphanumeric (with _ or -)",
            },
          ]}
        >
          <Input
            placeholder="LABOR"
            style={{ textTransform: "uppercase" }}
            onChange={(e) => {
              form.setFieldValue("code", e.target.value.toUpperCase());
            }}
          />
        </Form.Item>

        <Form.Item
          name="department_id"
          label="Department"
          rules={[{ required: true, message: "Please select a department" }]}
        >
          <Select
            placeholder="Select Department"
            loading={loadingDepts}
            showSearch
            filterOption={(input, option) =>
              (option?.label ?? "").toLowerCase().includes(input.toLowerCase())
            }
            options={departments.map((d) => ({
              label: d.name,
              value: d.department_id,
            }))}
          />
        </Form.Item>

        <Form.Item name="description" label="Description">
          <Input.TextArea placeholder="Description" rows={3} />
        </Form.Item>
      </Form>
    </Modal>
  );
};
