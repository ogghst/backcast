import { useEffect, useMemo } from "react";
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
import { CustomFieldsRenderer } from "@/features/custom-fields/components/CustomFieldsRenderer";
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

  // Edit-only: render custom fields from the entity's captured snapshot.
  // Template binding is immutable post-create, so there is no selector here.
  // Derived via useMemo (not state) to avoid setState-in-effect cascades.
  const snapshotFieldDefs = useMemo<FieldDefinitions | null>(
    () => (project?.custom_field_definitions_snapshot as FieldDefinitions) ?? null,
    [project],
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
      // snapshotFieldDefs is derived via useMemo above.
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

            {/* Custom fields rendered from the captured snapshot. Template
                binding is immutable post-create, so no selector here. */}
            {snapshotFieldDefs &&
              Object.keys(snapshotFieldDefs).length > 0 && (
                <CollapsibleCard
                  id="project-edit-custom-fields"
                  title="Custom Fields"
                  keepMounted
                >
                  <CustomFieldsRenderer fieldDefinitions={snapshotFieldDefs} />
                </CollapsibleCard>
              )}
          </Space>
        </Form>
      </Modal>
    </Can>
  );
};
