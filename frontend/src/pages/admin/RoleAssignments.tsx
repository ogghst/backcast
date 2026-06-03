/**
 * Role Assignments Admin Page
 *
 * Paginated table view for managing user-role assignments with
 * filters by user, role, and scope type.
 */

import { App, Button, Card, Select, Space, Tag, theme } from "antd";
import { useSearchParams } from "react-router-dom";
import { DeleteOutlined, EditOutlined, PlusOutlined } from "@ant-design/icons";
import { useCallback, useMemo, useState } from "react";
import type { ColumnType } from "antd/es/table";
import dayjs from "dayjs";

import { StandardTable } from "@/components/common/StandardTable";
import { useTableParams } from "@/hooks/useTableParams";
import { Can } from "@/components/auth/Can";
import {
  useRoleAssignments,
  useDeleteRoleAssignment,
} from "@/features/admin/role-assignments/hooks/useRoleAssignments";
import { AssignmentModal } from "@/features/admin/role-assignments/components/AssignmentModal";
import { useRBACRoles } from "@/features/admin/rbac/hooks/useRBAC";
import { useUsers } from "@/features/users/api/useUsers";
import type { UserRoleAssignmentRead, ScopeType } from "@/api/types/roleAssignment";

// ---------------------------------------------------------------------------
// Scope type configuration
// ---------------------------------------------------------------------------

const SCOPE_TYPE_CONFIG: Record<
  ScopeType,
  { label: string; color: string }
> = {
  global: { label: "Global", color: "blue" },
  project: { label: "Project", color: "green" },
  change_order: { label: "Change Order", color: "orange" },
};

// ---------------------------------------------------------------------------
// Main Page Component
// ---------------------------------------------------------------------------

