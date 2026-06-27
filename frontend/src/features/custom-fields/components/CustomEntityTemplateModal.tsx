import { useEffect } from "react";
import {
  Alert,
  Form,
  Input,
  Modal,
  Select,
  TreeSelect,
} from "antd";
import type {
  CustomEntityTemplateCreate,
  CustomEntityTemplateRead,
  CustomEntityTemplateUpdate,
} from "@/api/generated";
import { useOrgUnitTree } from "@/features/organizational-units/hooks/useOrgUnitTree";
import { buildOrgUnitTreeSelectData } from "@/features/organizational-units/utils/orgUnitTree";
import { CollapsibleCard } from "@/components/common/CollapsibleCard";
import {
  FieldDefinitionsEditor,
  type FieldDefinitionsValue,
} from "./FieldDefinitionsEditor";

type TargetEntityType =
  | "PROJECT"
  | "WBS_ELEMENT"
  | "WORK_PACKAGE"
  | "CHANGE_ORDER";

const TARGET_ENTITY_OPTIONS: { value: TargetEntityType; label: string }[] = [
  { value: "PROJECT", label: "Project" },
  { value: "WBS_ELEMENT", label: "WBS Element" },
  { value: "WORK_PACKAGE", label: "Work Package" },
  { value: "CHANGE_ORDER", label: "Change Order" },
];

interface CustomEntityTemplateModalProps {
  open: boolean;
  onCancel: () => void;
  onOk: (
    values: CustomEntityTemplateCreate | CustomEntityTemplateUpdate,
  ) => Promise<void>;
  confirmLoading: boolean;
  initialValues?: CustomEntityTemplateRead | null;
  /** Backend validation error to display (e.g. malformed field_definitions). */
  submitError?: string | null;
}

/**
 * Build the API payload from the form values. The form stores
 * `field_definitions` as a dict (already the wire shape); we just forward it.
 */
function buildPayload(
  values: {
    code: string;
    name: string;
    description?: string;
    target_entity_type: TargetEntityType;
    organizational_unit_id: string;
    field_definitions: FieldDefinitionsValue;
  },
  isEdit: boolean,
): CustomEntityTemplateCreate | CustomEntityTemplateUpdate {
  const fieldDefinitions = values.field_definitions ?? {};
  if (isEdit) {
    // target_entity_type is immutable post-create; omit it from the update so
    // the backend doesn't reject an unchanged-value edge case. code/name/etc.
    // follow the Update schema (all optional).
    return {
      code: values.code,
      name: values.name,
      description: values.description ?? null,
      field_definitions: fieldDefinitions,
    };
  }
  return {
    code: values.code,
    name: values.name,
    description: values.description ?? null,
    target_entity_type: values.target_entity_type,
    organizational_unit_id: values.organizational_unit_id,
    field_definitions: fieldDefinitions,
  };
}

export const CustomEntityTemplateModal = ({
  open,
  onCancel,
  onOk,
  confirmLoading,
  initialValues,
  submitError,
}: CustomEntityTemplateModalProps) => {
  const [form] = Form.useForm();
  const isEdit = !!initialValues;
  const { items: orgUnitItems, isLoading: orgUnitsLoading } = useOrgUnitTree();
  const orgUnitTreeData = buildOrgUnitTreeSelectData(orgUnitItems);

  useEffect(() => {
    if (open) {
      if (initialValues) {
        form.setFieldsValue({
          code: initialValues.code,
          name: initialValues.name,
          description: initialValues.description ?? undefined,
          target_entity_type: initialValues.target_entity_type,
          organizational_unit_id: initialValues.organizational_unit_id,
          field_definitions: initialValues.field_definitions ?? {},
        });
      } else {
        form.resetFields();
        form.setFieldsValue({ field_definitions: {} });
      }
    }
  }, [open, initialValues, form]);

  const handleSubmit = async () => {
    try {
      const values = await form.validateFields();
      await onOk(buildPayload(values, isEdit));
    } catch (error) {
      // Antd validation errors are expected; API errors are surfaced via
      // `submitError` (set by the parent from the mutation's onError).
      console.error("Form submission error:", error);
    }
  };

  return (
    <Modal
      title={
        isEdit ? "Edit Custom Entity Template" : "Create Custom Entity Template"
      }
      open={open}
      onCancel={onCancel}
      onOk={handleSubmit}
      okText={isEdit ? "Save" : "Create"}
      confirmLoading={confirmLoading}
      destroyOnHidden
      width={720}
    >
      <Form
        form={form}
        layout="vertical"
        name="custom_entity_template_form"
        initialValues={{ field_definitions: {} }}
      >
        {submitError && (
          <Alert
            type="error"
            message="Validation error"
            description={submitError}
            showIcon
            style={{ marginBottom: 16 }}
          />
        )}

        <Form.Item
          name="name"
          label="Name"
          rules={[{ required: true, message: "Please enter template name" }]}
        >
          <Input placeholder="Change Order Fields" />
        </Form.Item>

        <Form.Item
          name="code"
          label="Code"
          rules={[
            { required: true, message: "Please enter template code" },
            {
              pattern: /^[A-Z0-9_-]+$/,
              message: "Code must be uppercase alphanumeric (with _ or -)",
            },
          ]}
        >
          <Input
            placeholder="CHANGE_ORDER_FIELDS"
            style={{ textTransform: "uppercase" }}
            onChange={(e) => {
              form.setFieldValue("code", e.target.value.toUpperCase());
            }}
          />
        </Form.Item>

        <Form.Item
          name="target_entity_type"
          label="Target Entity Type"
          rules={[
            { required: true, message: "Please select a target entity type" },
          ]}
          extra={
            isEdit
              ? "Target entity type is immutable after creation."
              : undefined
          }
        >
          <Select
            placeholder="Select target entity type"
            options={TARGET_ENTITY_OPTIONS}
            disabled={isEdit}
          />
        </Form.Item>

        <Form.Item
          name="organizational_unit_id"
          label="Organizational Unit"
          rules={[{ required: true, message: "Please select an org unit" }]}
        >
          <TreeSelect
            placeholder="Select Org Unit"
            treeData={orgUnitTreeData}
            showSearch
            treeNodeFilterProp="title"
            allowClear
            treeLine
            loading={orgUnitsLoading}
            disabled={isEdit}
          />
        </Form.Item>

        <Form.Item name="description" label="Description">
          <Input.TextArea placeholder="Description" rows={2} />
        </Form.Item>

        {/* keepMounted: CollapsibleCard unmounts children on collapse, which
            would drop the registered Form.Item — MEMORY note. */}
        <CollapsibleCard title="Field Definitions" id="field-definitions" keepMounted>
          <Form.Item
            name="field_definitions"
            label="Custom fields"
            tooltip="Dict keyed by field code. Each field validates against its type config."
          >
            <FieldDefinitionsEditor />
          </Form.Item>
        </CollapsibleCard>
      </Form>
    </Modal>
  );
};
