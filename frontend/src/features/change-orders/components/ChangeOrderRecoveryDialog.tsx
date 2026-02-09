import { useMemo } from "react";
import { Modal, Form, Select, Input, message } from "antd";
import { ToolOutlined } from "@ant-design/icons";
import { useQuery } from "@tanstack/react-query";
import type { ChangeOrderPublic } from "@/api/generated";
import { OpenAPI } from "@/api/generated/core/OpenAPI";
import { request as __request } from "@/api/generated/core/request";
import { Can } from "@/components/auth/Can";
import { useRecoverChangeOrder, type ChangeOrderRecoveryRequest } from "../api/useRecoverChangeOrder";
import { queryKeys } from "@/api/queryKeys";

const { TextArea } = Input;

/**
 * Props for ChangeOrderRecoveryDialog component.
 */
export interface ChangeOrderRecoveryDialogProps {
  /** The change order to recover */
  changeOrder: ChangeOrderPublic;
  /** Whether the dialog is visible */
  visible: boolean;
  /** Callback when dialog is closed */
  onClose: () => void;
  /** Callback when recovery succeeds */
  onSuccess: () => void;
}

/**
 * Simplified User type for the approver selector.
 * Uses User.id (not User.user_id) as required by backend.
 */
interface UserPublic {
  id: string;
  user_id: string;
  email: string;
  full_name: string;
  role: string;
  is_active: boolean;
}

/**
 * ChangeOrderRecoveryDialog - Modal dialog for admins to recover stuck change orders.
 *
 * Context: Admin-only component to recover stuck workflows when impact analysis
 * fails or the change order gets stuck in an intermediate state. Allows manual
 * override of impact level and approver assignment.
 *
 * Requires change-order-recover permission (admin only).
 *
 * Features:
 * - Impact level selector (LOW/MEDIUM/HIGH/CRITICAL) - required
 * - Approver selector - required (fetches active users from API)
 * - Recovery reason textarea - required, 10-500 chars
 * - Form validation before submission
 * - Success/error toast notifications
 * - Loading state during submission
 *
 * @example
 * ```tsx
 * <ChangeOrderRecoveryDialog
 *   changeOrder={changeOrder}
 *   visible={recoveryDialogVisible}
 *   onClose={() => setRecoveryDialogVisible(false)}
 *   onSuccess={() => {
 *     setRecoveryDialogVisible(false);
 *     refetch();
 *   }}
 * />
 * ```
 */
export function ChangeOrderRecoveryDialog({
  changeOrder,
  visible,
  onClose,
  onSuccess,
}: ChangeOrderRecoveryDialogProps) {
  const [form] = Form.useForm();

  // Recovery mutation
  const { mutate: recover, isPending: isRecovering } = useRecoverChangeOrder({
    onSuccess: (data) => {
      message.success(
        `Change Order ${data.code} workflow recovered successfully`,
      );
      form.resetFields();
      onSuccess();
    },
    onError: (error) => {
      // Error toast is shown in the hook
      console.error("Recovery failed:", error);
    },
  });

  // Fetch users for approver selector
  const { data: users = [], isLoading: isLoadingUsers } = useQuery({
    queryKey: queryKeys.users.list({ page: 1, per_page: 100 }),
    queryFn: async () => {
      const response = await __request(OpenAPI, {
        method: "GET",
        url: "/api/v1/users",
        query: {
          skip: 0,
          limit: 100,
        },
      });
      // Handle paginated response
      if (response && typeof response === "object" && "items" in response) {
        return (response as { items: UserPublic[] }).items;
      }
      return response as UserPublic[];
    },
    // Only fetch when dialog is visible
    enabled: visible,
  });

  // Filter active users for approver selection
  const activeUsers = useMemo(() => {
    return users.filter((u) => u.is_active);
  }, [users]);

  // Handle form submission
  const handleSubmit = async () => {
    try {
      const values = await form.validateFields();

      const recoveryData: ChangeOrderRecoveryRequest = {
        impact_level: values.impact_level,
        assigned_approver_id: values.assigned_approver_id,
        skip_impact_analysis: true,
        recovery_reason: values.recovery_reason,
      };

      recover({
        id: changeOrder.change_order_id,
        recoveryData,
      });
    } catch (error) {
      // Form validation failed - user will see validation messages
      console.log("Form validation failed:", error);
    }
  };

  // Handle dialog close
  const handleCancel = () => {
    form.resetFields();
    onClose();
  };

  return (
    <Can permission="change-order-recover">
      <Modal
        title={
          <span>
            <ToolOutlined /> Recover Change Order Workflow
          </span>
        }
        open={visible}
        onOk={handleSubmit}
        onCancel={handleCancel}
        okText="Recover Workflow"
        okButtonProps={{
          loading: isRecovering,
          danger: true,
        }}
        cancelText="Cancel"
        width={600}
        destroyOnClose
      >
        <div style={{ marginBottom: 16 }}>
          <p>
            Recovering this change order will manually set the impact level and
            assign an approver, bypassing the automated impact analysis.
          </p>
          <p>
            <strong>Change Order:</strong> {changeOrder.code} - {changeOrder.title}
          </p>
          <p>
            <strong>Current Status:</strong> {changeOrder.status}
          </p>
        </div>

        <Form
          form={form}
          layout="vertical"
          autoComplete="off"
          initialValues={{
            impact_level: undefined,
            assigned_approver_id: undefined,
            recovery_reason: "",
          }}
        >
          <Form.Item
            label="Impact Level"
            name="impact_level"
            rules={[
              { required: true, message: "Please select an impact level" },
            ]}
          >
            <Select
              placeholder="Select impact level"
              loading={isRecovering}
              disabled={isRecovering}
              options={[
                { label: "Low", value: "LOW" },
                { label: "Medium", value: "MEDIUM" },
                { label: "High", value: "HIGH" },
                { label: "Critical", value: "CRITICAL" },
              ]}
            />
          </Form.Item>

          <Form.Item
            label="Assigned Approver"
            name="assigned_approver_id"
            rules={[
              { required: true, message: "Please select an approver" },
            ]}
          >
            <Select
              placeholder="Select an approver"
              loading={isLoadingUsers || isRecovering}
              disabled={isRecovering}
              showSearch
              optionFilterProp="label"
              filterSort={(optionA, optionB) =>
                (optionA?.label ?? "")
                  .toLowerCase()
                  .localeCompare((optionB?.label ?? "").toLowerCase())
              }
              options={activeUsers.map((user) => ({
                label: `${user.full_name} (${user.email})`,
                value: user.id, // Use User.id, not User.user_id
              }))}
            />
          </Form.Item>

          <Form.Item
            label="Recovery Reason"
            name="recovery_reason"
            rules={[
              { required: true, message: "Please provide a recovery reason" },
              {
                min: 10,
                message: "Recovery reason must be at least 10 characters",
              },
              {
                max: 500,
                message: "Recovery reason must not exceed 500 characters",
              },
            ]}
          >
            <TextArea
              placeholder="Explain why this change order needs to be recovered (10-500 characters)"
              rows={4}
              disabled={isRecovering}
              maxLength={500}
              showCount
            />
          </Form.Item>
        </Form>
      </Modal>
    </Can>
  );
}
