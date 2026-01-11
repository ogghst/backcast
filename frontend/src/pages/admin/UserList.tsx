import { App, Button, Input, Space, Tag } from "antd";
import {
  DeleteOutlined,
  EditOutlined,
  PlusOutlined,
  HistoryOutlined,
  SearchOutlined,
} from "@ant-design/icons";
import { useMemo, useState } from "react";
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

import type { PaginatedResponse } from "@/types/api";

// Create hooks instance
const userApi = {
  list: async (): Promise<PaginatedResponse<User>> => {
    // Fetch ALL users for client-side pagination and filtering
    // We ignore the pagination params because Ant Design will handle pagination client-side
    // This is acceptable for user management since user count is typically small (< 1000)
    const allUsers = await UsersService.getUsers(0, 100000);

    // Normalize response to PaginatedResponse
    if (Array.isArray(allUsers)) {
      return {
        items: allUsers,
        total: allUsers.length,
        page: 1,
        per_page: allUsers.length,
      };
    }

    // If backend ever returns paginated response, use it directly
    return allUsers as unknown as PaginatedResponse<User>;
  },
  detail: (id: string) => UsersService.getUser(id) as Promise<User>,
  create: (data: CreateUserPayload) =>
    UsersService.createUser(data) as Promise<User>,
  update: (id: string, data: UpdateUserPayload) =>
    UsersService.updateUser(id, data) as Promise<User>,
  delete: (id: string) => UsersService.deleteUser(id),
};

const { useList, useCreate, useUpdate, useDelete } = createResourceHooks<
  User,
  CreateUserPayload,
  UpdateUserPayload,
  PaginatedResponse<User>
>("users", userApi);

import { UserFilters } from "@/types/filters";

export const UserList = () => {
  const { tableParams, handleTableChange, handleSearch } = useTableParams<
    User,
    UserFilters
  >();
  const { data, isLoading, refetch } = useList(tableParams);
  const users = useMemo(() => data?.items || [], [data]);

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
    }
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

  const getColumnSearchProps = (dataIndex: keyof User): ColumnType<User> => ({
    filterDropdown: ({
      setSelectedKeys,
      selectedKeys,
      confirm,
      clearFilters,
    }) => (
      <div style={{ padding: 8 }}>
        <Input
          placeholder={`Search ${dataIndex}`}
          value={selectedKeys[0]}
          onChange={(e) =>
            setSelectedKeys(e.target.value ? [e.target.value] : [])
          }
          onPressEnter={() => confirm()}
          style={{ width: 188, marginBottom: 8, display: "block" }}
        />
        <Space>
          <Button
            type="primary"
            onClick={() => confirm()}
            icon={<SearchOutlined />}
            size="small"
            style={{ width: 90 }}
          >
            Search
          </Button>
          <Button
            onClick={() => clearFilters && clearFilters()}
            size="small"
            style={{ width: 90 }}
          >
            Reset
          </Button>
        </Space>
      </div>
    ),
    filterIcon: (filtered: boolean) => (
      <SearchOutlined style={{ color: filtered ? "#1890ff" : undefined }} />
    ),
    onFilter: (value, record) => {
      const fieldVal = record[dataIndex];
      return fieldVal
        ? fieldVal
            .toString()
            .toLowerCase()
            .includes((value as string).toLowerCase())
        : false;
    },
  });

  const columns: ColumnType<User>[] = [
    {
      title: "Full Name",
      dataIndex: "full_name",
      key: "full_name",
      sorter: (a, b) => a.full_name.localeCompare(b.full_name),
      ...getColumnSearchProps("full_name"),
    },
    {
      title: "Email",
      dataIndex: "email",
      key: "email",
      sorter: (a, b) => a.email.localeCompare(b.email),
      ...getColumnSearchProps("email"),
    },
    {
      title: "Role",
      dataIndex: "role",
      key: "role",
      filters: [
        { text: "Admin", value: "admin" },
        { text: "User", value: "user" },
        { text: "Viewer", value: "viewer" },
      ],
      onFilter: (value, record) => record.role === value,
      render: (role: string) => <Tag color="blue">{role.toUpperCase()}</Tag>,
    },
    {
      title: "Department",
      dataIndex: "department",
      key: "department",
      sorter: (a, b) => (a.department || "").localeCompare(b.department || ""),
      ...getColumnSearchProps("department"),
    },
    {
      title: "Status",
      dataIndex: "is_active",
      key: "is_active",
      filters: [
        { text: "Active", value: true },
        { text: "Inactive", value: false },
      ],
      onFilter: (value, record) => record.is_active === value,
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

  const filteredUsers = useMemo(() => {
    let result = users || [];

    // Apply global search
    if (tableParams.search) {
      const search = tableParams.search.toLowerCase();
      result = result.filter(
        (u) =>
          u.full_name.toLowerCase().includes(search) ||
          u.email.toLowerCase().includes(search) ||
          u.department?.toLowerCase().includes(search)
      );
    }

    return result;
  }, [users, tableParams.search]);

  return (
    <div>
      <StandardTable<User>
        tableParams={{
          ...tableParams,
          pagination: {
            ...tableParams.pagination,
            total: filteredUsers.length,
          },
        }}
        onChange={handleTableChange}
        loading={isLoading}
        dataSource={filteredUsers}
        columns={columns}
        rowKey="user_id"
        searchable={true}
        searchPlaceholder="Search users..."
        onSearch={handleSearch}
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
          changed_by: version.created_by_name || "System",
          changes: idx === 0 ? { created: "initial" } : { updated: "changed" },
        }))}
        entityName={`User: ${selectedUser?.full_name || ""}`}
        isLoading={historyLoading}
      />
    </div>
  );
};
