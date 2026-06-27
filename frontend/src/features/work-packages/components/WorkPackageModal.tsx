import { useEffect, useMemo, useRef, useState } from "react";
import { Modal, Form, Input, Select, InputNumber } from "antd";
import dayjs, { type Dayjs } from "dayjs";
import { useTimeMachineParams } from "@/contexts/TimeMachineContext";
import { useThemeTokens } from "@/hooks/useThemeTokens";
import { useControlAccounts } from "@/features/control-accounts/api/useControlAccounts";
import { CollapsibleCard } from "@/components/common/CollapsibleCard";
import { TemplateSelector } from "@/features/custom-fields/components/TemplateSelector";
import { CustomFieldsRenderer } from "@/features/custom-fields/components/CustomFieldsRenderer";
import type { FieldDefinitions } from "@/features/custom-fields/types/fieldSpec";
import type {
  WorkPackageCreate,
  WorkPackageUpdate,
  WorkPackageRead,
} from "@/api/generated";

/** Serialize custom-field dayjs values to ISO strings for the API. */
function serializeCustomFields(
  values: Record<string, unknown> | undefined | null,
): Record<string, unknown> | undefined {
  if (!values) return undefined;
  const out: Record<string, unknown> = {};
  for (const [key, value] of Object.entries(values)) {
    out[key] = dayjs.isDayjs(value) ? (value as Dayjs).toISOString() : value;
  }
  return out;
}

const STATUS_OPTIONS = [
  { label: "Open", value: "open" },
  { label: "In Progress", value: "in_progress" },
  { label: "Closed", value: "closed" },
] as const;

interface WorkPackageModalProps {
  open: boolean;
  onCancel: () => void;
  onOk: (values: WorkPackageCreate | WorkPackageUpdate) => void;
  confirmLoading: boolean;
  initialValues?: WorkPackageRead | null;
  currency?: string;
  /** When provided, scopes the Control Account dropdown to CAs belonging to this WBS element. */
  wbsElementId?: string;
}

