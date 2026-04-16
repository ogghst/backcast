/**
 * Project Member Manager Component
 *
 * Displays and manages project members with their roles.
 */

import { useState } from "react";
import { Table, Button, Select, Modal, message, Space, Tag, Avatar, Card, Input, Empty } from "antd";
import { PlusOutlined, DeleteOutlined, SearchOutlined, UserOutlined } from "@ant-design/icons";
import { useThemeTokens } from "@/hooks/useThemeTokens";
import { useAuthStore } from "@/stores/useAuthStore";
import {
  useProjectMembers,
  useRemoveProjectMember,
  useUpdateProjectMember,
  useAddProjectMember,
} from "../hooks/useProjectMembers";
import { useUsers } from "@/features/users/api/useUsers";
import { ProjectRole, type ProjectMemberRead } from "../types/projectMembers";
import type { ColumnsType } from "antd/es/table";
import { formatDate } from "@/utils/formatters";

interface ProjectMemberManagerProps {
  projectId: string;
  projectName?: string;
}

export const ProjectMemberManager = ({
  projectId,
  projectName,
}: ProjectMemberManagerProps) => {
  const { spacing, typography, borderRadius, colors } = useThemeTokens();
  const { user: currentUser } = useAuthStore();
  const [isAddModalOpen, setIsAddModalOpen] = useState(false);
  const [selectedUserId, setSelectedUserId] = useState<string | null>(null);
  const [selectedRole, setSelectedRole] = useState<ProjectRole>(ProjectRole.PROJECT_VIEWER);
  const [searchText, setSearchText] = useState("");

  // Fetch project members and available users
  const { data: members, isLoading } = useProjectMembers(projectId);
  const { data: users = [], isLoading: isLoadingUsers } = useUsers(100);

  // Mutations
  const addMemberMutation = useAddProjectMember();
  const removeMemberMutation = useRemoveProjectMember();
  const updateRoleMutation = useUpdateProjectMember();

  // Filter out users who are already members
  const memberUserIds = new Set(members?.map((m) => m.user_id) || []);
  const availableUsers = users.filter((user) => !memberUserIds.has(user.user_id));

  // Filter users by search text
  const filteredUsers = availableUsers.filter((user) => {
    const searchLower = searchText.toLowerCase();
    return (
      user.full_name?.toLowerCase().includes(searchLower) ||
      user.email.toLowerCase().includes(searchLower)
    );
  });

  // Get user initials for avatar
  const getUserInitials = (fullName: string) => {
    return fullName
      .split(" ")
      .map((n) => n[0])
      .join("")
      .toUpperCase()
      .slice(0, 2);
  };

  // Handle add member
  const handleAddMember = () => {
    if (!selectedUserId || !currentUser?.user_id) {
      message.error("Please select a user to add");
      return;
    }

    const selectedUser = users.find((u) => u.user_id === selectedUserId);
    if (!selectedUser) return;

    addMemberMutation.mutate(
      {
        user_id: selectedUserId,
        project_id: projectId,
        role: selectedRole,
        assigned_by: currentUser.user_id,
      },
      {
        onSuccess: () => {
          setIsAddModalOpen(false);
          setSelectedUserId(null);
          setSelectedRole(ProjectRole.PROJECT_VIEWER);
          setSearchText("");
          message.success(`Added ${selectedUser.full_name || selectedUser.email} to the project`);
        },
      }
    );
  };

  // Handle modal close
  const handleModalClose = () => {
    setIsAddModalOpen(false);
    setSelectedUserId(null);
    setSelectedRole(ProjectRole.PROJECT_VIEWER);
    setSearchText("");
  };

  // Role display configuration
  const roleConfig: Record<
    ProjectRole,
    { label: string; color: string; description: string }
  > = {
    [ProjectRole.PROJECT_ADMIN]: {
      label: "Admin",
      color: "red",
      description: "Full control including member management",
    },
    [ProjectRole.PROJECT_MANAGER]: {
      label: "Manager",
      color: "orange",
      description: "Manage project settings and content",
    },
    [ProjectRole.PROJECT_EDITOR]: {
      label: "Editor",
      color: "blue",
      description: "Edit project content",
    },
    [ProjectRole.PROJECT_VIEWER]: {
      label: "Viewer",
      color: "default",
      description: "Read-only access",
    },
  };

  // Handle role change
  const handleRoleChange = (member: ProjectMemberRead, newRole: ProjectRole) => {
    if (!currentUser?.user_id) {
      message.error("You must be logged in to perform this action");
      return;
    }

    updateRoleMutation.mutate({
      projectId,
      userId: member.user_id,
      update: {
        role: newRole,
        assigned_by: currentUser.user_id,
      },
    });
  };

  // Handle member removal
  const handleRemoveMember = (member: ProjectMemberRead) => {
    Modal.confirm({
      title: "Remove Project Member",
      content: `Are you sure you want to remove ${member.user_name || member.user_email} from this project?`,
      okText: "Remove",
      okType: "danger",
      cancelText: "Cancel",
      onOk: () => {
        removeMemberMutation.mutate({
          projectId,
          userId: member.user_id,
        });
      },
    });
  };

  // Table columns
  const columns: ColumnsType<ProjectMemberRead> = [
    {
      title: "Member",
      dataIndex: "user_name",
      key: "user_name",
      render: (name: string, record) => (
        <div>
          <div style={{ fontWeight: 500, fontSize: typography.sizes.md, color: colors.text }}>
            {name || record.user_email}
          </div>
          {name && record.user_email && (
            <div style={{ fontSize: typography.sizes.sm, color: colors.textSecondary }}>
              {record.user_email}
            </div>
          )}
        </div>
      ),
    },
    {
      title: "Role",
      dataIndex: "role",
      key: "role",
      width: 200,
      render: (role: ProjectRole, record) => {
        const isCurrentUser = record.user_id === currentUser?.user_id;

        return (
          <Select
            value={role}
            onChange={(newRole) => handleRoleChange(record, newRole)}
            loading={updateRoleMutation.isPending}
            disabled={isCurrentUser || updateRoleMutation.isPending}
            style={{ width: "100%" }}
            placeholder="Select role"
          >
            {Object.entries(roleConfig).map(([key, { label, color }]) => (
              <Select.Option key={key} value={key}>
                <Space size="small">
                  <Tag color={color}>{label}</Tag>
                  <span>{label}</span>
                </Space>
              </Select.Option>
            ))}
          </Select>
        );
      },
    },
    {
      title: "Added",
      dataIndex: "assigned_at",
      key: "assigned_at",
      width: 180,
      render: (date: string) => (
        <span style={{ fontSize: typography.sizes.sm }}>
          {formatDate(date)}
        </span>
      ),
    },
    {
      title: "Actions",
      key: "actions",
      width: 100,
      render: (_, record) => {
        const isCurrentUser = record.user_id === currentUser?.user_id;

        return (
          <Button
            icon={<DeleteOutlined />}
            danger
            size="small"
            disabled={isCurrentUser || removeMemberMutation.isPending}
            onClick={() => handleRemoveMember(record)}
          >
            Remove
          </Button>
        );
      },
    },
  ];

  return (
    <div
      style={{
        padding: spacing.md,
        backgroundColor: colors.bgContainer,
        borderRadius: borderRadius.lg,
      }}
    >
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          marginBottom: spacing.md,
        }}
      >
        <div>
          <h2 style={{ margin: 0, fontSize: typography.sizes.xl, color: colors.text }}>
            Project Members
          </h2>
          {projectName && (
            <p
              style={{
                margin: 0,
                marginTop: spacing.xs,
                fontSize: typography.sizes.sm,
                color: colors.textSecondary,
              }}
            >
              {projectName}
            </p>
          )}
        </div>
        <Button
          type="primary"
          icon={<PlusOutlined />}
          onClick={() => setIsAddModalOpen(true)}
        >
          Add Member
        </Button>
      </div>

      <Table
        columns={columns}
        dataSource={members || []}
        rowKey="id"
        loading={isLoading}
        pagination={false}
        size="middle"
        style={{ marginTop: spacing.md }}
      />

      {/* Add Member Modal */}
      <Modal
        title={
          <div style={{ display: "flex", alignItems: "center", gap: spacing.sm }}>
            <UserOutlined style={{ fontSize: typography.sizes.lg, color: colors.primary }} />
            <span style={{ fontSize: typography.sizes.xl, fontWeight: typography.weights.semiBold }}>
              Add Project Member
            </span>
          </div>
        }
        open={isAddModalOpen}
        onCancel={handleModalClose}
        onOk={handleAddMember}
        okText="Add Member"
        okButtonProps={{
          disabled: !selectedUserId || addMemberMutation.isPending,
          loading: addMemberMutation.isPending,
        }}
        cancelText="Cancel"
        width={600}
        destroyOnClose
        styles={{
          body: { padding: spacing.lg },
        }}
      >
        <div style={{ display: "flex", flexDirection: "column", gap: spacing.lg }}>
          {/* Search Input */}
          <div>
            <div
              style={{
                marginBottom: spacing.sm,
                fontSize: typography.sizes.sm,
                fontWeight: typography.weights.medium,
                color: colors.textSecondary,
              }}
            >
              Search Users
            </div>
            <Input
              placeholder="Search by name or email..."
              prefix={<SearchOutlined />}
              value={searchText}
              onChange={(e) => setSearchText(e.target.value)}
              size="large"
              allowClear
            />
          </div>

          {/* User List */}
          <div>
            <div
              style={{
                marginBottom: spacing.sm,
                fontSize: typography.sizes.sm,
                fontWeight: typography.weights.medium,
                color: colors.textSecondary,
              }}
            >
              Available Users ({filteredUsers.length})
            </div>
            <div
              style={{
                maxHeight: 300,
                overflowY: "auto",
                border: `1px solid ${colors.border}`,
                borderRadius: borderRadius.md,
                backgroundColor: colors.bgElevated,
              }}
            >
              {isLoadingUsers ? (
                <div style={{ padding: spacing.lg, textAlign: "center" }}>Loading users...</div>
              ) : filteredUsers.length === 0 ? (
                <Empty
                  description={
                    searchText
                      ? "No users match your search"
                      : "All users are already members of this project"
                  }
                  style={{ padding: spacing.lg }}
                />
              ) : (
                filteredUsers.map((user) => (
                  <Card
                    key={user.user_id}
                    hoverable
                    onClick={() => setSelectedUserId(user.user_id)}
                    style={{
                      margin: spacing.xs,
                      borderRadius: borderRadius.md,
                      border:
                        selectedUserId === user.user_id
                          ? `2px solid ${colors.primary}`
                          : `1px solid ${colors.border}`,
                      backgroundColor:
                        selectedUserId === user.user_id ? `${colors.primary}10` : colors.bgElevated,
                      cursor: "pointer",
                      transition: "all 0.2s ease",
                    }}
                    bodyStyle={{ padding: spacing.sm }}
                  >
                    <div style={{ display: "flex", alignItems: "center", gap: spacing.sm }}>
                      <Avatar
                        size={40}
                        style={{
                          backgroundColor: colors.primary,
                          flexShrink: 0,
                        }}
                      >
                        {getUserInitials(user.full_name || "U")}
                      </Avatar>
                      <div style={{ flex: 1, minWidth: 0 }}>
                        <div
                          style={{
                            fontSize: typography.sizes.md,
                            fontWeight: typography.weights.medium,
                            color: colors.text,
                            overflow: "hidden",
                            textOverflow: "ellipsis",
                            whiteSpace: "nowrap",
                          }}
                        >
                          {user.full_name || "Unknown User"}
                        </div>
                        <div
                          style={{
                            fontSize: typography.sizes.sm,
                            color: colors.textSecondary,
                            overflow: "hidden",
                            textOverflow: "ellipsis",
                            whiteSpace: "nowrap",
                          }}
                        >
                          {user.email}
                        </div>
                      </div>
                      {selectedUserId === user.user_id && (
                        <Tag color="blue" style={{ margin: 0 }}>
                          Selected
                        </Tag>
                      )}
                    </div>
                  </Card>
                ))
              )}
            </div>
          </div>

          {/* Role Selection */}
          <div>
            <div
              style={{
                marginBottom: spacing.sm,
                fontSize: typography.sizes.sm,
                fontWeight: typography.weights.medium,
                color: colors.textSecondary,
              }}
            >
              Select Role
            </div>
            <Select
              value={selectedRole}
              onChange={setSelectedRole}
              size="large"
              style={{ width: "100%" }}
              placeholder="Select a role"
            >
              {Object.entries(roleConfig).map(([key, { label, color, description }]) => (
                <Select.Option key={key} value={key}>
                  <Space size="small">
                    <Tag color={color}>{label}</Tag>
                    <span>{description}</span>
                  </Space>
                </Select.Option>
              ))}
            </Select>
          </div>

          {/* Selected User Summary */}
          {selectedUserId && (
            <div
              style={{
                padding: spacing.md,
                backgroundColor: `${colors.success}10`,
                border: `1px solid ${colors.success}`,
                borderRadius: borderRadius.md,
              }}
            >
              <div style={{ fontSize: typography.sizes.sm, color: colors.textSecondary }}>
                Adding{" "}
                <strong>
                  {users.find((u) => u.user_id === selectedUserId)?.full_name ||
                    users.find((u) => u.user_id === selectedUserId)?.email}
                </strong>{" "}
                as{" "}
                <Tag color={roleConfig[selectedRole].color} style={{ margin: 0 }}>
                  {roleConfig[selectedRole].label}
                </Tag>
              </div>
            </div>
          )}
        </div>
      </Modal>

      {/* Role Legend */}
      <div
        style={{
          marginTop: spacing.lg,
          padding: spacing.md,
          backgroundColor: colors.bgLayout,
          borderRadius: borderRadius.md,
        }}
      >
        <h4 style={{ margin: 0, marginBottom: spacing.sm, color: colors.text }}>Role Permissions</h4>
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))",
            gap: spacing.sm,
          }}
        >
          {Object.entries(roleConfig).map(([key, { label, color, description }]) => (
            <div key={key} style={{ display: "flex", alignItems: "flex-start", gap: spacing.xs }}>
              <Tag color={color}>{label}</Tag>
              <span style={{ fontSize: typography.sizes.sm, color: colors.textSecondary }}>{description}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};
