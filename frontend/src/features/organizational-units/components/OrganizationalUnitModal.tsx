import { useEffect, useMemo } from "react";
import { Modal, Form, Input, TreeSelect } from "antd";
import type {
  OrganizationalUnitRead,
  OrganizationalUnitCreate,
  OrganizationalUnitUpdate,
} from "@/api/generated";
import { useOrgUnitTree } from "@/features/organizational-units/hooks/useOrgUnitTree";
import { buildOrgUnitTreeSelectData, getDescendantIds } from "@/features/organizational-units/utils/orgUnitTree";

interface OrganizationalUnitModalProps {
  open: boolean;
  onCancel: () => void;
  onOk: (values: OrganizationalUnitCreate | OrganizationalUnitUpdate) => void;
  confirmLoading: boolean;
  initialValues?: OrganizationalUnitRead | null;
  /** IDs to exclude from parent selection (self + descendants to prevent circular refs). */
  excludeIds?: Set<string>;
}

export const OrganizationalUnitModal = ({
  open,
  onCancel,
  onOk,
  confirmLoading,
  initialValues,
  excludeIds,
}: OrganizationalUnitModalProps) => {
  const [form] = Form.useForm();
  const isEdit = !!initialValues;
  const { items } = useOrgUnitTree();

  // Compute full exclusion set: excludeIds + all their descendants
  const fullExcludeIds = useMemo(() => {
    if (!excludeIds || excludeIds.size === 0) return undefined;
    const ids = new Set<string>();
    for (const id of excludeIds) {
      ids.add(id);
      for (const descId of getDescendantIds(id, items)) {
        ids.add(descId);
      }
    }
    return ids;
  }, [excludeIds, items]);

  const treeSelectData = buildOrgUnitTreeSelectData(items, fullExcludeIds);

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
          name="parent_unit_id"
          label="Parent Organizational Unit"
        >
          <TreeSelect
            treeData={treeSelectData}
            placeholder="None (Root Unit)"
            allowClear
            showSearch
            treeNodeFilterProp="title"
            treeLine
            style={{ width: "100%" }}
          />
        </Form.Item>

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
          <Input placeholder="ENG" disabled={isEdit} />
        </Form.Item>

        <Form.Item name="description" label="Description">
          <Input.TextArea placeholder="Organizational unit description" rows={3} />
        </Form.Item>
      </Form>
    </Modal>
  );
};
