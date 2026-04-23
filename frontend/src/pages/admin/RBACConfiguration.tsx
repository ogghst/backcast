/**
 * RBAC Configuration Admin Page
 *
 * Provides admin interface for managing RBAC roles and permissions.
 * Shows a provider indicator banner and supports read-only mode when
 * the RBAC provider is JSON (file-based).
 */

import {
  Alert,
  App,
  Button,
  Checkbox,
  Collapse,
  Form,
  Input,
  Modal,
  Space,
  Tag,
  Tooltip,
  theme,
} from "antd";
import {
  CheckOutlined,
  DeleteOutlined,
  EditOutlined,
  LockOutlined,
  PlusOutlined,
  SearchOutlined,
} from "@ant-design/icons";
import { useCallback, useMemo, useState } from "react";
import type { CSSProperties } from "react";
import type { ColumnType } from "antd/es/table";

import { StandardTable } from "@/components/common/StandardTable";
import { useTableParams } from "@/hooks/useTableParams";
import { useThemeTokens } from "@/hooks/useThemeTokens";
import {
  useRBACRoles,
  useRBACPermissions,
  useRBACProviderStatus,
  useCreateRBACRole,
  useUpdateRBACRole,
  useDeleteRBACRole,
} from "@/features/admin/rbac/hooks/useRBAC";
import {
  PERMISSION_METADATA,
  getActionLabel,
  groupPermissionsByTopic,
} from "@/features/admin/rbac/permissions";
import type { PermissionTopic } from "@/features/admin/rbac/permissions";
import type { RBACRoleRead, RBACRoleCreate } from "@/api/types/rbac";

// ---------------------------------------------------------------------------
// Permission Selector Component
// ---------------------------------------------------------------------------

interface PermissionSelectorProps {
  value?: string[];
  onChange?: (value: string[]) => void;
  allPermissions: string[];
  disabled?: boolean;
}

