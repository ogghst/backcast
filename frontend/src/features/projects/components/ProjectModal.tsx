import { useEffect, useMemo, useState } from "react";
import { Modal, Form, Input, InputNumber, DatePicker, Select } from "antd";
import dayjs, { type Dayjs } from "dayjs";
import type {
  ProjectRead,
  ProjectCreate,
  ProjectUpdate,
} from "@/api/generated";
import { getCurrencySymbol } from "@/utils/formatters";
import { CollapsibleCard } from "@/components/common/CollapsibleCard";
import { TemplateSelector } from "@/features/custom-fields/components/TemplateSelector";
import { CustomFieldsRenderer } from "@/features/custom-fields/components/CustomFieldsRenderer";
import { useLiveTemplateStatuses } from "@/features/custom-fields/hooks/useLiveTemplateStatuses";
import type { FieldDefinitions } from "@/features/custom-fields/types/fieldSpec";

/**
 * Serialize custom-field values: any dayjs becomes an ISO date string, the rest
 * pass through. Mirrors how this modal serializes start_date/end_date.
 */
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

const CURRENCY_OPTIONS = [
  { label: "EUR - Euro", value: "EUR" },
  { label: "USD - US Dollar", value: "USD" },
  { label: "GBP - British Pound", value: "GBP" },
  { label: "CHF - Swiss Franc", value: "CHF" },
  { label: "JPY - Japanese Yen", value: "JPY" },
];

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

  // A template is immutable ONCE SET (decision D2). On EDIT of an entity that
  // already has a bound template, the selector is hidden and fields render from
  // the captured snapshot. On EDIT of a template-less entity, the user may
  // first-time bind one (backend captures the snapshot on UPDATE).
  const hasBoundTemplate = isEdit && Boolean(
    initialValues?.custom_entity_template_root_id,
  );

  // Custom-fields template selection. CREATE always shows the selector; EDIT
  // shows it only when the entity has no bound template yet (first-time bind).
  const [selectedTemplateRootId, setSelectedTemplateRootId] = useState<
    string | null
  >(null);
  const [selectedFieldDefs, setSelectedFieldDefs] =
    useState<FieldDefinitions | null>(null);

  // Bound-template field definitions are derived purely from the entity's
  // captured snapshot (no user interaction), so useMemo — not state — to avoid
  // setState-in-effect cascades. Template-less defs live in selectedFieldDefs.
  const boundFieldDefs = useMemo<FieldDefinitions | null>(
    () =>
      (initialValues?.custom_field_definitions_snapshot as FieldDefinitions) ??
      null,
    [initialValues],
  );
  const fieldDefs = hasBoundTemplate ? boundFieldDefs : selectedFieldDefs;

  // Bound EDIT: overlay the LIVE template's field statuses so deprecated /
  // retired fields render read-only (an admin can change a field's status
  // AFTER the entity was bound). CREATE / first-time-bind paths skip this —
  // their field defs already come from the live template, so the renderer's
  // create-mode filter handles hiding.
  const liveStatuses = useLiveTemplateStatuses(
    hasBoundTemplate
      ? initialValues?.custom_entity_template_root_id
      : undefined,
  );

  const selectedCurrency = Form.useWatch("currency", form) || initialValues?.currency || "EUR";
  const currencySymbol = useMemo(() => getCurrencySymbol(selectedCurrency), [selectedCurrency]);

  const currencyFormatValue = useMemo(
    () => (value: string | number | undefined) =>
      `${currencySymbol} ${value}`.replace(/\B(?=(\d{3})+(?!\d))/g, ","),
    [currencySymbol],
  );

  const currencyParseRegex = useMemo(
    () => new RegExp(`\\${currencySymbol}\\s?|(,*)`, "g"),
    [currencySymbol],
  );

  useEffect(() => {
    if (open) {
      if (initialValues) {
        // Transform API date strings to dayjs objects for DatePicker
        // eslint-disable-next-line @typescript-eslint/no-unused-vars
        const { budget: _budget, ...rest } = initialValues;
        form.setFieldsValue({
          ...rest,
          start_date: initialValues.start_date
            ? dayjs(initialValues.start_date)
            : null,
          end_date: initialValues.end_date
            ? dayjs(initialValues.end_date)
            : null,
          custom_fields: initialValues.custom_fields ?? {},
        });
        // Bound entities render fields from the captured snapshot; template-less
        // entities show the selector for a first-time bind. boundFieldDefs is
        // derived via useMemo above.
      } else {
        form.resetFields();
        form.setFieldsValue({ currency: "EUR", custom_fields: {} });
        // No-cascade: child/standalone create starts with an empty selector.
        // Resetting selection state when the modal re-opens for CREATE is the
        // documented React exception to set-state-in-effect (reset on prop
        // change). Key-based remount would fight the form's destroyOnHidden.
        // eslint-disable-next-line react-hooks/set-state-in-effect
        setSelectedTemplateRootId(null);
        setSelectedFieldDefs(null);
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
        custom_fields: serializeCustomFields(
          values.custom_fields as Record<string, unknown> | undefined,
        ),
        // Template binding is immutable once set. Send the template id on
        // CREATE, and on EDIT only when first-time-binding a template-less
        // entity (the backend captures the snapshot). Already-bound entities
        // never re-send it.
        custom_entity_template_root_id: hasBoundTemplate
          ? undefined
          : (selectedTemplateRootId ?? null),
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

        <Form.Item
          name="currency"
          label="Currency"
          rules={[{ required: true, message: "Please select a currency" }]}
        >
          <Select placeholder="Select currency" options={CURRENCY_OPTIONS} />
        </Form.Item>

        <Form.Item
          name="contract_value"
          label={`Contract Value (${selectedCurrency})`}
        >
          <InputNumber
            style={{ width: "100%" }}
            formatter={(value) => currencyFormatValue(value)}
            parser={(value) =>
              value?.replace(currencyParseRegex, "") as unknown as number
            }
            placeholder="0.00"
            addonAfter={currencySymbol}
          />
        </Form.Item>

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

        {/* Custom fields (template-driven). CREATE: pick a template. EDIT:
            shown only when the entity has no bound template yet (first-time
            bind); an already-bound entity renders from its captured snapshot
            (immutable binding). */}
        {!hasBoundTemplate && (
          <Form.Item
            name="custom_entity_template_root_id"
            label="Custom Fields Template"
            tooltip={
              isEdit
                ? "Apply a template to add custom fields. Once saved, the template is bound permanently."
                : "Optional. Selecting a template adds its custom fields below."
            }
          >
            <TemplateSelector
              targetType="PROJECT"
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
            id="project-custom-fields"
            title="Custom Fields"
            keepMounted
          >
            <CustomFieldsRenderer
              fieldDefinitions={fieldDefs}
              mode={hasBoundTemplate ? "edit" : "create"}
              liveStatuses={hasBoundTemplate ? liveStatuses : undefined}
            />
          </CollapsibleCard>
        )}
      </Form>
    </Modal>
  );
};
