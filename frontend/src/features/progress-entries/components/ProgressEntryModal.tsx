import { useState } from "react";
import {
  Modal,
  Form,
  InputNumber,
  DatePicker,
  Input,
  Alert,
  Space,
} from "antd";
import type {
  ProgressEntryRead,
  ProgressEntryCreate,
  ProgressEntryUpdate,
} from "@/api/generated";
import { useLatestProgress } from "../api/useProgressEntries";
import dayjs from "dayjs";
import { useTimeMachineParams } from "@/contexts/TimeMachineContext";

interface ProgressEntryModalProps {
  open: boolean;
  onCancel: () => void;
  onOk: (values: ProgressEntryCreate | ProgressEntryUpdate) => void;
  confirmLoading: boolean;
  initialValues?: ProgressEntryRead | null;
  costElementId: string;
}

/**
 * Modal form for creating/updating progress entries.
 *
 * Features:
 * - Progress percentage validation (0-100, 2 decimals)
 * - Date picker with time support
 * - Notes field (optional, but recommended when progress decreases)
 * - Warning display when progress decreases from latest
 */
export const ProgressEntryModal = ({
  open,
  onCancel,
  onOk,
  confirmLoading,
  initialValues,
  costElementId,
}: ProgressEntryModalProps) => {
  const [form] = Form.useForm();
  const isEdit = !!initialValues;
  const { asOf } = useTimeMachineParams();

  // Get latest progress for comparison (to warn on decreases)
  const { data: latestProgress } = useLatestProgress(costElementId);

  // Track decrease warning state
  const [showDecreaseWarning, setShowDecreaseWarning] = useState(false);

  // Set initial form values
  const initialValuesForForm = initialValues
    ? {
        progress_percentage: parseFloat(initialValues.progress_percentage),
        reported_date: dayjs(initialValues.reported_date),
        notes: initialValues.notes || "",
      }
    : {
        reported_date: asOf ? dayjs(asOf) : dayjs(),
      };

  // Check if progress is decreasing
  const checkProgressDecrease = (value: number | null) => {
    if (value === null || value === undefined) {
      setShowDecreaseWarning(false);
      return;
    }

    // Show warning if new progress is less than latest (only for create mode)
    if (
      !isEdit &&
      latestProgress &&
      value < parseFloat(latestProgress.progress_percentage)
    ) {
      setShowDecreaseWarning(true);
    } else {
      setShowDecreaseWarning(false);
    }
  };

  const handleSubmit = async () => {
    try {
      const values = await form.validateFields();

      // Format the data for API
      const formattedValues: ProgressEntryCreate | ProgressEntryUpdate = {
        progress_percentage: values.progress_percentage,
        reported_date: values.reported_date.toISOString(),
        notes: values.notes || null,
      };

      // Add cost_element_id for create only
      if (!isEdit) {
        (formattedValues as ProgressEntryCreate).cost_element_id =
          costElementId;
        // Note: reported_by_user_id is auto-injected in the API hook
      }

      await onOk(formattedValues);
    } catch (error) {
      console.error("Form submission error:", error);
    }
  };

  return (
    <Modal
      title={isEdit ? "Edit Progress Entry" : "Record Progress"}
      open={open}
      onCancel={onCancel}
      onOk={handleSubmit}
      okText={isEdit ? "Save" : "Record"}
      confirmLoading={confirmLoading}
      destroyOnClose
      width={600}
    >
      <Form
        form={form}
        layout="vertical"
        name="progress_entry_form"
        initialValues={initialValuesForForm}
      >
        {showDecreaseWarning && (
          <Alert
            message="Progress Decrease Detected"
            description="You are recording a decrease in progress. Please add notes explaining why this has occurred."
            type="warning"
            showIcon
            style={{ marginBottom: 16 }}
          />
        )}

        <Form.Item
          name="progress_percentage"
          label="Progress Percentage"
          rules={[
            { required: true, message: "Please enter progress percentage" },
            {
              type: "number",
              min: 0,
              max: 100,
              message: "Progress must be between 0 and 100",
            },
          ]}
        >
          <InputNumber
            style={{ width: "100%" }}
            min={0}
            max={100}
            step={0.01}
            precision={2}
            formatter={(value) => `${value}%`}
            parser={(value) => value?.replace("%", "") as unknown as number}
            onChange={checkProgressDecrease}
          />
        </Form.Item>

        <Form.Item
          name="reported_date"
          label="Reported Date"
          rules={[{ required: true, message: "Please select a date and time" }]}
        >
          <DatePicker
            showTime
            style={{ width: "100%" }}
            format="YYYY-MM-DD HH:mm"
            placeholder="Select date and time"
          />
        </Form.Item>

        <Form.Item
          name="notes"
          label="Notes"
          tooltip={
            showDecreaseWarning
              ? "Recommended: explain why progress decreased"
              : "Optional: add context about this progress entry"
          }
        >
          <Input.TextArea
            placeholder={
              showDecreaseWarning
                ? "Please explain why progress has decreased..."
                : "Add notes (optional)"
            }
            rows={3}
            maxLength={1000}
            showCount
          />
        </Form.Item>

        {latestProgress && !isEdit && (
          <Alert
            message={
              <Space>
                <span>Latest Progress: </span>
                <strong>{latestProgress.progress_percentage}%</strong>
                <span>
                  (
                  {dayjs(latestProgress.reported_date).format(
                    "YYYY-MM-DD HH:mm",
                  )}
                  )
                </span>
              </Space>
            }
            type="info"
            showIcon
          />
        )}
      </Form>
    </Modal>
  );
};
