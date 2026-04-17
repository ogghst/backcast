import { useEffect } from "react";
import { Modal, Form, Input, InputNumber, DatePicker, Select } from "antd";
import type {
  QualityEventRead,
  QualityEventCreate,
  QualityEventUpdate,
} from "@/api/generated";
import dayjs from "dayjs";
import { useTimeMachineParams } from "@/contexts/TimeMachineContext";
import { useThemeTokens } from "@/hooks/useThemeTokens";

interface QualityEventModalProps {
  open: boolean;
  onCancel: () => void;
  onOk: (values: QualityEventCreate | QualityEventUpdate) => void;
  confirmLoading: boolean;
  initialValues?: QualityEventRead | null;
  costElementId: string;
}

// Event type options
const EVENT_TYPE_OPTIONS = [
  { label: "Defect", value: "defect" },
  { label: "Rework", value: "rework" },
  { label: "Scrap", value: "scrap" },
  { label: "Warranty", value: "warranty" },
  { label: "Other", value: "other" },
].sort((a, b) => a.label.localeCompare(b.label));

// Severity options
const SEVERITY_OPTIONS = [
  { label: "Low", value: "low" },
  { label: "Medium", value: "medium" },
  { label: "High", value: "high" },
  { label: "Critical", value: "critical" },
].sort((a, b) => a.label.localeCompare(b.label));

export const QualityEventModal = ({
  open,
  onCancel,
  onOk,
  confirmLoading,
  initialValues,
  costElementId,
}: QualityEventModalProps) => {
  const [form] = Form.useForm();
  const { asOf } = useTimeMachineParams();
  const { spacing } = useThemeTokens();
  const isEdit = !!initialValues;

  useEffect(() => {
    if (open) {
      if (initialValues) {
        // Set form values for edit mode
        const formValues = {
          event_type: initialValues.event_type,
          severity: initialValues.severity,
          event_date: initialValues.event_date
            ? dayjs(initialValues.event_date)
            : dayjs(),
          description: initialValues.description,
          cost_impact: Number(initialValues.cost_impact),
          root_cause: initialValues.root_cause,
          resolution_notes: initialValues.resolution_notes,
        };
        form.setFieldsValue(formValues);
      } else {
        // Reset form for create mode with default date
        form.resetFields();
        form.setFieldsValue({
          event_date: asOf ? dayjs(asOf) : dayjs(),
          event_type: "defect",
          severity: "medium",
        });
      }
    }
  }, [open, initialValues, form, asOf]);

  const handleSubmit = async () => {
    try {
      const values = await form.validateFields();

      // Convert dayjs date to ISO string
      const submissionValues = {
        ...values,
        event_date: values.event_date
          ? values.event_date.toISOString()
          : undefined,
        cost_element_id: costElementId,
      };

      await onOk(submissionValues);
    } catch (error) {
      console.error("Form submission error:", error);
    }
  };

  return (
    <Modal
      title={isEdit ? "Edit Quality Event" : "Add Quality Event"}
      open={open}
      onCancel={onCancel}
      onOk={handleSubmit}
      okText={isEdit ? "Save" : "Create"}
      confirmLoading={confirmLoading}
      destroyOnClose
      width={600}
    >
      <Form form={form} layout="vertical" name="quality_event_form">
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "1fr 1fr",
            gap: spacing.md,
          }}
        >
          <Form.Item
            name="event_type"
            label="Event Type"
            rules={[{ required: true, message: "Please select event type" }]}
          >
            <Select
              placeholder="Select event type"
              options={EVENT_TYPE_OPTIONS}
            />
          </Form.Item>

          <Form.Item
            name="severity"
            label="Severity"
            rules={[{ required: true, message: "Please select severity" }]}
          >
            <Select
              placeholder="Select severity"
              options={SEVERITY_OPTIONS}
            />
          </Form.Item>
        </div>

        <Form.Item
          name="event_date"
          label="Event Date"
          rules={[{ required: true, message: "Please select event date" }]}
        >
          <DatePicker
            style={{ width: "100%" }}
            showTime
            format="YYYY-MM-DD HH:mm"
            placeholder="Select date and time"
          />
        </Form.Item>

        <Form.Item
          name="cost_impact"
          label="Cost Impact"
          rules={[
            { required: true, message: "Please enter cost impact" },
            {
              type: "number",
              min: 0.01,
              message: "Cost impact must be greater than 0",
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

        <Form.Item
          name="description"
          label="Description"
          rules={[
            { required: true, message: "Please enter description" },
            { min: 10, message: "Description must be at least 10 characters" },
          ]}
        >
          <Input.TextArea
            placeholder="Describe the quality issue"
            rows={3}
            maxLength={1000}
            showCount
          />
        </Form.Item>

        <Form.Item
          name="root_cause"
          label="Root Cause (optional)"
        >
          <Input.TextArea
            placeholder="Root cause analysis"
            rows={2}
            maxLength={500}
            showCount
          />
        </Form.Item>

        <Form.Item
          name="resolution_notes"
          label="Resolution Notes (optional)"
        >
          <Input.TextArea
            placeholder="Resolution details and corrective actions"
            rows={2}
            maxLength={500}
            showCount
          />
        </Form.Item>
      </Form>
    </Modal>
  );
};
