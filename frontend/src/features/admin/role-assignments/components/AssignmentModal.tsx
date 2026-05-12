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
import { useTimeMachineParams } from "@/contexts/TimeMachineContext";
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
  const { branch, mode } = useTimeMachineParams();
  return useQuery<ProjectOption[]>({
    queryKey: queryKeys.projects.list({ branch, mode }),
    queryFn: async () => {
      const { data } = await apiClient.get("/api/v1/projects", {
        params: { per_page: 200, branch, mode },
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

function useScopeChangeOrders(enabled: boolean, projectId?: string) {
  return useQuery<ChangeOrderOption[]>({
    queryKey: queryKeys.changeOrders.list(projectId || "", { per_page: 200 }),
    queryFn: async () => {
      if (!projectId) return [];
      const { data } = await apiClient.get("/api/v1/change-orders", {
        params: { per_page: 200, project_id: projectId, branch: "main" },
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
    enabled: enabled && !!projectId,
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

  // For change_order scope, we need a project selection first
  const scopeProjectId = Form.useWatch("scope_project_id", form) as string | undefined;

  const { data: projects } = useScopeProjects(scopeType === "project" || scopeType === "change_order");
  const { data: changeOrders } = useScopeChangeOrders(
    scopeType === "change_order",
    scopeProjectId,
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
    form.setFieldValue("scope_project_id", undefined);
  };

  // Clear scope_id when scope_project_id changes (for change_order scope)
  const handleScopeProjectChange = () => {
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
      console.error("Error submitting assignment:", error);
      let errorMessage = "An error occurred";
      if (error && typeof error === "object") {
        // Check for Axios error with response data
        if ("response" in error && error.response) {
          const responseData = (error.response as { data?: { detail?: string } })?.data;
          errorMessage = responseData?.detail || ((error as unknown) as { message?: string })?.message || errorMessage;
        } else if ("message" in error) {
          errorMessage = (error as { message: string }).message;
        }
      }
      messageApi.error(errorMessage);
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

          {/* For change_order scope, first select a project */}
          {scopeType === "change_order" && (
            <Form.Item
              name="scope_project_id"
              label="Project"
              rules={[{ required: true, message: "Please select a project first" }]}
            >
              <Select
                showSearch
                placeholder="Search projects..."
                optionFilterProp="label"
                onChange={handleScopeProjectChange}
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
            </Form.Item>
          )}

          {needsScopeEntity && scopeType !== "change_order" && (
            <Form.Item
              name="scope_id"
              label="Project"
              rules={[{ required: true, message: "Please select a project" }]}
            >
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
            </Form.Item>
          )}

          {/* For change_order scope, select the change order after project */}
          {scopeType === "change_order" && (
            <Form.Item
              name="scope_id"
              label="Change Order"
              rules={[{ required: true, message: "Please select a change order" }]}
            >
              <Select
                showSearch
                placeholder="Search change orders..."
                optionFilterProp="label"
                disabled={!scopeProjectId}
                loading={scopeProjectId ? !changeOrders : false}
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
            </Form.Item>
          )}
        </Form>
      </Modal>
    </>
  );
};