const PermissionSelector: React.FC<PermissionSelectorProps> = ({
  value = [],
  onChange,
  allPermissions,
  disabled = false,
}) => {
  const { token } = theme.useToken();
  const { colors, spacing, borderRadius } = useThemeTokens();
  const [searchText, setSearchText] = useState("");

  const topics = useMemo(
    () => groupPermissionsByTopic(allPermissions),
    [allPermissions],
  );

  const filteredTopics = useMemo(() => {
    if (!searchText.trim()) return topics;

    const lower = searchText.toLowerCase();
    return topics
      .map((topic) => ({
        ...topic,
        permissions: topic.permissions.filter((perm) => {
          const meta = PERMISSION_METADATA[perm];
          const actionLabel = getActionLabel(perm);
          return (
            perm.toLowerCase().includes(lower) ||
            (meta?.description ?? "").toLowerCase().includes(lower) ||
            (meta?.topic ?? "").toLowerCase().includes(lower) ||
            actionLabel.toLowerCase().includes(lower)
          );
        }),
      }))
      .filter((topic) => topic.permissions.length > 0);
  }, [topics, searchText]);

  const selectedSet = useMemo(() => new Set(value), [value]);

  const togglePermission = useCallback(
    (perm: string) => {
      if (disabled) return;
      const next = selectedSet.has(perm)
        ? value.filter((p) => p !== perm)
        : [...value, perm];
      onChange?.(next);
    },
    [disabled, selectedSet, value, onChange],
  );

  const toggleTopic = useCallback(
    (topic: PermissionTopic) => {
      if (disabled) return;
      const allSelected = topic.permissions.every((p) => selectedSet.has(p));
      let next: string[];
      if (allSelected) {
        // Deselect all in topic
        next = value.filter((p) => !topic.permissions.includes(p));
      } else {
        // Select all in topic (union)
        const toAdd = topic.permissions.filter((p) => !selectedSet.has(p));
        next = [...value, ...toAdd];
      }
      onChange?.(next);
    },
    [disabled, value, selectedSet, onChange],
  );

  const collapseItems = useMemo(
    () =>
      filteredTopics.map((topic) => {
        const selectedCount = topic.permissions.filter((p) =>
          selectedSet.has(p),
        ).length;
        const total = topic.permissions.length;
        const allSelected = total > 0 && selectedCount === total;

        return {
          key: topic.name,
          label: (
            <div
              style={{
                display: "flex",
                alignItems: "center",
                justifyContent: "space-between",
                width: "100%",
                paddingRight: spacing.xs,
              }}
            >
              <span
                style={{
                  fontWeight: 600,
                  fontSize: token.fontSize,
                  color: colors.text,
                }}
              >
                {topic.name}
              </span>
              <Space
                size={spacing.xs}
                onClick={(e) => e.stopPropagation()}
              >
                <span
                  style={{
                    fontSize: token.fontSizeSM,
                    color: colors.textSecondary,
                  }}
                >
                  {selectedCount}/{total}
                </span>
                {!disabled && (
                  <Checkbox
                    checked={allSelected}
                    indeterminate={
                      selectedCount > 0 && selectedCount < total
                    }
                    onChange={() => toggleTopic(topic)}
                  />
                )}
              </Space>
            </div>
          ),
          children: (
            <div
              style={{
                display: "flex",
                flexWrap: "wrap",
                gap: spacing.sm,
              }}
            >
              {topic.permissions.map((perm) => {
                const meta = PERMISSION_METADATA[perm];
                const isSelected = selectedSet.has(perm);
                const actionLabel = getActionLabel(perm);

                return (
                  <PermissionCard
                    key={perm}
                    label={actionLabel}
                    description={meta?.description ?? perm}
                    selected={isSelected}
                    disabled={disabled}
                    onClick={() => togglePermission(perm)}
                    colors={colors}
                    spacing={spacing}
                    borderRadius={borderRadius}
                    token={token}
                  />
                );
              })}
            </div>
          ),
        };
      }),
    [
      filteredTopics,
      selectedSet,
      disabled,
      toggleTopic,
      togglePermission,
      colors,
      spacing,
      borderRadius,
      token,
    ],
  );

  return (
    <div>
      <Input
        prefix={<SearchOutlined />}
        placeholder="Filter permissions..."
        value={searchText}
        onChange={(e) => setSearchText(e.target.value)}
        allowClear
        size="small"
        style={{ marginBottom: spacing.sm }}
        disabled={disabled}
      />
      <div
        style={{
          maxHeight: 420,
          overflowY: "auto",
          paddingRight: spacing.xs,
        }}
      >
        <Collapse
          items={collapseItems}
          defaultActiveKey={topics.map((t) => t.name)}
          ghost
          size="small"
        />
      </div>
    </div>
  );
};

// ---------------------------------------------------------------------------
// Permission Card (toggle card with 3D effect)
// ---------------------------------------------------------------------------

interface PermissionCardProps {
  label: string;
  description: string;
  selected: boolean;
  disabled: boolean;
  onClick: () => void;
  colors: ReturnType<typeof useThemeTokens>["colors"];
  spacing: ReturnType<typeof useThemeTokens>["spacing"];
  borderRadius: ReturnType<typeof useThemeTokens>["borderRadius"];
  token: ReturnType<typeof theme.useToken>["token"];
}

const cardTransition: CSSProperties = {
  transition:
    "transform 200ms ease, box-shadow 200ms ease, border-color 200ms ease, border-left-color 200ms ease, background-color 200ms ease",
};