export const WorkPackageModal = ({
  open,
  onCancel,
  onOk,
  confirmLoading,
  initialValues,
  currency = "EUR",
  wbsElementId,
}: WorkPackageModalProps) => {
  const [form] = Form.useForm();
  const { asOf } = useTimeMachineParams();
  const { spacing } = useThemeTokens();
  const isEdit = !!initialValues;

  // Custom-fields template (CREATE only; EDIT renders from the snapshot).
  const [selectedTemplateRootId, setSelectedTemplateRootId] = useState<
    string | null
  >(null);
  const [selectedFieldDefs, setSelectedFieldDefs] =
    useState<FieldDefinitions | null>(null);

  // EDIT-mode field definitions are derived purely from the entity's captured
  // snapshot (no user interaction), so useMemo — not state — to avoid
  // setState-in-effect cascades.
  const editFieldDefs = useMemo<FieldDefinitions | null>(
    () =>
      (initialValues?.custom_field_definitions_snapshot as FieldDefinitions) ??
      null,
    [initialValues],
  );
  const fieldDefs = isEdit ? editFieldDefs : selectedFieldDefs;

  // Control Account options — scoped to a specific WBS element when provided
  const { data: caData } = useControlAccounts(
    wbsElementId ? { wbs_element_id: wbsElementId } : undefined,
  );
  const caOptions = (caData?.items || []).map((ca) => ({
    label:
      ca.code && ca.name
        ? `${ca.code} - ${ca.name}`
        : ca.name || ca.code || "Unknown Control Account",
    value: ca.control_account_id,
  }));

  // Currency formatter/parser for InputNumber
  const currencySymbol = currency === "EUR" ? "€" : currency;

  const currencyFormatValue = useMemo(
    () => (value: string | number | undefined) => {
      if (!value) return "";
      return `${currencySymbol} ${value}`.replace(
        /\B(?=(\d{3})+(?!\d))/g,
        ",",
      );
    },
    [currencySymbol],
  );

  const currencyParseRegex = useMemo(
    () => new RegExp(`\\${currencySymbol}\\s?|(,*)`, "g"),
    [currencySymbol],
  );

  // Track previous open state to detect transitions
  const prevOpenRef = useRef(false);

  // Initialize form values when modal opens
  useEffect(() => {
    if (open && !prevOpenRef.current) {
      if (initialValues) {
        form.setFieldsValue({
          name: initialValues.name,
          code: initialValues.code,
          description: initialValues.description,
          budget_amount: initialValues.budget_amount
            ? Number(initialValues.budget_amount)
            : undefined,
          status: initialValues.status,
          control_account_id: initialValues.control_account_id,
          custom_fields: initialValues.custom_fields ?? {},
        });
        // editFieldDefs is derived via useMemo above.
      } else {
        form.resetFields();
        form.setFieldsValue({
          status: "open",
          custom_fields: {},
        });
        // No-cascade: start with an empty selector. Resetting selection state
        // when the modal re-opens for CREATE is the documented React exception
        // to set-state-in-effect (reset on prop change). Key-based remount
        // would fight the form's destroyOnHidden.
        // eslint-disable-next-line react-hooks/set-state-in-effect
        setSelectedTemplateRootId(null);
        setSelectedFieldDefs(null);
      }
    }
    prevOpenRef.current = open;
  }, [open, initialValues, form, asOf]);

  const handleSubmit = async () => {
    try {
      const values = await form.validateFields();
      await onOk({
        ...values,
        custom_fields: serializeCustomFields(
          values.custom_fields as Record<string, unknown> | undefined,
        ),
        custom_entity_template_root_id: isEdit
          ? undefined
          : (selectedTemplateRootId ?? null),
      });
    } catch (error) {
      console.error("Form submission error:", error);
    }
  };

  return (
    <Modal
      title={isEdit ? "Edit Work Package" : "Add Work Package"}
      open={open}
      onCancel={onCancel}
      onOk={handleSubmit}
      okText={isEdit ? "Save" : "Create"}
      confirmLoading={confirmLoading}
      destroyOnHidden
      width={600}
    >
      <Form form={form} layout="vertical" name="work_package_form">
        {/* Name + Code row */}
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "1fr 1fr",
            gap: spacing.md,
          }}
        >
          <Form.Item
            name="name"
            label="Name"
            rules={[{ required: true, message: "Please enter a name" }]}
          >
            <Input placeholder="e.g. WP-100 Electrical Assembly" />
          </Form.Item>

          <Form.Item
            name="code"
            label="Code"
            rules={[{ required: true, message: "Please enter a code" }]}
          >
            <Input placeholder="e.g. WP-100" />
          </Form.Item>
        </div>

        {/* Description */}
        <Form.Item name="description" label="Description">
          <Input.TextArea rows={2} placeholder="Optional description" />
        </Form.Item>

        {/* Budget + Status row */}
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "1fr 1fr",
            gap: spacing.md,
          }}
        >
          <Form.Item name="budget_amount" label="Budget Amount">
            <InputNumber
              style={{ width: "100%" }}
              controls={false}
              precision={2}
              min={0 as number}
              placeholder="0.00"
              formatter={(value) => currencyFormatValue(value)}
              parser={(value) => {
                if (!value) return 0;
                const cleaned = value.replace(currencyParseRegex, "");
                const parsed = parseFloat(cleaned);
                return isNaN(parsed) ? 0 : parsed;
              }}
            />
          </Form.Item>

          <Form.Item name="status" label="Status">
            <Select placeholder="Select status" options={[...STATUS_OPTIONS]} />
          </Form.Item>
        </div>

        {/* Control Account */}
        <Form.Item
          name="control_account_id"
          label="Control Account"
          rules={[
            { required: true, message: "Please select a Control Account" },
          ]}
        >
          <Select
            placeholder="Select Control Account"
            options={caOptions}
            showSearch
            optionFilterProp="label"
            allowClear
          />
        </Form.Item>

        {/* Custom fields (template-driven). CREATE: pick a template; EDIT:
            immutable binding, render from the captured snapshot. */}
        {!isEdit && (
          <Form.Item
            name="custom_entity_template_root_id"
            label="Custom Fields Template"
            tooltip="Optional. Selecting a template adds its custom fields below."
          >
            <TemplateSelector
              targetType="WORK_PACKAGE"
              value={selectedTemplateRootId}
              onChange={(rootId, fieldDefs) => {
                setSelectedTemplateRootId(rootId);
                setSelectedFieldDefs(fieldDefs ?? null);
                form.setFieldValue(
                  "custom_entity_template_root_id",
                  rootId,
                );
              }}
            />
          </Form.Item>
        )}

        {fieldDefs && Object.keys(fieldDefs).length > 0 && (
          <CollapsibleCard
            id="work-package-custom-fields"
            title="Custom Fields"
            keepMounted
          >
            <CustomFieldsRenderer fieldDefinitions={fieldDefs} />
          </CollapsibleCard>
        )}
      </Form>
    </Modal>
  );
};
