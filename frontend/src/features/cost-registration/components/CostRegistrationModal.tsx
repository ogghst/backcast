import { useEffect, useMemo, useRef } from "react";
import { App, Modal, Form, Input, InputNumber, DatePicker, Select, Button, Space, Typography, Tooltip, theme } from "antd";
import {
  DeleteOutlined,
  DownloadOutlined,
  PaperClipOutlined,
  UploadOutlined,
} from "@ant-design/icons";
import type {
  CostRegistrationRead,
  CostRegistrationCreate,
  CostRegistrationUpdate,
} from "@/api/generated";
import dayjs from "dayjs";
import { useTimeMachineParams } from "@/contexts/TimeMachineContext";
import {
  useBudgetStatus,
  useProjectBudgetSettings,
} from "../api/useCostRegistrations";
import {
  useCostRegistrationAttachments,
  useUploadAttachment,
  useDeleteAttachment,
  downloadAttachment,
} from "../api/useCostRegistrationAttachments";
import { getCurrencySymbol } from "@/utils/formatters";
import { useThemeTokens } from "@/hooks/useThemeTokens";
import { useProjectCurrency } from "@/features/projects/api/useProjectCurrency";
import { useCostEvents, useCostEventTypes } from "@/features/cost-events/api/useCostEvents";
import { formatFileSize } from "@/features/ai/chat/api/attachmentUpload";
import { toast } from "sonner";

const { Text } = Typography;

/** Max file size in bytes (10MB default, should match backend config). */
const MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024;

interface CostRegistrationModalProps {
  open: boolean;
  onCancel: () => void;
  onOk: (values: CostRegistrationCreate | CostRegistrationUpdate) => void;
  confirmLoading: boolean;
  initialValues?: CostRegistrationRead | null;
  costElementId: string;
  projectId: string;
}

// Common unit of measure options
const UNIT_OPTIONS = [
  { label: "Hours", value: "hours" },
  { label: "Days", value: "days" },
  { label: "Each", value: "each" },
  { label: "kg", value: "kg" },
  { label: "m", value: "m" },
  { label: "m²", value: "m²" },
  { label: "m³", value: "m³" },
  { label: "liters", value: "liters" },
  { label: "units", value: "units" },
].sort((a, b) => a.label.localeCompare(b.label));

