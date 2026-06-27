import { useEffect, useMemo, useState } from "react";
import {
  Modal,
  Form,
  Input,
  InputNumber,
  DatePicker,
  Select,
  Space,
  theme,
} from "antd";
import { ProjectRead, ProjectUpdate, type ProjectStatus } from "@/api/generated";
import { Can } from "@/components/auth/Can";
import { getCurrencySymbol } from "@/utils/formatters";
import { CollapsibleCard } from "@/components/common/CollapsibleCard";
import { TemplateSelector } from "@/features/custom-fields/components/TemplateSelector";
import { CustomFieldsRenderer } from "@/features/custom-fields/components/CustomFieldsRenderer";
import { useLiveTemplateStatuses } from "@/features/custom-fields/hooks/useLiveTemplateStatuses";
import type { FieldDefinitions } from "@/features/custom-fields/types/fieldSpec";
import dayjs, { type Dayjs } from "dayjs";

interface ProjectEditModalProps {
  open: boolean;
  onCancel: () => void;
  onOk: (values: ProjectUpdate) => void;
  confirmLoading?: boolean;
  project: ProjectRead | null;
}

interface FormValues {
  name: string;
  status?: string;
  currency?: string;
  contract_value?: number | null;
  start_date?: dayjs.Dayjs | null;
  end_date?: dayjs.Dayjs | null;
  description?: string;
  custom_fields?: Record<string, unknown>;
  custom_entity_template_root_id?: string | null;
}

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

const PROJECT_STATUSES = [
  { label: "draft", value: "draft" },
  { label: "active", value: "active" },
  { label: "on hold", value: "on_hold" },
  { label: "completed", value: "completed" },
  { label: "cancelled", value: "cancelled" },
];

const CURRENCY_OPTIONS = [
  { label: "EUR - Euro", value: "EUR" },
  { label: "USD - US Dollar", value: "USD" },
  { label: "GBP - British Pound", value: "GBP" },
  { label: "CHF - Swiss Franc", value: "CHF" },
  { label: "JPY - Japanese Yen", value: "JPY" },
];

/**
 * ProjectEditModal - Modal form for editing project details.
 *
 * Allows editing of project fields with validation.
 * Requires project-update permission.
 */
