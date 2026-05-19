import { useEffect, useMemo } from "react";
import { App, Modal, Form, Input, InputNumber, DatePicker } from "antd";
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
import { getCurrencySymbol } from "@/utils/formatters";
import { useProjectCurrency } from "@/features/projects/api/useProjectCurrency";

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
        ? values.registration_date.toISOString()
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
                <div style={{ marginTop: 8, marginBottom: 8, padding: 8, background: "#fff1f0", borderRadius: 4, border: "1px solid #ffccc7" }}>
                  <p style={{ margin: 0 }}><strong>Cost Element Budget:</strong> {formatBudgetDisplay(costElementBudget)}</p>
                  <p style={{ margin: 0 }}><strong>Currently Used:</strong> {formatBudgetDisplay(effectiveCostElementUsed)}</p>
                  <p style={{ margin: 0, color: "#cf1322" }}><strong>Projected Total:</strong> {formatBudgetDisplay(projectedCostElementSpend)}</p>
                  <p style={{ margin: 0, fontSize: "12px", color: "#666" }}>
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
                  marginTop: 8,
                  marginBottom: 8,
                  padding: 8,
                  background: "#fff1f0",
                  borderRadius: 4,
                  border: "1px solid #ffccc7",
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
                <p style={{ margin: 0, color: "#cf1322" }}>
                  <strong>Projected Total:</strong>{" "}
                  {formatBudgetDisplay(projectedCostElementSpend)}
                </p>
                <p style={{ margin: 0, fontSize: "12px", color: "#666" }}>
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
                  marginTop: 8,
                  marginBottom: 8,
                  padding: 8,
                  background: "#fffbe6",
                  borderRadius: 4,
                  border: "1px solid #ffe58f",
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
                <p style={{ margin: 0, color: "#d46b08" }}>
                  <strong>Projected Total:</strong>{" "}
                  {formatBudgetDisplay(projectedCostElementSpend)}{" "}
                  ({projectedPercentage.toFixed(1)}%)
                </p>
                <p style={{ margin: 0, fontSize: "12px", color: "#666" }}>
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
      width={600}
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
            parser={(value) => {
              if (!value) return undefined as unknown as number;
              const cleaned = value.replace(currencyParseValue, "");
              const parsed = parseFloat(cleaned);
              return isNaN(parsed) ? undefined : parsed;
            }}
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
      </Form>
    </Modal>
  );
};
