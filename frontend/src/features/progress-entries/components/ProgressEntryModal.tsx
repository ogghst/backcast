import { useState } from "react";
import {
  Modal,
  Form,
  InputNumber,
  Input,
  Alert,
  Space,
} from "antd";
import type {
  ProgressEntryCreate,
} from "@/api/generated";
import { useLatestProgress } from "../api/useProgressEntries";
import dayjs from "dayjs";
import { useTimeMachineParams } from "@/contexts/TimeMachineContext";

interface ProgressEntryModalProps {
  open: boolean;
  onCancel: () => void;
  onOk: (values: ProgressEntryCreate) => void;
  confirmLoading: boolean;
  costElementId: string;
}

/**
 * Modal form for creating progress entries.
 *
 * Progress entries are immutable — this modal only creates new entries.
 * - Progress percentage validation (0-100, 2 decimals)
 * - Notes field (optional, but recommended when progress decreases)
 * - Warning display when progress decreases from latest
 */
export const ProgressEntryModal = ({
  open,
  onCancel,
  onOk,
  confirmLoading,
  costElementId,
}: ProgressEntryModalProps) => {
  const [form] = Form.useForm();
  const { asOf } = useTimeMachineParams();

  // Get latest progress for comparison (to warn on decreases)
  const { data: latestProgress } = useLatestProgress(costElementId);

  // Track decrease warning state
  const [showDecreaseWarning, setShowDecreaseWarning] = useState(false);

  // Check if progress is decreasing
  const checkProgressDecrease = (value: number | null) => {
    if (value === null || value === undefined) {
      setShowDecreaseWarning(false);
      return;
    }

    // Show warning if new progress is less than latest
    if (
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
      const formattedValues: ProgressEntryCreate = {
        progress_percentage: values.progress_percentage,
        control_date: asOf || null,
        notes: values.notes || null,
        cost_element_id: costElementId,
      };

      await onOk(formattedValues);
    } catch (error) {
      console.error("Form submission error:", error);
    }
  };

  return (
    <Modal
      title="Record Progress"
      open={open}
      onCancel={onCancel}
      onOk={handleSubmit}
      okText="Record"
      confirmLoading={confirmLoading}
      destroyOnClose
      width={600}
    >
      <Form
        form={form}
        layout="vertical"
        name="progress_entry_form"
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
            parser={(value) => parseFloat(value?.replace("%", "") || "0")}
            onChange={checkProgressDecrease}
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

        {latestProgress && (
          <Alert
            message={
              <Space>
                <span>Latest Progress: </span>
                <strong>{latestProgress.progress_percentage}%</strong>
                <span>
                  (
                  {latestProgress.valid_time_formatted?.lower
                    ? dayjs(latestProgress.valid_time_formatted.lower).format(
                        "YYYY-MM-DD HH:mm",
                      )
                    : "-"}
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