export const CostRegistrationModal = ({
  open,
  onCancel,
  onOk,
  confirmLoading,
  initialValues,
  costElementId,
  projectId,
}: CostRegistrationModalProps) => {
  const [form] = Form.useForm();
  const { asOf } = useTimeMachineParams();
  const { modal } = App.useApp();
  const { data: budgetStatus } = useBudgetStatus(costElementId);
  const { data: projectBudgetSettings } = useProjectBudgetSettings(projectId);
  const isEdit = !!initialValues;
  const enforceBudget = projectBudgetSettings?.enforce_budget ?? false;
  const currency = useProjectCurrency(projectId);
  const currencySymbol = getCurrencySymbol(currency);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const { token } = theme.useToken();
  const { spacing, typography, borderRadius } = useThemeTokens();

  // Fetch open work packages for the project
  const { data: wpData, isLoading: wpLoading } = useCostEvents({
    project_id: projectId,
    status: "open",
    perPage: 100,
  });

  // Fetch package types for label resolution
  const { data: packageTypeOptions } = useCostEventTypes();

  const workPackageOptions = (wpData?.items || []).map((wp) => {
    const typeLabel = packageTypeOptions?.find((o) => o.value === wp.cost_event_type_id)?.label || wp.cost_event_type_code || wp.cost_event_type_name || "";
    return {
      label: `${wp.name} (${typeLabel})`,
      value: wp.cost_event_id,
    };
  });

  // Attachment hooks (only for edit mode)
  const costRegId = isEdit ? initialValues?.cost_registration_id ?? null : null;
  const { data: attachments = [], isLoading: attachmentsLoading } =
    useCostRegistrationAttachments(costRegId);
  const uploadMutation = useUploadAttachment(costRegId ?? "");
  const deleteMutation = useDeleteAttachment(costRegId ?? "");

  const handleFileUpload = (file: File) => {
    if (file.size > MAX_FILE_SIZE_BYTES) {
      toast.error(`File too large. Maximum size: ${formatFileSize(MAX_FILE_SIZE_BYTES)}`);
      return;
    }
    uploadMutation.mutate(file);
  };

  const handleDeleteAttachment = (attachmentId: string, filename: string) => {
    modal.confirm({
      title: "Delete Attachment",
      content: `Are you sure you want to delete "${filename}"?`,
      okText: "Delete",
      okType: "danger",
      onOk: () => deleteMutation.mutateAsync(attachmentId),
    });
  };

  const currencyFormatValue = useMemo(
    () => (value: string | number | undefined) => {
      if (!value) return "";
      return `${currencySymbol} ${value}`.replace(/\B(?=(\d{3})+(?!\d))/g, ",");
    },
    [currencySymbol],
  );

  const currencyParseValue = useMemo(
    () =>
      new RegExp(`\\${currencySymbol}\\s?|(,*)`, "g"),
    [currencySymbol],
  );

  const formatBudgetDisplay = (amount: number) =>
    `${currencySymbol}${amount.toLocaleString(undefined, { minimumFractionDigits: 2 })}`;

  useEffect(() => {
    if (open) {
      if (initialValues) {
        // Set form values for edit mode
        const formValues = {
          amount: initialValues.amount,
          quantity: initialValues.quantity,
          unit_of_measure: initialValues.unit_of_measure,
          registration_date: initialValues.registration_date
            ? dayjs(initialValues.registration_date)
            : dayjs(),
          description: initialValues.description,
          invoice_number: initialValues.invoice_number,
          vendor_reference: initialValues.vendor_reference,
          work_package_id: initialValues.cost_element_id,
        };
        form.setFieldsValue(formValues);
      } else {
        // Reset form for create mode with default date
        form.resetFields();
        form.setFieldsValue({
          registration_date: asOf ? dayjs(asOf) : dayjs(),
        });
      }
    }
  }, [open, initialValues, form, asOf]);

  const processSubmit = async (values: Record<string, unknown>) => {
    // Convert dayjs date to ISO string
    const submissionValues = {
      ...values,
      registration_date: values.registration_date
        ? (values.registration_date as unknown as { toISOString: () => string }).toISOString()
        : undefined,
    };

    await onOk(submissionValues);
  };

  const handleSubmit = async () => {
    try {
      const values = await form.validateFields();

      const newAmount = Number(values.amount || 0);

      // Cost element-level budget validation
      const costElementBudget = budgetStatus
        ? Number(budgetStatus.budget)
        : 0;
      const costElementUsed = budgetStatus ? Number(budgetStatus.used) : 0;

      // Calculate effective used amount (subtract old amount if editing)
      let effectiveCostElementUsed = costElementUsed;
      if (isEdit && initialValues) {
        effectiveCostElementUsed -= Number(initialValues.amount);
      }

      // Get project warning threshold (default to 85% if not configured)
      const warningThresholdPercent = projectBudgetSettings
        ? Number(projectBudgetSettings.warning_threshold_percent || 85)
        : 85;

      // Calculate cost element warning limit
      const costElementWarningLimit = costElementBudget * (warningThresholdPercent / 100);
      const projectedCostElementSpend = effectiveCostElementUsed + newAmount;

      // Check if cost element budget will be exceeded
      if (costElementBudget > 0 && projectedCostElementSpend > costElementBudget) {
        if (enforceBudget) {
          // Hard block — enforcement is on
          modal.error({
            title: "Budget Limit Reached",
            content: (
              <div>
                <p>
                  Budget enforcement is enabled. This cost registration would exceed the cost element budget.
                </p>
                <div style={{ marginTop: spacing.sm, marginBottom: spacing.sm, padding: spacing.sm, backgroundColor: token.colorErrorBg, borderRadius: borderRadius.sm, border: `1px solid ${token.colorErrorBorder}` }}>
                  <p style={{ margin: 0 }}><strong>Cost Element Budget:</strong> {formatBudgetDisplay(costElementBudget)}</p>
                  <p style={{ margin: 0 }}><strong>Currently Used:</strong> {formatBudgetDisplay(effectiveCostElementUsed)}</p>
                  <p style={{ margin: 0, color: token.colorError }}><strong>Projected Total:</strong> {formatBudgetDisplay(projectedCostElementSpend)}</p>
                  <p style={{ margin: 0, fontSize: typography.sizes.sm, color: token.colorTextTertiary }}>
                    Over budget by: {formatBudgetDisplay(projectedCostElementSpend - costElementBudget)}
                  </p>
                </div>
                <p>Contact your project manager to increase the budget or disable enforcement.</p>
              </div>
            ),
            okText: "Understood",
          });
          return;
        }
        modal.confirm({
          title: "Cost Element Budget Exceeded",
          content: (
            <div>
              <p>
                This cost registration will exceed the <strong>cost element budget</strong>.
              </p>
              <div
                style={{
                  marginTop: spacing.sm,
                  marginBottom: spacing.sm,
                  padding: spacing.sm,
                  backgroundColor: token.colorErrorBg,
                  borderRadius: borderRadius.sm,
                  border: `1px solid ${token.colorErrorBorder}`,
                }}
              >
                <p style={{ margin: 0 }}>
                  <strong>Cost Element Budget:</strong>{" "}
                  {formatBudgetDisplay(costElementBudget)}
                </p>
                <p style={{ margin: 0 }}>
                  <strong>Currently Used:</strong>{" "}
                  {formatBudgetDisplay(effectiveCostElementUsed)}
                </p>
                <p style={{ margin: 0, color: token.colorError }}>
                  <strong>Projected Total:</strong>{" "}
                  {formatBudgetDisplay(projectedCostElementSpend)}
                </p>
                <p style={{ margin: 0, fontSize: typography.sizes.sm, color: token.colorTextTertiary }}>
                  Over budget by:{" "}
                  {formatBudgetDisplay(projectedCostElementSpend - costElementBudget)}
                </p>
              </div>
              <p>Are you sure you want to proceed?</p>
            </div>
          ),
          okText: "Yes, Proceed",
          okButtonProps: { danger: true },
          cancelText: "Cancel",
          onOk: () => processSubmit(values),
        });
        return;
      }

      // Check if cost element spend exceeds warning threshold
      if (costElementBudget > 0 && projectedCostElementSpend > costElementWarningLimit) {
        const projectedPercentage = (projectedCostElementSpend / costElementBudget) * 100;
        modal.confirm({
          title: "Cost Element Budget Warning",
          content: (
            <div>
              <p>
                This cost registration will <strong>exceed the cost element threshold</strong> (warning threshold: {warningThresholdPercent}%).
              </p>
              <div
                style={{
                  marginTop: spacing.sm,
                  marginBottom: spacing.sm,
                  padding: spacing.sm,
                  backgroundColor: token.colorWarningBg,
                  borderRadius: borderRadius.sm,
                  border: `1px solid ${token.colorWarningBorder}`,
                }}
              >
                <p style={{ margin: 0 }}>
                  <strong>Cost Element Budget:</strong>{" "}
                  {formatBudgetDisplay(costElementBudget)}
                </p>
                <p style={{ margin: 0 }}>
                  <strong>Currently Used:</strong>{" "}
                  {formatBudgetDisplay(effectiveCostElementUsed)}{" "}
                  ({((effectiveCostElementUsed / costElementBudget) * 100).toFixed(1)}%)
                </p>
                <p style={{ margin: 0, color: token.colorWarning }}>
                  <strong>Projected Total:</strong>{" "}
                  {formatBudgetDisplay(projectedCostElementSpend)}{" "}
                  ({projectedPercentage.toFixed(1)}%)
                </p>
                <p style={{ margin: 0, fontSize: typography.sizes.sm, color: token.colorTextTertiary }}>
                  <strong>Warning threshold:</strong> {warningThresholdPercent}% ({formatBudgetDisplay(costElementWarningLimit)})
                </p>
              </div>
              <p>Are you sure you want to proceed?</p>
            </div>
          ),
          okText: "Yes, Proceed",
          okButtonProps: { danger: false },
          cancelText: "Cancel",
          onOk: () => processSubmit(values),
        });
        return;
      }

      await processSubmit(values);
    } catch (error) {
      console.error("Form submission error:", error);
    }
  };

  return (
    <Modal
      title={isEdit ? "Edit Cost Registration" : "Add Cost Registration"}
      open={open}
      onCancel={onCancel}
      onOk={handleSubmit}
      okText={isEdit ? "Save" : "Create"}
      confirmLoading={confirmLoading}
      destroyOnHidden
      width={650}
    >
      <Form form={form} layout="vertical" name="cost_registration_form">
        <Form.Item
          name="amount"
          label="Amount"
          rules={[
            { required: true, message: "Please enter amount" },
            {
              type: "number",
              min: 0.01,
              message: "Amount must be greater than 0",
            },
          ]}
        >
          <InputNumber
            style={{ width: "100%" }}
            controls={false}
            precision={2}
            min={0.01}
            placeholder="0.00"
            formatter={(value) => {
              if (!value) return "";
              return currencyFormatValue(value);
            }}
            parser={((value: string | undefined) => {
              if (!value) return 0;
              const cleaned = value.replace(currencyParseValue, "");
              return parseFloat(cleaned) || 0;
            }) as never}
          />
        </Form.Item>

        <datalist id="unit-options">
          {UNIT_OPTIONS.map((option) => (
            <option key={option.value} value={option.value}>
              {option.label}
            </option>
          ))}
        </datalist>

        <div
          style={{
            display: "grid",
            gridTemplateColumns: "1fr 1fr",
            gap: "16px",
          }}
        >
          <Form.Item name="quantity" label="Quantity (optional)">
            <InputNumber
              style={{ width: "100%" }}
              precision={2}
              min={0}
              placeholder="0.00"
            />
          </Form.Item>

          <Form.Item name="unit_of_measure" label="Unit of Measure (optional)">
            <Input list="unit-options" placeholder="e.g., hours, kg, m, each" />
          </Form.Item>
        </div>

        <Form.Item
          name="registration_date"
          label="Registration Date"
          rules={[{ required: true, message: "Please select date" }]}
        >
          <DatePicker
            style={{ width: "100%" }}
            showTime
            format="YYYY-MM-DD HH:mm"
            placeholder="Select date and time"
          />
        </Form.Item>

        <Form.Item name="work_package_id" label="Work Package (optional)">
          <Select
            placeholder="Select work package"
            allowClear
            showSearch
            optionFilterProp="label"
            options={workPackageOptions}
            loading={wpLoading}
          />
        </Form.Item>

        <Form.Item name="description" label="Description (optional)">
          <Input.TextArea
            placeholder="Description of the cost"
            rows={3}
            maxLength={500}
            showCount
          />
        </Form.Item>

        <div
          style={{
            display: "grid",
            gridTemplateColumns: "1fr 1fr",
            gap: "16px",
          }}
        >
          <Form.Item name="invoice_number" label="Invoice Number (optional)">
            <Input placeholder="INV-001" />
          </Form.Item>

          <Form.Item
            name="vendor_reference"
            label="Vendor Reference (optional)"
          >
            <Input placeholder="Supplier name or reference" />
          </Form.Item>
        </div>

        {/* Attachments section - visible in edit mode when cost registration exists */}
        {isEdit && costRegId && (
          <Form.Item label="Attachments">
            <div style={{ marginBottom: spacing.sm }}>
              <input
                ref={fileInputRef}
                type="file"
                style={{ display: "none" }}
                onChange={(e) => {
                  const file = e.target.files?.[0];
                  if (file) handleFileUpload(file);
                  e.target.value = "";
                }}
              />
              <Button
                icon={<UploadOutlined />}
                onClick={() => fileInputRef.current?.click()}
                loading={uploadMutation.isPending}
                size="small"
              >
                {uploadMutation.isPending ? `Uploading ${uploadMutation.variables?.name}...` : "Upload File"}
              </Button>
              <Text
                type="secondary"
                style={{ marginLeft: spacing.sm, fontSize: typography.sizes.sm }}
              >
                Max {formatFileSize(MAX_FILE_SIZE_BYTES)}
              </Text>
            </div>

            {attachmentsLoading ? (
              <Text type="secondary">Loading attachments...</Text>
            ) : attachments.length === 0 ? (
              <Text type="secondary">No attachments</Text>
            ) : (
              <div style={{ display: "flex", flexDirection: "column", gap: spacing.xs }}>
                {attachments.map((att) => (
                  <div
                    key={att.id}
                    style={{
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "space-between",
                      padding: `${spacing.xs}px ${spacing.sm}px`,
                      backgroundColor: token.colorFillTertiary,
                      borderRadius: borderRadius.sm,
                      border: `1px solid ${token.colorBorderSecondary}`,
                    }}
                  >
                    <Space size={spacing.xs}>
                      <PaperClipOutlined />
                      <Text
                        ellipsis
                        style={{ maxWidth: 250, cursor: "pointer" }}
                        onClick={() =>
                          downloadAttachment(costRegId, att.id, att.filename)
                        }
                      >
                        {att.filename}
                      </Text>
                      <Text type="secondary" style={{ fontSize: typography.sizes.xs }}>
                        ({formatFileSize(att.size)})
                      </Text>
                    </Space>
                    <Space size={spacing.xs}>
                      <Tooltip title="Download">
                        <Button
                          type="text"
                          size="small"
                          icon={<DownloadOutlined />}
                          onClick={() =>
                            downloadAttachment(costRegId, att.id, att.filename)
                          }
                        />
                      </Tooltip>
                      <Tooltip title="Delete">
                        <Button
                          type="text"
                          size="small"
                          danger
                          icon={<DeleteOutlined />}
                          loading={deleteMutation.isPending}
                          onClick={() =>
                            handleDeleteAttachment(att.id, att.filename)
                          }
                        />
                      </Tooltip>
                    </Space>
                  </div>
                ))}
              </div>
            )}
          </Form.Item>
        )}

        {/* Show hint for create mode */}
        {!isEdit && (
          <Text type="secondary" style={{ fontSize: typography.sizes.sm }}>
            <PaperClipOutlined style={{ marginRight: spacing.xs }} />
            Attachments can be added after creating the cost registration.
          </Text>
        )}
      </Form>
    </Modal>
  );
};
