import { useEffect, useMemo } from "react";
import { Modal, Form, Input, InputNumber, DatePicker, Select } from "antd";
import dayjs from "dayjs";
import type {
  ProjectRead,
  ProjectCreate,
  ProjectUpdate,
} from "@/api/generated";
import { getCurrencySymbol } from "@/utils/formatters";

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
        });
      } else {
        form.resetFields();
        form.setFieldsValue({ currency: "EUR" });
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
      </Form>
    </Modal>
  );
};
