import { useEffect } from "react";
import { Modal, Form, Input, TreeSelect } from "antd";
import type {
  CostElementTypeRead,
  CostElementTypeCreate,
  CostElementTypeUpdate,
} from "@/api/generated";
import { useOrgUnitTree } from "@/features/organizational-units/hooks/useOrgUnitTree";
import { buildOrgUnitTreeSelectData } from "@/features/organizational-units/utils/orgUnitTree";

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
  const { items: orgUnitItems, isLoading: orgUnitsLoading } = useOrgUnitTree();
  const orgUnitTreeData = buildOrgUnitTreeSelectData(orgUnitItems);

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
          name="organizational_unit_id"
          label="Organizational Unit"
          rules={[{ required: true, message: "Please select a department" }]}
        >
          <TreeSelect
            placeholder="Select Org Unit"
            treeData={orgUnitTreeData}
            showSearch
            treeNodeFilterProp="title"
            allowClear
            treeLine
            loading={orgUnitsLoading}
          />
        </Form.Item>

        <Form.Item name="description" label="Description">
          <Input.TextArea placeholder="Description" rows={3} />
        </Form.Item>
      </Form>
    </Modal>
  );
};
