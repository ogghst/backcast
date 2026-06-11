/**
 * Schedule Dependency Modal
 *
 * Modal for creating and editing dependency links between schedule baselines.
 * Uses Ant Design Modal + Form pattern matching the existing ScheduleBaselineModal.
 *
 * @module features/schedule-baselines/components
 */

import { useEffect } from "react";
import { Modal, Form, Select, InputNumber, Button, Space, theme, message } from "antd";
import {
  useCreateScheduleDependency,
  useUpdateScheduleDependency,
  type ScheduleDependencyRead,
  type ScheduleDependencyCreate,
  type ScheduleDependencyUpdate,
  type ScheduleOption,
  formatScheduleLabel,
} from "../api/useScheduleDependencies";

const DEPENDENCY_TYPES = [
  { value: "FS", label: "FS (Finish-Start)" },
  { value: "SS", label: "SS (Start-Start)" },
  { value: "FF", label: "FF (Finish-Finish)" },
  { value: "SF", label: "SF (Start-Finish)" },
];

interface ScheduleDependencyModalProps {
  open: boolean;
  projectId: string;
  editDependency?: ScheduleDependencyRead | null;
  schedules: ScheduleOption[];
  onClose: () => void;
}

export const ScheduleDependencyModal: React.FC<ScheduleDependencyModalProps> = ({
  open,
  projectId,
  editDependency,
  schedules,
  onClose,
}) => {
  const { token } = theme.useToken();
  const [form] = Form.useForm();
  const isEdit = !!editDependency;

  const createMutation = useCreateScheduleDependency();
  const updateMutation = useUpdateScheduleDependency();

  useEffect(() => {
    if (open) {
      if (editDependency) {
        form.setFieldsValue({
          predecessor_id: editDependency.predecessor_id,
          successor_id: editDependency.successor_id,
          dependency_type: editDependency.dependency_type,
          lag_days: editDependency.lag_days,
        });
      } else {
        form.resetFields();
        form.setFieldsValue({
          dependency_type: "FS",
          lag_days: 0,
        });
      }
    }
  }, [open, editDependency, form]);

  const handleSubmit = async () => {
    try {
      const values = await form.validateFields();

      if (isEdit && editDependency) {
        const updateData: ScheduleDependencyUpdate & { schedule_dependency_id: string } = {
          schedule_dependency_id: editDependency.schedule_dependency_id,
          dependency_type: values.dependency_type,
          lag_days: values.lag_days,
        };
        await updateMutation.mutateAsync(updateData);
      } else {
        const createData: ScheduleDependencyCreate = {
          project_id: projectId,
          predecessor_id: values.predecessor_id,
          successor_id: values.successor_id,
          dependency_type: values.dependency_type,
          lag_days: values.lag_days,
        };
        await createMutation.mutateAsync(createData);
      }
      form.resetFields();
      onClose();
    } catch (error) {
      // Form validation errors are displayed by Ant Design automatically.
      // Only surface API/mutation errors to the user.
      if (error && typeof error === "object" && "errorFields" in error) return;
      message.error("Failed to save dependency. Please try again.");
    }
  };

  const scheduleOptions = schedules.map((s) => ({
    value: s.schedule_baseline_id,
    label: formatScheduleLabel(s),
  }));

  return (
    <Modal
      title={isEdit ? "Edit Dependency" : "Add Dependency"}
      open={open}
      onCancel={onClose}
      footer={null}
      width={520}
      destroyOnHidden
    >
      <Form
        layout="vertical"
        form={form}
        onFinish={handleSubmit}
      >
        <Form.Item
          label="Predecessor"
          name="predecessor_id"
          rules={[{ required: true, message: "Please select a predecessor" }]}
        >
          <Select
            showSearch
            placeholder="Select predecessor schedule"
            optionFilterProp="label"
            options={scheduleOptions}
            disabled={isEdit}
          />
        </Form.Item>

        <Form.Item
          label="Successor"
          name="successor_id"
          rules={[{ required: true, message: "Please select a successor" }]}
        >
          <Select
            showSearch
            placeholder="Select successor schedule"
            optionFilterProp="label"
            options={scheduleOptions}
            disabled={isEdit}
          />
        </Form.Item>

        <Form.Item
          label="Dependency Type"
          name="dependency_type"
          rules={[{ required: true, message: "Please select a dependency type" }]}
        >
          <Select options={DEPENDENCY_TYPES} placeholder="Select type" />
        </Form.Item>

        <Form.Item
          label="Lag Days"
          name="lag_days"
          tooltip="Positive = delay, negative = lead"
        >
          <InputNumber style={{ width: "100%" }} min={-365} max={365} />
        </Form.Item>

        <div style={{ textAlign: "right", marginTop: token.marginSM }}>
          <Space>
            <Button onClick={onClose}>Cancel</Button>
            <Button
              type="primary"
              htmlType="submit"
              loading={createMutation.isPending || updateMutation.isPending}
            >
              {isEdit ? "Update Dependency" : "Add Dependency"}
            </Button>
          </Space>
        </div>
      </Form>
    </Modal>
  );
};