const PermissionCard: React.FC<PermissionCardProps> = ({
  label,
  description,
  selected,
  disabled,
  onClick,
  colors,
  spacing,
  borderRadius,
  token,
}) => {
  const cursor = disabled ? "not-allowed" : "pointer";
  const opacity = disabled ? 0.5 : 1;

  return (
    <div
      role="button"
      tabIndex={disabled ? -1 : 0}
      aria-pressed={selected}
      onClick={disabled ? undefined : onClick}
      onKeyDown={(e) => {
        if (!disabled && (e.key === "Enter" || e.key === " ")) {
          e.preventDefault();
          onClick();
        }
      }}
      style={{
        ...cardTransition,
        position: "relative",
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        padding: `${spacing.sm}px ${spacing.md}px`,
        minWidth: 90,
        maxWidth: 120,
        backgroundColor: selected
          ? token.colorPrimaryBg
          : token.colorFillQuaternary,
        border: selected
          ? `1px solid ${token.colorPrimary}`
          : `1px solid ${token.colorBorderSecondary}`,
        borderLeft: selected
          ? `4px solid ${token.colorPrimary}`
          : `1px solid ${token.colorBorderSecondary}`,
        borderRadius: borderRadius.md,
        boxShadow: selected
          ? `0 3px 12px ${token.colorPrimaryBorder}`
          : "none",
        transform: selected ? "translateY(-2px)" : "none",
        cursor,
        opacity,
        userSelect: "none",
      }}
    >
      {selected && (
        <CheckOutlined
          style={{
            position: "absolute",
            top: 4,
            right: 4,
            fontSize: token.fontSizeXS,
            color: token.colorPrimary,
          }}
        />
      )}
      <span
        style={{
          fontSize: token.fontSizeSM,
          fontWeight: selected ? 600 : 400,
          color: selected ? token.colorPrimary : token.colorTextSecondary,
          lineHeight: 1.2,
          textAlign: "center",
        }}
      >
        {label}
      </span>
      <span
        style={{
          fontSize: token.fontSizeXS,
          color: colors.textTertiary,
          marginTop: 2,
          textAlign: "center",
          lineHeight: 1.3,
          whiteSpace: "nowrap",
          overflow: "hidden",
          textOverflow: "ellipsis",
          maxWidth: "100%",
        }}
      >
        {description}
      </span>
    </div>
  );
};

// ---------------------------------------------------------------------------
// Role Modal Component
// ---------------------------------------------------------------------------

interface RoleModalProps {
  open: boolean;
  onCancel: () => void;
  onOk: (values: RBACRoleCreate) => Promise<void>;
  confirmLoading: boolean;
  initialValues?: RBACRoleRead | null;
  allPermissions: string[];
  editable: boolean;
}

const RoleModal: React.FC<RoleModalProps> = ({
  open,
  onCancel,
  onOk,
  confirmLoading,
  initialValues,
  allPermissions,
  editable,
}) => {
  const [form] = Form.useForm<RBACRoleCreate>();

  return (
    <Modal
      title={initialValues ? "Edit Role" : "Create Role"}
      open={open}
      onCancel={onCancel}
      onOk={() => form.submit()}
      confirmLoading={confirmLoading}
      okButtonProps={{ disabled: !editable }}
      destroyOnHidden
      width={720}
    >
      <Form<RBACRoleCreate>
        form={form}
        layout="vertical"
        initialValues={
          initialValues
            ? {
                name: initialValues.name,
                description: initialValues.description ?? "",
                permissions: initialValues.permissions.map((p) => p.permission),
              }
            : { permissions: [] }
        }
        onFinish={onOk}
        disabled={!editable}
      >
        <Form.Item
          name="name"
          label="Name"
          rules={[{ required: true, message: "Role name is required" }]}
        >
          <Input placeholder="e.g. project_manager" />
        </Form.Item>

        <Form.Item name="description" label="Description">
          <Input.TextArea rows={2} placeholder="Optional description" />
        </Form.Item>

        <Form.Item
          name="permissions"
          label="Permissions"
          rules={[
            {
              required: true,
              message: "At least one permission is required",
            },
          ]}
        >
          <PermissionSelector allPermissions={allPermissions} />
        </Form.Item>
      </Form>
    </Modal>
  );
};

// ---------------------------------------------------------------------------
// Main Page Component
// ---------------------------------------------------------------------------

