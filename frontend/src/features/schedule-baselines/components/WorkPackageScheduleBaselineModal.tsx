/**
 * Work Package Schedule Baseline Modal
 *
 * Modal for creating and editing schedule baselines scoped to a work package.
 * Uses work-package nested endpoints (1:1 relationship).
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
import type { ScheduleBaselineRead } from "@/api/generated";
import {
  useCreateWorkPackageScheduleBaseline,
  useUpdateWorkPackageScheduleBaseline,
} from "../api/useWorkPackageScheduleBaseline";
import { ProgressionPreviewChart } from "./ProgressionPreviewChart";

const { TextArea } = Input;
const { Text } = Typography;

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

interface WorkPackageScheduleBaselineModalProps {
  visible: boolean;
  onClose: () => void;
  onSuccess?: (baseline: ScheduleBaselineRead) => void;
  workPackageId: string;
  baseline?: ScheduleBaselineRead | null;
}

export const WorkPackageScheduleBaselineModal: React.FC<
  WorkPackageScheduleBaselineModalProps
> = ({ visible, onClose, onSuccess, workPackageId, baseline }) => {
  const { token } = theme.useToken();
  const isEdit = !!baseline;
  const [form] = Form.useForm();

  const defaultStartDate = useMemo(() => {
    return new Date().toISOString().split("T")[0];
  }, []);
  const defaultEndDate = useMemo(() => {
    const start = new Date(defaultStartDate);
    return new Date(start.getTime() + 365 * 24 * 60 * 60 * 1000)
      .toISOString()
      .split("T")[0];
  }, [defaultStartDate]);

  const createMutation = useCreateWorkPackageScheduleBaseline({
    onSuccess: (data) => {
      form.resetFields();
      onSuccess?.(data);
      onClose();
    },
  });

  const updateMutation = useUpdateWorkPackageScheduleBaseline({
    onSuccess: (data) => {
      form.resetFields();
      onSuccess?.(data);
      onClose();
    },
  });

  useEffect(() => {
    if (visible) {
      if (baseline) {
        const fmt = (d: string) => (d ? d.split("T")[0] : defaultStartDate);
        form.setFieldsValue({
          name: baseline.name,
          start_date: fmt(baseline.start_date),
          end_date: fmt(baseline.end_date),
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
  }, [visible, baseline, form, defaultStartDate, defaultEndDate]);

  const handleSubmit = async () => {
    try {
      const values = await form.validateFields();
      if (isEdit && baseline) {
        await updateMutation.mutateAsync({
          workPackageId,
          baselineId: baseline.schedule_baseline_id,
          data: values,
        });
      } else {
        await createMutation.mutateAsync({
          workPackageId,
          ...values,
        });
      }
    } catch (error) {
      console.error("Form submission error:", error);
    }
  };

  const progressionType =
    Form.useWatch("progression_type", form) || "LINEAR";
  const startDate =
    Form.useWatch("start_date", form) || defaultStartDate;
  const endDate =
    Form.useWatch("end_date", form) || defaultEndDate;

  return (
    <Modal
      title={isEdit ? "Edit Schedule Baseline" : "Create Schedule Baseline"}
      open={visible}
      onCancel={onClose}
      footer={null}
      width={700}
      destroyOnHidden
    >
      <Form layout="vertical" form={form} onFinish={handleSubmit}>
        <Form.Item
          label="Baseline Name"
          name="name"
          rules={[{ required: true, message: "Please enter a name" }]}
        >
          <Input placeholder="e.g., Q1 2026 Baseline" />
        </Form.Item>

        <Space.Compact style={{ width: "100%", marginBottom: token.marginMD }}>
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
          rules={[
            { required: true, message: "Please select a progression type" },
          ]}
          tooltip="The pattern of progress over time for Planned Value calculations"
        >
          <Select placeholder="Select progression type">
            {PROGRESSION_TYPES.map((type) => (
              <Select.Option key={type.value} value={type.value}>
                <div>
                  <div style={{ fontWeight: 500 }}>{type.label}</div>
                  <div
                    style={{
                      fontSize: 12,
                      color: token.colorTextTertiary,
                    }}
                  >
                    {type.description}
                  </div>
                </div>
              </Select.Option>
            ))}
          </Select>
        </Form.Item>

        <Form.Item label="Description" name="description">
          <TextArea
            rows={3}
            placeholder="Optional description of this baseline..."
          />
        </Form.Item>

        <Card
          title={
            <Space>
              <span>Progression Preview</span>
              <Text type="secondary" style={{ fontSize: 12 }}>
                (
                {PROGRESSION_TYPES.find((t) => t.value === progressionType)
                  ?.label}
                )
              </Text>
            </Space>
          }
          size="small"
          style={{ marginBottom: token.marginMD }}
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
          style={{ marginBottom: token.marginMD }}
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
