import { useEffect } from "react";
import { Modal, Form, Input, InputNumber, DatePicker } from "antd";
import type {
  CostRegistrationRead,
  CostRegistrationCreate,
  CostRegistrationUpdate,
} from "@/api/generated";
import dayjs from "dayjs";
import { useTimeMachineParams } from "@/contexts/TimeMachineContext";

interface CostRegistrationModalProps {
  open: boolean;
  onCancel: () => void;
  onOk: (values: CostRegistrationCreate | CostRegistrationUpdate) => void;
  confirmLoading: boolean;
  initialValues?: CostRegistrationRead | null;
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
}: CostRegistrationModalProps) => {
  const [form] = Form.useForm();
  const { asOf } = useTimeMachineParams();
  const isEdit = !!initialValues;

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
  }, [open, initialValues, form]);

  const handleSubmit = async () => {
    try {
      const values = await form.validateFields();

      // Convert dayjs date to ISO string
      const submissionValues = {
        ...values,
        registration_date: values.registration_date
          ? values.registration_date.toISOString()
          : undefined,
      };

      await onOk(submissionValues);
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
      destroyOnClose
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
              return `€ ${value}`.replace(/\B(?=(\d{3})+(?!\d))/g, ",");
            }}
            parser={(value) => {
              if (!value) return undefined as unknown as number;
              const cleaned = value.replace(/€\s?|,/g, "");
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
