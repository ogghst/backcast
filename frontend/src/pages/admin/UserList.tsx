import { App, Button, Space, Tag } from "antd";
import {
  DeleteOutlined,
  EditOutlined,
  PlusOutlined,
  HistoryOutlined,
} from "@ant-design/icons";
import { useState } from "react";
import { CreateUserPayload, UpdateUserPayload, User } from "@/types/user";
import { UserModal } from "@/features/users/components/UserModal";
import type { ColumnType } from "antd/es/table";
import { StandardTable } from "@/components/common/StandardTable";
import { useTableParams } from "@/hooks/useTableParams";
import { createResourceHooks } from "@/hooks/useCrud";
import { UserService } from "@/features/users/api/userService";
import { UsersService } from "@/api/generated";
import { VersionHistoryDrawer } from "@/components/common/VersionHistory";
import { useEntityHistory } from "@/hooks/useEntityHistory";
import { Can } from "@/components/auth/Can";

// Create hooks instance
// We use the generated service directly, but mapping parameters might be needed if signatures differ.
// Implementation Plan said: "Reduces api/userService.ts ... to near-zero lines"
// So we should ideally pass UsersService methods directly if they match.
// UsersService.getUsers(skip, limit) -> hook expects (filters) => Promise<T[]>
// We need a small adapter here or in the hook factory usage.

const userApi = {
  getUsers: async (params?: {
    pagination?: { current?: number; pageSize?: number };
  }) => {
    // Adapt filters/pagination to backend skip/limit
    // params comes from tableParams (pagination.current, pageSize)
    const current = params?.pagination?.current || 1;
    const pageSize = params?.pagination?.pageSize || 10;
    const skip = (current - 1) * pageSize;
    // Search/Filters support can be added here
    const res = await UsersService.getUsers(skip, pageSize);
    // Handle paginated response wrapper
    // Backend returns { items: [], total: ... } or similar?
    // UserService.ts (old) said: "if (response && ... 'items' in response)"
    return Array.isArray(res) ? res : (res as { items: User[] }).items;
  },
  getUser: (id: string) => UsersService.getUser(id) as Promise<User>,
  createUser: (data: CreateUserPayload) =>
    UsersService.createUser(data) as Promise<User>,
  updateUser: (id: string, data: UpdateUserPayload) =>
    UsersService.updateUser(id, data) as Promise<User>,
  deleteUser: (id: string) => UsersService.deleteUser(id),
};

const { useList, useCreate, useUpdate, useDelete } = createResourceHooks<
  User,
  CreateUserPayload,
  UpdateUserPayload
>("users", userApi);

export const UserList = () => {
  const { tableParams, handleTableChange } = useTableParams<User>();
  const { data: users, isLoading, refetch } = useList(tableParams);

  const [modalOpen, setModalOpen] = useState(false);
  const [historyOpen, setHistoryOpen] = useState(false);
  const [selectedUser, setSelectedUser] = useState<User | null>(null);

  // Fetch version history for selected user when drawer opens
  const { data: historyVersions, isLoading: historyLoading } = useEntityHistory(
    {
      resource: "users",
      entityId: selectedUser?.user_id,
      fetchFn: UserService.getUserHistory,
      enabled: historyOpen,
    },
  );

  const { mutateAsync: createUser } = useCreate({
    onSuccess: () => {
      refetch();
      setModalOpen(false);
    },
  });
  const { mutateAsync: updateUser } = useUpdate({
    onSuccess: () => {
      refetch();
      setModalOpen(false);
      // Invalidate history cache for updated user (handled by React Query)
    },
  });
  const { mutate: deleteUser } = useDelete({ onSuccess: () => refetch() });

  const { modal } = App.useApp();

  const handleDelete = (id: string) => {
    modal.confirm({
      title: "Are you sure you want to delete this user?",
      content: "This action cannot be undone.",
      okText: "Yes, Delete",
      okType: "danger",
      onOk: () => deleteUser(id),
    });
  };

  const columns: ColumnType<User>[] = [
    {
      title: "Full Name",
      dataIndex: "full_name",
      key: "full_name",
      sorter: true,
    },
    {
      title: "Email",
      dataIndex: "email",
      key: "email",
    },
    {
      title: "Role",
      dataIndex: "role",
      key: "role",
      render: (role: string) => <Tag color="blue">{role.toUpperCase()}</Tag>,
    },
    {
      title: "Department",
      dataIndex: "department",
      key: "department",
    },
    {
      title: "Status",
      dataIndex: "is_active",
      key: "is_active",
      render: (isActive: boolean) => (
        <Tag color={isActive ? "green" : "red"}>
          {isActive ? "Active" : "Inactive"}
        </Tag>
      ),
    },
    {
      title: "Actions",
      key: "actions",
      render: (_, record) => (
        <Space>
          <Button
            icon={<HistoryOutlined />}
            onClick={() => {
              setSelectedUser(record);
              setHistoryOpen(true);
            }}
            title="View History"
          />
          <Can permission="user-update">
            <Button
              icon={<EditOutlined />}
              onClick={() => {
                setSelectedUser(record);
                setModalOpen(true);
              }}
              title="Edit User"
            />
          </Can>
          <Can permission="user-delete">
            <Button
              danger
              icon={<DeleteOutlined />}
              onClick={() => handleDelete(record.user_id)}
              title="Delete User"
            />
          </Can>
        </Space>
      ),
    },
  ];

  return (
    <div>
      <StandardTable<User>
        tableParams={tableParams}
        onChange={handleTableChange}
        loading={isLoading}
        dataSource={users || []}
        columns={columns}
        rowKey="id"
        toolbar={
          <div
            style={{
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
            }}
          >
            <div style={{ fontSize: "16px", fontWeight: "bold" }}>
              User Management
            </div>
            <Can permission="user-create">
              <Button
                type="primary"
                icon={<PlusOutlined />}
                onClick={() => {
                  setSelectedUser(null);
                  setModalOpen(true);
                }}
              >
                Add User
              </Button>
            </Can>
          </div>
        }
      />

      <UserModal
        open={modalOpen}
        onCancel={() => setModalOpen(false)}
        onOk={async (values) => {
          if (selectedUser) {
            await updateUser({ id: selectedUser.user_id, data: values });
          } else {
            await createUser(values as CreateUserPayload);
          }
          // Don't close here - let mutation onSuccess handle it
        }}
        confirmLoading={isLoading}
        initialValues={selectedUser}
      />

      <VersionHistoryDrawer
        open={historyOpen}
        onClose={() => setHistoryOpen(false)}
        versions={(historyVersions || []).map((version, idx, arr) => ({
          id: `v${arr.length - idx}`,
          valid_from: version.valid_time?.[0] || new Date().toISOString(),
          transaction_time:
            version.transaction_time?.[0] || new Date().toISOString(),
          changed_by: "System", // TODO: Track actual actor when backend supports it
          changes: idx === 0 ? { created: "initial" } : { updated: "changed" },
        }))}
        entityName={`User: ${selectedUser?.full_name || ""}`}
        isLoading={historyLoading}
      />
    </div>
  );
};
