import { useEffect, useState, useCallback } from "react";
import { Modal, Form, Input, Select, Switch, Tag, App } from "antd";
import { User, CreateUserPayload, UpdateUserPayload } from "@/types/user";
import { useRBACRoles } from "@/features/admin/rbac/hooks/useRBAC";
import {
  useRoleAssignments,
  useCreateRoleAssignment,
  useUpdateRoleAssignment,
  useDeleteRoleAssignment,
} from "@/features/admin/role-assignments/hooks/useRoleAssignments";

interface UserModalProps {
  open: boolean;
  onCancel: () => void;
  /** Called with form values. Should return the created/updated User. */
  onOk: (
    values: CreateUserPayload | UpdateUserPayload,
  ) => Promise<User | void>;
  confirmLoading: boolean;
  initialValues?: User | null;
}

export const UserModal = ({
  open,
  onCancel,
  onOk,
  confirmLoading,
  initialValues,
}: UserModalProps) => {
  const [form] = Form.useForm();
  const { message } = App.useApp();
  const isEdit = !!initialValues;

  // Tracks user's explicit role selection. `destroyOnHidden` remounts the component,
  // so this resets to [] each time the modal opens.
  const [selectedRoleIds, setSelectedRoleIds] = useState<string[]>([]);

  // RBAC roles for the dropdown
  const { data: rbacRoles } = useRBACRoles();

  // Edit mode: fetch current GLOBAL assignments
  const { data: globalAssignments } = useRoleAssignments(
    isEdit && initialValues
      ? { userId: initialValues.user_id, scopeType: "global" }
      : undefined,
  );

  // Assignment mutations
  const createAssignment = useCreateRoleAssignment();
  const updateAssignment = useUpdateRoleAssignment();
  const deleteAssignment = useDeleteRoleAssignment();

  // Derive role options from RBAC
  const roleOptions = (rbacRoles || []).map((role) => ({
    value: role.id,
    label: role.name,
  }));

  // Derive the initial role from the first GLOBAL assignment (for edit mode)
  const initialRoleId =
    isEdit && globalAssignments && globalAssignments.length > 0
      ? globalAssignments[0].role_id
      : undefined;

  // Effective role: user's selection takes priority, fall back to initial from data
  // For edit mode with single/no assignment, this resolves to a single role ID
  const effectiveRoleId = selectedRoleIds.length > 0 ? selectedRoleIds[0] : initialRoleId;

  // Reset form when modal opens
  useEffect(() => {
    if (open) {
      if (initialValues) {
        form.setFieldsValue(initialValues);
      } else {
        form.resetFields();
      }
    }
  }, [open, initialValues, form]);

  const handleSubmit = useCallback(async () => {
    try {
      const values = await form.validateFields();

      // Remove the legacy 'role' field — we manage roles via GLOBAL assignments
      const { role: _role, ...userValues } = values as CreateUserPayload &
        UpdateUserPayload & { role?: string };
      void _role;

      // Submit user data (without legacy role field)
      const result = await onOk(userValues);

      // Manage GLOBAL role assignment
      if (isEdit && initialValues) {
        // --- Edit mode ---
        const existing = globalAssignments || [];

        if (effectiveRoleId) {
          if (existing.length === 0) {
            // No existing assignment — create one
            await createAssignment.mutateAsync({
              user_id: initialValues.user_id,
              role_id: effectiveRoleId,
              scope_type: "global",
              scope_id: null,
            });
          } else if (existing[0].role_id !== effectiveRoleId) {
            // Assignment exists but role changed — update it
            await updateAssignment.mutateAsync({
              id: existing[0].id,
              role_id: effectiveRoleId,
            });
          }
        }
        // Note: removing the last assignment is allowed (effectiveRoleId === undefined)
      } else if (result && selectedRoleIds.length > 0) {
        // --- Create mode ---
        // After user creation, create one GLOBAL assignment per selected role
        const userId = result.user_id || result.id;
        for (const roleId of selectedRoleIds) {
          try {
            await createAssignment.mutateAsync({
              user_id: userId,
              role_id: roleId,
              scope_type: "global",
              scope_id: null,
            });
          } catch {
            // User is already created — show warning but don't fail the whole operation
            message.warning(
              "User created but some role assignments failed. You can assign roles later.",
            );
            break;
          }
        }
      }
    } catch (error) {
      // Validation failed or onOk threw — don't close modal
      console.error("Form submission error:", error);
    }
  }, [
    form,
    onOk,
    isEdit,
    initialValues,
    globalAssignments,
    effectiveRoleId,
    selectedRoleIds,
    createAssignment,
    updateAssignment,
    message,
  ]);

  const handleRemoveAssignment = useCallback(
    (assignmentId: string) => {
      deleteAssignment.mutate(assignmentId);
      // Reset local selection if the removed assignment's role was selected
      setSelectedRoleIds([]);
    },
    [deleteAssignment],
  );

  // Compute whether we're in a submitting state
  const isSubmitting =
    confirmLoading ||
    createAssignment.isPending ||
    updateAssignment.isPending ||
    deleteAssignment.isPending;

  // Edit mode: show multiple GLOBAL assignments as tags if present
  const renderEditRoleField = () => {
    const assignments = globalAssignments || [];

    if (assignments.length <= 1) {
      // Single or no assignment — show dropdown
      return (
        <Form.Item label="Global Role" required data-testid="global-role-field">
          <Select
            placeholder="Select a role"
            value={effectiveRoleId}
            onChange={(value) => setSelectedRoleIds(value ? [value] : [])}
            options={roleOptions}
            allowClear
            aria-label="Global Role"
          />
        </Form.Item>
      );
    }

    // Multiple GLOBAL assignments — show tags with remove
    return (
      <Form.Item label="Global Roles">
        <div style={{ display: "flex", flexWrap: "wrap", gap: 4 }}>
          {assignments.map((assignment) => (
            <Tag
              key={assignment.id}
              closable
              onClose={() => handleRemoveAssignment(assignment.id)}
              color={assignment.role_id === effectiveRoleId ? "blue" : undefined}
            >
              {assignment.role_name || assignment.role_id}
            </Tag>
          ))}
        </div>
      </Form.Item>
    );
  };

  return (
    <Modal
      title={isEdit ? "Edit User" : "Create User"}
      open={open}
      onCancel={onCancel}
      onOk={handleSubmit}
      okText={isEdit ? "Save" : "Create"}
      okButtonProps={{ "data-testid": "submit-user-btn" }}
      confirmLoading={isSubmitting}
      destroyOnHidden
    >
      <Form form={form} layout="vertical" name="user_form">
        <Form.Item
          name="full_name"
          label="Full Name"
          rules={[{ required: true, message: "Please enter full name" }]}
        >
          <Input placeholder="John Doe" />
        </Form.Item>

        <Form.Item
          name="email"
          label="Email"
          rules={[
            { required: true, message: "Please enter email" },
            { type: "email", message: "Please enter a valid email" },
          ]}
        >
          <Input placeholder="john@example.com" />
        </Form.Item>

        {!isEdit && (
          <Form.Item
            name="password"
            label="Password"
            rules={[{ required: true, message: "Please enter password" }]}
          >
            <Input.Password placeholder="Password" />
          </Form.Item>
        )}

        {isEdit ? renderEditRoleField() : (
          <Form.Item label="Global Roles" required data-testid="global-role-field">
            <Select
              mode="multiple"
              placeholder="Select one or more roles"
              value={selectedRoleIds}
              onChange={setSelectedRoleIds}
              options={roleOptions}
              allowClear
              aria-label="Global Roles"
            />
          </Form.Item>
        )}

        {isEdit && (
          <Form.Item name="is_active" label="Active" valuePropName="checked">
            <Switch />
          </Form.Item>
        )}
      </Form>
    </Modal>
  );
};