export const RoleAssignments: React.FC = () => {
  const { token } = theme.useToken();
  const { modal } = App.useApp();
  const { tableParams, handleTableChange } =
    useTableParams<UserRoleAssignmentRead>();

  const [searchParams] = useSearchParams();

  // Filter state (initialize userId from URL param)
  const [userFilter, setUserFilter] = useState<string | undefined>(
    searchParams.get("userId") ?? undefined,
  );
  const [scopeTypeFilter, setScopeTypeFilter] = useState<
    ScopeType | undefined
  >();
  const [roleFilter, setRoleFilter] = useState<string | undefined>();

  // Modal placeholder state (AssignmentModal will be integrated in FE-006)
  const [modalOpen, setModalOpen] = useState(false);
  const [selectedAssignment, setSelectedAssignment] =
    useState<UserRoleAssignmentRead | null>(null);

  // Build query params from filters
  const queryParams = useMemo(
    () => ({
      userId: userFilter,
      scopeType: scopeTypeFilter,
      roleId: roleFilter,
    }),
    [userFilter, scopeTypeFilter, roleFilter],
  );

  // Data queries
  const { data: assignments, isLoading } =
    useRoleAssignments(queryParams);
  const { data: roles } = useRBACRoles();

  // Fetch users for the filter dropdown
  const { data: usersData, isLoading: usersLoading } = useUsers(1000);

  // Mutations
  const { mutate: deleteAssignment } = useDeleteRoleAssignment();

  // Clear all filters
  const clearFilters = useCallback(() => {
    setUserFilter(undefined);
    setScopeTypeFilter(undefined);
    setRoleFilter(undefined);
  }, []);

  // Handlers
  const handleDelete = (record: UserRoleAssignmentRead) => {
    modal.confirm({
      title: "Are you sure you want to delete this role assignment?",
      content: `Remove "${record.role_name || "Unknown Role"}" from "${record.user_name || "Unknown User"}".`,
      okText: "Yes, Delete",
      okType: "danger",
      onOk: () => deleteAssignment(record.id),
    });
  };

  const handleCreate = () => {
    setSelectedAssignment(null);
    setModalOpen(true);
  };

  const handleEdit = (record: UserRoleAssignmentRead) => {
    setSelectedAssignment(record);
    setModalOpen(true);
  };

  // Whether any filter is active
  const hasActiveFilters = userFilter || scopeTypeFilter || roleFilter;

  // Role options for the filter dropdown
  const roleOptions = useMemo(
    () =>
      (roles || []).map((r) => ({
        value: r.id,
        label: r.name,
      })),
    [roles],
  );

  // User options for the filter dropdown
  const userOptions = useMemo(
    () =>
      (usersData || []).map((u) => ({
        value: u.user_id,
        label: u.full_name || u.email,
      })),
    [usersData],
  );

  // ---- Columns ----
  const columns: ColumnType<UserRoleAssignmentRead>[] = [
    {
      title: "User Name",
      dataIndex: "user_name",
      key: "user_name",
      sorter: (a, b) =>
        (a.user_name || "").localeCompare(b.user_name || ""),
      render: (name: string) => name || "—",
    },
    {
      title: "Role",
      dataIndex: "role_name",
      key: "role_name",
      sorter: (a, b) =>
        (a.role_name || "").localeCompare(b.role_name || ""),
      render: (name: string) => (
        <Tag color="blue">{name || "Unknown"}</Tag>
      ),
    },
    {
      title: "Scope Type",
      dataIndex: "scope_type",
      key: "scope_type",
      sorter: (a, b) => a.scope_type.localeCompare(b.scope_type),
      render: (scopeType: ScopeType) => {
        const config = SCOPE_TYPE_CONFIG[scopeType];
        return (
          <Tag color={config.color}>{config.label}</Tag>
        );
      },
    },
    {
      title: "Scope Entity",
      dataIndex: "scope_id",
      key: "scope_id",
      render: (scopeId: string | null) => scopeId || "—",
    },
    {
      title: "Granted By",
      dataIndex: "granted_by_name",
      key: "granted_by_name",
      render: (name: string | null) => name || "—",
    },
    {
      title: "Granted At",
      dataIndex: "granted_at",
      key: "granted_at",
      sorter: (a, b) =>
        dayjs(a.granted_at).unix() - dayjs(b.granted_at).unix(),
      render: (date: string) => date ? dayjs(date).format("YYYY-MM-DD HH:mm") : "—",
    },
    {
      title: "Actions",
      key: "actions",
      width: 140,
      render: (_, record) => (
        <Space>
          <Can permission="role-assignment-update">
            <Button
              icon={<EditOutlined />}
              onClick={() => handleEdit(record)}
              title="Edit Assignment"
              size="small"
            />
          </Can>
          <Can permission="role-assignment-delete">
            <Button
              danger
              icon={<DeleteOutlined />}
              onClick={() => handleDelete(record)}
              title="Delete Assignment"
              size="small"
            />
          </Can>
        </Space>
      ),
    },
  ];

  return (
    <>
      <Card
        title={<span style={{ fontSize: token.fontSizeLG, fontWeight: "bold" }}>Role Assignments</span>}
        extra={
          <Can permission="role-assignment-create">
            <Button
              type="primary"
              icon={<PlusOutlined />}
              onClick={handleCreate}
            >
              Add Assignment
            </Button>
          </Can>
        }
      >
        {/* Filters row */}
        <Space style={{ marginBottom: token.marginMD }} wrap>
          <Select
            placeholder="Filter by User"
            value={userFilter}
            onChange={setUserFilter}
            options={userOptions}
            allowClear
            showSearch
            optionFilterProp="label"
            loading={usersLoading}
            style={{ minWidth: 180 }}
            size="small"
          />
          <Select
            placeholder="Filter by Scope"
            value={scopeTypeFilter}
            onChange={setScopeTypeFilter}
            options={[
              { value: "global", label: "Global" },
              { value: "project", label: "Project" },
              { value: "change_order", label: "Change Order" },
            ]}
            allowClear
            style={{ minWidth: 140 }}
            size="small"
          />
          <Select
            placeholder="Filter by Role"
            value={roleFilter}
            onChange={setRoleFilter}
            options={roleOptions}
            allowClear
            showSearch
            optionFilterProp="label"
            style={{ minWidth: 160 }}
            size="small"
          />
          {hasActiveFilters && (
            <Button size="small" onClick={clearFilters}>
              Clear Filters
            </Button>
          )}
        </Space>

        <StandardTable<UserRoleAssignmentRead>
          tableParams={{
            ...tableParams,
            pagination: {
              ...tableParams.pagination,
              total: (assignments || []).length,
            },
          }}
          onChange={handleTableChange}
          loading={isLoading}
          dataSource={assignments || []}
          columns={columns}
          rowKey="id"
        />
      </Card>

      <AssignmentModal
        open={modalOpen}
        onClose={() => setModalOpen(false)}
        assignment={selectedAssignment ?? undefined}
      />
    </>
  );
};
