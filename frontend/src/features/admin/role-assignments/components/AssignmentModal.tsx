import { useEffect } from "react";
import { Modal, Form, Select, message } from "antd";
import { useUsers } from "@/features/users/api/useUsers";
import { useRBACRoles } from "@/features/admin/rbac/hooks/useRBAC";
import {
  useCreateRoleAssignment,
  useUpdateRoleAssignment,
} from "@/features/admin/role-assignments/hooks/useRoleAssignments";
import { apiClient } from "@/api/client";
import { useQuery } from "@tanstack/react-query";
import { queryKeys } from "@/api/queryKeys";
import type {
  UserRoleAssignmentRead,
  ScopeType,
} from "@/api/types/roleAssignment";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface AssignmentModalProps {
  open: boolean;
  onClose: () => void;
  assignment?: UserRoleAssignmentRead;
}

interface ProjectOption {
  project_id: string;
  name: string;
  code: string;
}

interface ChangeOrderOption {
  change_order_id: string;
  code: string;
  title: string;
}

// ---------------------------------------------------------------------------
// Lightweight hooks for scope entity dropdowns
// ---------------------------------------------------------------------------

function useScopeProjects(enabled: boolean) {
  return useQuery<ProjectOption[]>({
    queryKey: queryKeys.projects.list({}),
    queryFn: async () => {
      const { data } = await apiClient.get("/api/v1/projects", {
        params: { per_page: 200 },
      });
      // API returns paginated { items: [...] }
      const items = data?.items ?? data;
      return (Array.isArray(items) ? items : []).map(
        (p: { project_id: string; name: string; code: string }) => ({
          project_id: p.project_id,
          name: p.name,
          code: p.code,
        }),
      );
    },
    enabled,
  });
}

function useScopeChangeOrders(enabled: boolean) {
  return useQuery<ChangeOrderOption[]>({
    queryKey: queryKeys.changeOrders.lists(),
    queryFn: async () => {
      const { data } = await apiClient.get("/api/v1/change-orders", {
        params: { per_page: 200, branch: "main" },
      });
      const items = data?.items ?? data;
      return (Array.isArray(items) ? items : []).map(
        (co: { change_order_id: string; code: string; title: string }) => ({
          change_order_id: co.change_order_id,
          code: co.code,
          title: co.title,
        }),
      );
    },
    enabled,
  });
}

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const SCOPE_TYPE_OPTIONS: { value: ScopeType; label: string }[] = [
  { value: "global", label: "Global" },
  { value: "project", label: "Project" },
  { value: "change_order", label: "Change Order" },
];

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export const AssignmentModal = ({
  open,
  onClose,
  assignment,
}: AssignmentModalProps) => {
  const [form] = Form.useForm();
  const [messageApi, contextHolder] = message.useMessage();
  const isEdit = !!assignment;

  // External data
  const { data: users } = useUsers();
  const { data: roles } = useRBACRoles();

  // Watch scope_type to conditionally show scope entity selector
  const scopeType = Form.useWatch("scope_type", form) as ScopeType | undefined;
  const needsScopeEntity =
    scopeType === "project" || scopeType === "change_order";

  const { data: projects } = useScopeProjects(scopeType === "project");
  const { data: changeOrders } = useScopeChangeOrders(
    scopeType === "change_order",
  );

  // Mutations
  const createMutation = useCreateRoleAssignment();
  const updateMutation = useUpdateRoleAssignment();

  // Reset / populate form when modal opens
  useEffect(() => {
    if (!open) return;
    if (assignment) {
      form.setFieldsValue({
        user_id: assignment.user_id,
        role_id: assignment.role_id,
        scope_type: assignment.scope_type as ScopeType,
        scope_id: assignment.scope_id,
      });
    } else {
      form.resetFields();
    }
  }, [open, assignment, form]);

  // Clear scope_id when scope_type changes
  const handleScopeTypeChange = () => {
    form.setFieldValue("scope_id", undefined);
  };

  const handleSubmit = async () => {
    try {
      const values = await form.validateFields();

      if (isEdit) {
        await updateMutation.mutateAsync({
          id: assignment.id,
          role_id: values.role_id,
        });
        messageApi.success("Role assignment updated");
      } else {
        const payload: Record<string, unknown> = {
          user_id: values.user_id,
          role_id: values.role_id,
          scope_type: values.scope_type,
        };
        // Only include scope_id for non-global scopes
        if (values.scope_type !== "global") {
          payload.scope_id = values.scope_id;
        }
        await createMutation.mutateAsync(payload as never);
        messageApi.success("Role assignment created");
      }
      onClose();
    } catch (error) {
      // Form validation errors are handled silently;
      // mutation errors are displayed here.
      if (error && typeof error === "object" && "message" in error) {
        messageApi.error((error as { message: string }).message);
      }
    }
  };

  const confirmLoading = createMutation.isPending || updateMutation.isPending;

  return (
    <>
      {contextHolder}
      <Modal
        title={isEdit ? "Edit Role Assignment" : "Create Role Assignment"}
        open={open}
        onCancel={onClose}
        onOk={handleSubmit}
        okText={isEdit ? "Save" : "Create"}
        confirmLoading={confirmLoading}
        destroyOnHidden
      >
        <Form form={form} layout="vertical" name="assignment_form">
          <Form.Item
            name="user_id"
            label="User"
            rules={[{ required: true, message: "Please select a user" }]}
          >
            <Select
              showSearch
              placeholder="Search users..."
              optionFilterProp="label"
              disabled={isEdit}
            >
              {(users ?? []).map((u) => (
                <Select.Option
                  key={u.user_id}
                  value={u.user_id}
                  label={u.full_name}
                >
                  {u.full_name} ({u.email})
                </Select.Option>
              ))}
            </Select>
          </Form.Item>

          <Form.Item
            name="role_id"
            label="Role"
            rules={[{ required: true, message: "Please select a role" }]}
          >
            <Select placeholder="Select a role" optionFilterProp="label">
              {(roles ?? []).map((r) => (
                <Select.Option key={r.id} value={r.id} label={r.name}>
                  {r.name}
                </Select.Option>
              ))}
            </Select>
          </Form.Item>

          <Form.Item
            name="scope_type"
            label="Scope Type"
            initialValue="global"
            rules={[{ required: true, message: "Please select a scope type" }]}
          >
            <Select
              options={SCOPE_TYPE_OPTIONS}
              placeholder="Select scope type"
              disabled={isEdit}
              onChange={handleScopeTypeChange}
            />
          </Form.Item>

          {needsScopeEntity && (
            <Form.Item
              name="scope_id"
              label={
                scopeType === "project" ? "Project" : "Change Order"
              }
              rules={[{ required: true, message: "Please select an entity" }]}
            >
              {scopeType === "project" ? (
                <Select
                  showSearch
                  placeholder="Search projects..."
                  optionFilterProp="label"
                >
                  {(projects ?? []).map((p) => (
                    <Select.Option
                      key={p.project_id}
                      value={p.project_id}
                      label={p.name}
                    >
                      {p.name} ({p.code})
                    </Select.Option>
                  ))}
                </Select>
              ) : (
                <Select
                  showSearch
                  placeholder="Search change orders..."
                  optionFilterProp="label"
                >
                  {(changeOrders ?? []).map((co) => (
                    <Select.Option
                      key={co.change_order_id}
                      value={co.change_order_id}
                      label={`${co.code} - ${co.title}`}
                    >
                      {co.code} &mdash; {co.title}
                    </Select.Option>
                  ))}
                </Select>
              )}
            </Form.Item>
          )}
        </Form>
      </Modal>
    </>
  );
};