export const ProjectEditModal = ({
  open,
  onCancel,
  onOk,
  confirmLoading,
  project,
}: ProjectEditModalProps) => {
  const { token } = theme.useToken();
  const [form] = Form.useForm<FormValues>();

  // A template is immutable ONCE SET (decision D2). If the project already has
  // a bound template, fields render from the captured snapshot. If it has none,
  // the user may first-time bind one on edit (the backend captures the snapshot
  // on UPDATE). This modal is edit-only, so isEdit is implied.
  const hasBoundTemplate = Boolean(project?.custom_entity_template_root_id);

  // First-time binding selector state (CREATE-less modal, so always user-driven).
  const [selectedTemplateRootId, setSelectedTemplateRootId] = useState<
    string | null
  >(null);
  const [selectedFieldDefs, setSelectedFieldDefs] =
    useState<FieldDefinitions | null>(null);

  // Bound-template field definitions from the captured snapshot. Derived via
  // useMemo (not state) to avoid setState-in-effect cascades.
  const snapshotFieldDefs = useMemo<FieldDefinitions | null>(
    () => (project?.custom_field_definitions_snapshot as FieldDefinitions) ?? null,
    [project],
  );
  const fieldDefs = hasBoundTemplate ? snapshotFieldDefs : selectedFieldDefs;

  // Bound EDIT: overlay the LIVE template's field statuses so deprecated /
  // retired fields render read-only. First-time-bind (no bound template) uses
  // create-mode rendering (field defs already come from the live template).
  const liveStatuses = useLiveTemplateStatuses(
    hasBoundTemplate ? project?.custom_entity_template_root_id : undefined,
  );

  const selectedCurrency = Form.useWatch("currency", form) || project?.currency || "EUR";
  const currencySymbol = useMemo(() => getCurrencySymbol(selectedCurrency), [selectedCurrency]);

  useEffect(() => {
    if (open && project) {
      form.setFieldsValue({
        name: project.name,
        status: project.status || "draft",
        currency: project.currency || "EUR",
        contract_value: project.contract_value
          ? Number(project.contract_value)
          : undefined,
        start_date: project.start_date ? dayjs(project.start_date) : undefined,
        end_date: project.end_date ? dayjs(project.end_date) : undefined,
        description: project.description ?? undefined,
        custom_fields: project.custom_fields ?? {},
      });
      // Reset first-time-binding selector when the modal re-opens. Only the
      // template-less path uses selector state; bound entities render from the
      // snapshot via useMemo above. This is the documented React exception to
      // set-state-in-effect (reset on prop change).
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setSelectedTemplateRootId(null);
      setSelectedFieldDefs(null);
    }
  }, [open, project, form]);

  const handleOk = async () => {
    try {
      const values = await form.validateFields();
      const updateData: ProjectUpdate = {
        name: values.name,
        status: (values.status as ProjectStatus) ?? null,
        currency: values.currency ?? null,
        contract_value: values.contract_value ?? null,
        start_date: values.start_date
          ? values.start_date.toISOString()
          : null,
        end_date: values.end_date ? values.end_date.toISOString() : null,
        description: values.description ?? null,
        custom_fields: serializeCustomFields(
          values.custom_fields as Record<string, unknown> | undefined,
        ),
        // Template binding is immutable once set. Send the template id only
        // when first-time-binding a template-less project (the backend captures
        // the snapshot). Already-bound projects never re-send it.
        custom_entity_template_root_id: hasBoundTemplate
          ? undefined
          : (selectedTemplateRootId ?? null),
      };
      onOk(updateData);
    } catch (error) {
      // Validation failed - don't close modal
      console.log("Validation failed:", error);
    }
  };

  return (
    <Can permission="project-update" fallback={null}>
      <Modal
        title="Edit Project"
        open={open}
        onCancel={onCancel}
        onOk={handleOk}
        confirmLoading={confirmLoading}
        okText="Save Changes"
        cancelText="Cancel"
        width={600}
        styles={{
          body: {
            padding: token.paddingLG,
          },
        }}
        style={{
          borderRadius: token.borderRadiusLG,
        }}
      >
        <Form
          form={form}
          layout="vertical"
          autoComplete="off"
          style={{ marginTop: token.marginMD }}
        >
          <Space direction="vertical" size={token.marginLG} style={{ width: "100%" }}>
            {/* Project Name */}
            <Form.Item
              label="Project Name"
              name="name"
              rules={[
                { required: true, message: "Please enter the project name" },
                { min: 2, message: "Name must be at least 2 characters" },
                { max: 200, message: "Name must not exceed 200 characters" },
              ]}
            >
              <Input
                placeholder="Enter project name"
                style={{
                  borderRadius: token.borderRadius,
                }}
              />
            </Form.Item>

            {/* Status */}
            <Form.Item
              label="Status"
              name="status"
              rules={[{ required: true, message: "Please select a status" }]}
            >
              <Select
                placeholder="Select project status"
                options={PROJECT_STATUSES}
                style={{
                  borderRadius: token.borderRadius,
                }}
              />
            </Form.Item>

            {/* Currency */}
            <Form.Item
              label="Currency"
              name="currency"
              rules={[{ required: true, message: "Please select a currency" }]}
            >
              <Select
                placeholder="Select project currency"
                options={CURRENCY_OPTIONS}
                style={{
                  borderRadius: token.borderRadius,
                }}
              />
            </Form.Item>

            {/* Contract Value */}
            <Form.Item
              label={`Contract Value (${selectedCurrency})`}
              name="contract_value"
              rules={[
                {
                  type: "number",
                  min: 0,
                  message: "Contract value must be a positive number",
                },
              ]}
            >
              <InputNumber
                placeholder="0.00"
                style={{ width: "100%", borderRadius: token.borderRadius }}
                precision={2}
                min={0}
                controls={false}
                addonAfter={currencySymbol}
              />
            </Form.Item>

            {/* Date Range */}
            <Space direction="horizontal" size={token.marginLG} style={{ width: "100%" }}>
              <Form.Item
                label="Start Date"
                name="start_date"
                style={{ width: "100%" }}
              >
                <DatePicker
                  style={{ width: "100%", borderRadius: token.borderRadius }}
                  placeholder="Select start date"
                  format="YYYY-MM-DD"
                />
              </Form.Item>

              <Form.Item
                label="End Date"
                name="end_date"
                rules={[
                  ({ getFieldValue }) => ({
                    validator(_, value) {
                      const startDate = getFieldValue("start_date");
                      if (value && startDate && value.isBefore(startDate, "day")) {
                        return Promise.reject(
                          new Error("End date must be after start date")
                        );
                      }
                      return Promise.resolve();
                    },
                  }),
                ]}
                style={{ width: "100%" }}
              >
                <DatePicker
                  style={{ width: "100%", borderRadius: token.borderRadius }}
                  placeholder="Select end date"
                  format="YYYY-MM-DD"
                />
              </Form.Item>
            </Space>

            {/* Description */}
            <Form.Item
              label="Description"
              name="description"
              rules={[
                { max: 2000, message: "Description must not exceed 2000 characters" },
              ]}
            >
              <Input.TextArea
                placeholder="Enter project description"
                rows={4}
                maxLength={2000}
                showCount
                style={{
                  borderRadius: token.borderRadius,
                }}
              />
            </Form.Item>

            {/* Custom fields (template-driven). Shown only when the project has
                no bound template yet (first-time bind); an already-bound project
                renders from its captured snapshot (immutable binding). */}
            {!hasBoundTemplate && (
              <Form.Item
                name="custom_entity_template_root_id"
                label="Custom Fields Template"
                tooltip="Apply a template to add custom fields. Once saved, the template is bound permanently."
              >
                <TemplateSelector
                  targetType="PROJECT"
                  value={selectedTemplateRootId}
                  onChange={(rootId, defs) => {
                    setSelectedTemplateRootId(rootId);
                    setSelectedFieldDefs(defs ?? null);
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
                id="project-edit-custom-fields"
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
          </Space>
        </Form>
      </Modal>
    </Can>
  );
};