export const RBACConfiguration: React.FC = () => {
  const { token } = theme.useToken();
  const { tableParams, handleTableChange } = useTableParams<RBACRoleRead>();
  const { modal } = App.useApp();

  // Data queries
  const { data: roles, isLoading } = useRBACRoles();
  const { data: allPermissions = [] } = useRBACPermissions();
  const { data: providerStatus } = useRBACProviderStatus();

  const isEditable = providerStatus?.editable ?? false;

  // Mutations
  const { mutateAsync: createRole, isPending: isCreating } =
    useCreateRBACRole();
  const { mutateAsync: updateRole, isPending: isUpdating } =
    useUpdateRBACRole();
  const { mutate: deleteRole } = useDeleteRBACRole();

  // Modal state
  const [modalOpen, setModalOpen] = useState(false);
  const [selectedRole, setSelectedRole] = useState<RBACRoleRead | null>(null);

  const handleCreate = () => {
    setSelectedRole(null);
    setModalOpen(true);
  };

  const handleEdit = (role: RBACRoleRead) => {
    setSelectedRole(role);
    setModalOpen(true);
  };

  const handleDelete = (role: RBACRoleRead) => {
    if (role.is_system) return;

    modal.confirm({
      title: "Are you sure you want to delete this role?",
      content: `Role "${role.name}" will be permanently removed.`,
      okText: "Yes, Delete",
      okType: "danger",
      onOk: () => deleteRole(role.id),
    });
  };

  const handleModalOk = async (values: RBACRoleCreate) => {
    if (selectedRole) {
      await updateRole({ id: selectedRole.id, ...values });
    } else {
      await createRole(values);
    }
    setModalOpen(false);
  };

  // ---- Columns ----
  const columns: ColumnType<RBACRoleRead>[] = [
    {
      title: "Name",
      dataIndex: "name",
      key: "name",
      sorter: true,
      render: (name: string, record) => (
        <Space>
          <span>{name}</span>
          {record.is_system && (
            <Tag color="blue" style={{ marginLeft: token.marginXXS }}>
              System
            </Tag>
          )}
        </Space>
      ),
    },
    {
      title: "Description",
      dataIndex: "description",
      key: "description",
      ellipsis: true,
    },
    {
      title: "Permissions",
      key: "permissions_count",
      width: 120,
      sorter: false,
      render: (_, record) => (
        <Tag>{record.permissions.length} permissions</Tag>
      ),
    },
    {
      title: "Actions",
      key: "actions",
      width: 140,
      render: (_, record) => {
        if (!isEditable) {
          return <span style={{ color: token.colorTextDisabled }}>N/A</span>;
        }

        return (
          <Space>
            <Button
              icon={<EditOutlined />}
              onClick={() => handleEdit(record)}
              title="Edit Role"
              size="small"
            />
            <Tooltip title={record.is_system ? "System roles cannot be deleted" : ""}>
              <Button
                danger
                icon={<DeleteOutlined />}
                onClick={() => handleDelete(record)}
                disabled={record.is_system}
                title={record.is_system ? "System role" : "Delete Role"}
                size="small"
              />
            </Tooltip>
          </Space>
        );
      },
    },
  ];

  return (
    <div>
      {/* Provider status banner */}
      {providerStatus && (
        <Alert
          type={isEditable ? "success" : "info"}
          title={
            isEditable
              ? "RBAC Provider: Database"
              : "RBAC Provider: JSON (read-only)"
          }
          description={
            isEditable
              ? "Roles and permissions are managed via the database."
              : 'To manage roles, switch the RBAC_PROVIDER setting to "database".'
          }
          showIcon
          style={{ marginBottom: token.marginMD }}
          icon={isEditable ? undefined : <LockOutlined />}
        />
      )}

      <StandardTable<RBACRoleRead>
        tableParams={tableParams}
        onChange={handleTableChange}
        loading={isLoading}
        dataSource={roles || []}
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
            <div style={{ fontSize: token.fontSizeLG, fontWeight: "bold" }}>
              RBAC Configuration
            </div>
            <Button
              type="primary"
              icon={<PlusOutlined />}
              onClick={handleCreate}
              disabled={!isEditable}
            >
              Create Role
            </Button>
          </div>
        }
      />

      <RoleModal
        open={modalOpen}
        onCancel={() => setModalOpen(false)}
        onOk={handleModalOk}
        confirmLoading={isCreating || isUpdating}
        initialValues={selectedRole}
        allPermissions={allPermissions}
        editable={isEditable}
      />
    </div>
  );
};
