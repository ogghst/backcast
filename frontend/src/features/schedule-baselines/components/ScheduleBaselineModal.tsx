/**
 * Schedule Baseline Modal Component
 *
 * Modal for creating and editing Schedule Baselines with progression type selection
 * and visual preview of the progression curve.
 */

import { useEffect, useMemo } from "react";
import {
  Modal,
  Form,
  Input,
  Select,
  Button,
  Space,
  Typography,
  Card,
  Alert,
  theme,
} from "antd";
import {
  useCreateCostElementScheduleBaseline,
  useUpdateCostElementScheduleBaseline,
} from "../api/useCostElementScheduleBaseline";
import { ProgressionPreviewChart } from "./ProgressionPreviewChart";
import type { ScheduleBaselineRead } from "../api/useScheduleBaselines";

const { TextArea } = Input;
const { Text } = Typography;

// Progression type options
const PROGRESSION_TYPES = [
  { value: "LINEAR", label: "Linear", description: "Uniform progress over time" },
  {
    value: "GAUSSIAN",
    label: "Gaussian (S-Curve)",
    description: "Slow start, fast middle, tapering end",
  },
  {
    value: "LOGARITHMIC",
    label: "Logarithmic",
    description: "Front-loaded with rapid initial progress",
  },
];

interface ScheduleBaselineModalProps {
  visible: boolean;
  onClose: () => void;
  onSuccess?: (baseline: ScheduleBaselineRead) => void;
  costElementId: string;
  baseline?: ScheduleBaselineRead;
}

export const ScheduleBaselineModal: React.FC<ScheduleBaselineModalProps> = ({
  visible,
  onClose,
  onSuccess,
  costElementId,
  baseline,
}) => {
  const { token } = theme.useToken();
  const isEdit = !!baseline;
  const [form] = Form.useForm();

  // Compute default dates once using useMemo
  const defaultStartDate = useMemo(() => {
    const now = new Date();
    return now.toISOString().split("T")[0];
  }, []);
  const defaultEndDate = useMemo(() => {
    const start = new Date(defaultStartDate);
    const end = new Date(start.getTime() + 365 * 24 * 60 * 60 * 1000);
    return end.toISOString().split("T")[0];
  }, [defaultStartDate]);

  const createMutation = useCreateCostElementScheduleBaseline({
    onSuccess: (data) => {
      form.resetFields();
      onSuccess?.(data);
      onClose();
    },
  });

  const updateMutation = useUpdateCostElementScheduleBaseline({
    onSuccess: (data) => {
      form.resetFields();
      onSuccess?.(data);
      onClose();
    },
  });

  useEffect(() => {
    if (visible) {
      if (baseline) {
        form.setFieldsValue({
          name: baseline.name,
          start_date: baseline.start_date,
          end_date: baseline.end_date,
          progression_type: baseline.progression_type,
          description: baseline.description || "",
        });
      } else {
        form.resetFields();
        form.setFieldsValue({
          start_date: defaultStartDate,
          end_date: defaultEndDate,
          progression_type: "LINEAR",
        });
      }
    }
  }, [visible, baseline, costElementId, form, defaultStartDate, defaultEndDate]);

  const handleValuesChange = (_changedValues: unknown, allValues: Record<string, unknown>) => {
    const progressionType = allValues.progression_type as "LINEAR" | "GAUSSIAN" | "LOGARITHMIC" | undefined;
    const startDate = allValues.start_date as string | undefined;
    const endDate = allValues.end_date as string | undefined;

    // Force re-render by updating form values - preview chart reads from form
    if (progressionType && startDate && endDate) {
      form.setFieldValue("_preview_update", { progressionType, startDate, endDate });
    }
  };

  const handleSubmit = async () => {
    try {
      const values = await form.validateFields();

      if (isEdit && baseline) {
        // Update using nested endpoint
        await updateMutation.mutateAsync({
          costElementId: costElementId,
          baselineId: baseline.schedule_baseline_id,
          data: values,
        });
      } else {
        // Create using nested endpoint (cost element ID is in URL)
        await createMutation.mutateAsync({
          costElementId: costElementId,
          ...values,
        });
      }
    } catch (error) {
      console.error("Form submission error:", error);
    }
  };

  // Get current form values for preview
  const progressionType = Form.useWatch("progression_type", form) || "LINEAR";
  const startDate = Form.useWatch("start_date", form) || defaultStartDate;
  const endDate = Form.useWatch("end_date", form) || defaultEndDate;

  return (
    <Modal
      title={isEdit ? "Edit Schedule Baseline" : "Create Schedule Baseline"}
      open={visible}
      onCancel={onClose}
      footer={null}
      width={700}
      destroyOnClose
    >
      <Form
        layout="vertical"
        form={form}
        onFinish={handleSubmit}
        onValuesChange={handleValuesChange}
      >
        <Form.Item
          label="Baseline Name"
          name="name"
          rules={[{ required: true, message: "Please enter a name" }]}
        >
          <Input placeholder="e.g., Q1 2026 Baseline" />
        </Form.Item>

        <Space.Compact style={{ width: "100%", marginBottom: 16 }}>
          <Form.Item
            label="Start Date"
            name="start_date"
            rules={[{ required: true, message: "Please select a start date" }]}
            style={{ width: "50%", marginBottom: 0 }}
          >
            <Input type="date" style={{ width: "100%" }} />
          </Form.Item>

          <Form.Item
            label="End Date"
            name="end_date"
            rules={[{ required: true, message: "Please select an end date" }]}
            style={{ width: "50%", marginBottom: 0 }}
          >
            <Input type="date" style={{ width: "100%" }} />
          </Form.Item>
        </Space.Compact>

        <Form.Item
          label="Progression Type"
          name="progression_type"
          rules={[{ required: true, message: "Please select a progression type" }]}
          tooltip="The pattern of progress over time for Planned Value calculations"
        >
          <Select placeholder="Select progression type">
            {PROGRESSION_TYPES.map((type) => (
              <Select.Option key={type.value} value={type.value}>
                <div>
                  <div style={{ fontWeight: 500 }}>{type.label}</div>
                  <div style={{ fontSize: 12, color: token.colorTextTertiary }}>{type.description}</div>
                </div>
              </Select.Option>
            ))}
          </Select>
        </Form.Item>

        <Form.Item
          label="Description"
          name="description"
        >
          <TextArea
            rows={3}
            placeholder="Optional description of this baseline..."
          />
        </Form.Item>

        {/* cost_element_id is no longer needed - it's in the URL for nested endpoint */}

        {/* Progression Preview */}
        <Card
          title={
            <Space>
              <span>Progression Preview</span>
              <Text type="secondary" style={{ fontSize: 12 }}>
                ({PROGRESSION_TYPES.find((t) => t.value === progressionType)?.label})
              </Text>
            </Space>
          }
          size="small"
          style={{ marginBottom: 16 }}
        >
          <ProgressionPreviewChart
            progressionType={progressionType}
            startDate={startDate}
            endDate={endDate}
          />
        </Card>

        <Alert
          message="Planned Value Calculation"
          description="PV will be calculated as: PV = BAC × Progress, where Progress is determined by the selected progression type and current date."
          type="info"
          showIcon
          style={{ marginBottom: 16 }}
        />

        <div style={{ textAlign: "right" }}>
          <Space>
            <Button onClick={onClose}>Cancel</Button>
            <Button
              type="primary"
              htmlType="submit"
              loading={createMutation.isPending || updateMutation.isPending}
            >
              {isEdit ? "Update Baseline" : "Create Baseline"}
            </Button>
          </Space>
        </div>
      </Form>
    </Modal>
  );
};
