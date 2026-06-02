import { useEffect, useMemo, useRef } from "react";
import { Modal, Form, Input, Select, InputNumber } from "antd";
import { useTimeMachineParams } from "@/contexts/TimeMachineContext";
import { useThemeTokens } from "@/hooks/useThemeTokens";
import { useControlAccounts } from "@/features/control-accounts/api/useControlAccounts";
import type {
  WorkPackageCreate,
  WorkPackageUpdate,
  WorkPackageRead,
} from "@/api/generated";

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
        });
      } else {
        form.resetFields();
        form.setFieldsValue({
          status: "open",
        });
      }
    }
    prevOpenRef.current = open;
  }, [open, initialValues, form, asOf]);

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
      </Form>
    </Modal>
  );
};
