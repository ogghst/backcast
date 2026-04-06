import { useCallback, useMemo } from "react";
import {
  Button,
  Dropdown,
  Popconfirm,
  Space,
  Typography,
  message,
  theme,
} from "antd";
import {
  CheckOutlined,
  EditOutlined,
  PlusOutlined,
  SaveOutlined,
  UndoOutlined,
  AppstoreOutlined,
} from "@ant-design/icons";
import { useDashboardCompositionStore } from "@/stores/useDashboardCompositionStore";
import { useDashboardLayoutTemplates } from "@/features/widgets/api/useDashboardLayouts";
import type { MenuProps } from "antd";

const { Text } = Typography;

/**
 * Enhanced toolbar for the dashboard composition page.
 *
 * Features:
 * - Editable dashboard name (marks dirty on change)
 * - Save button with dirty-state indicator (red dot)
 * - Template selector dropdown (system + user templates)
 * - "Reset to Default" with confirmation
 * - Customize/Done toggle (auto-saves on Done)
 * - Add Widget button (edit mode only)
 * - Responsive layout
 */
export function DashboardToolbar({ onSave }: { onSave: () => Promise<void> }) {
  const { token } = theme.useToken();
  const { message: messageApi, contextHolder } = message.useMessage();

  // Composition store state
  const isEditing = useDashboardCompositionStore((s) => s.isEditing);
  const isDirty = useDashboardCompositionStore((s) => s.isDirty);
  const activeDashboard = useDashboardCompositionStore(
    (s) => s.activeDashboard,
  );
  const setEditing = useDashboardCompositionStore((s) => s.setEditing);
  const updateDashboardName = useDashboardCompositionStore(
    (s) => s.updateDashboardName,
  );
  const resetDashboard = useDashboardCompositionStore(
    (s) => s.resetDashboard,
  );

  // Template query
  const { data: templates = [], isLoading: templatesLoading } =
    useDashboardLayoutTemplates();

  // Categorize templates into system and user
  const { systemTemplates, userTemplates } = useMemo(() => {
    const system = templates.filter((t) => t.is_template);
    const user = templates.filter((t) => !t.is_template && t.is_default);
    return { systemTemplates: system, userTemplates: user };
  }, [templates]);

  // Toggle edit mode
  const handleToggleEdit = useCallback(async () => {
    if (isEditing && isDirty) {
      // Auto-save before exiting edit mode
      await onSave();
      messageApi.success("Dashboard saved");
    }
    setEditing(!isEditing);
  }, [isEditing, isDirty, onSave, setEditing, messageApi]);

  // Handle name edit
  const handleNameChange = useCallback(
    (newName: string) => {
      if (newName && newName !== activeDashboard?.name) {
        updateDashboardName(newName);
      }
    },
    [activeDashboard?.name, updateDashboardName],
  );

  // Handle explicit save
  const handleSave = useCallback(async () => {
    await onSave();
    messageApi.success("Dashboard saved");
  }, [onSave, messageApi]);

  // Handle reset to default
  const handleReset = useCallback(() => {
    resetDashboard();
    messageApi.success("Dashboard reset to default");
  }, [resetDashboard, messageApi]);

  // Handle template selection
  const handleTemplateSelect: MenuProps["onClick"] = useCallback(
    (info) => {
      const templateId = info.key;
      const template = templates.find((t) => t.id === templateId);
      if (template) {
        // Load template into dashboard
        const store = useDashboardCompositionStore.getState();
        store.loadFromBackend(template);
        store.setEditing(true);
        messageApi.success(`Template "${template.name}" applied`);
      }
    },
    [templates, messageApi],
  );

  // Build template dropdown menu
  const templateMenuItems: MenuProps["items"] = useMemo(() => {
    const items: MenuProps["items"] = [];

    if (systemTemplates.length > 0) {
      items.push({
        type: "group",
        label: "System Templates",
        children: systemTemplates.map((template) => ({
          key: template.id,
          label: (
            <Space>
              <AppstoreOutlined />
              <span>{template.name}</span>
              <span style={{ color: token.colorTextSecondary }}>
                ({template.widgets.length})
              </span>
            </Space>
          ),
        })),
      });
    }

    if (userTemplates.length > 0) {
      items.push({
        type: "group",
        label: "My Templates",
        children: userTemplates.map((template) => ({
          key: template.id,
          label: (
            <Space>
              <AppstoreOutlined />
              <span>{template.name}</span>
              <span style={{ color: token.colorTextSecondary }}>
                ({template.widgets.length})
              </span>
            </Space>
          ),
        })),
      });
    }

    if (items.length === 0) {
      items.push({
        key: "no-templates",
        label: "No templates available",
        disabled: true,
      });
    }

    return items;
  }, [systemTemplates, userTemplates, token.colorTextSecondary]);

  return (
    <>
      {contextHolder}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          padding: `${token.paddingSM}px ${token.paddingMD}px`,
          background: token.colorBgContainer,
          borderBottom: `1px solid ${token.colorBorderSecondary}`,
          borderRadius: token.borderRadiusLG,
          marginBottom: token.paddingSM,
          flexWrap: "wrap",
          gap: token.paddingSM,
        }}
      >
        {/* Left side: Name and template selector */}
        <Space
          size="middle"
          style={{ flex: 1, minWidth: 0, overflow: "hidden" }}
        >
          <Text
            editable={{
              onChange: handleNameChange,
              tooltip: "Click to edit dashboard name",
            }}
            strong
            style={{
              fontSize: token.fontSizeLG,
              whiteSpace: "nowrap",
              overflow: "hidden",
              textOverflow: "ellipsis",
            }}
          >
            {activeDashboard?.name ?? "My Dashboard"}
          </Text>

          <Dropdown
            menu={{
              items: templateMenuItems,
              onClick: handleTemplateSelect,
              loading: templatesLoading,
            }}
            trigger={["click"]}
            disabled={templatesLoading || templates.length === 0}
          >
            <Button
              icon={<AppstoreOutlined />}
              loading={templatesLoading}
              disabled={templates.length === 0}
              aria-label="Select dashboard template"
            >
              Templates
            </Button>
          </Dropdown>
        </Space>

        {/* Right side: Action buttons */}
        <Space size="small" wrap>
          {/* Edit mode: Add widget button */}
          {isEditing && (
            <Button
              icon={<PlusOutlined />}
              aria-label="Add widget to dashboard"
              onClick={() => {
                useDashboardCompositionStore.getState().setPaletteOpen(true);
              }}
            >
              Add Widget
            </Button>
          )}

          {/* Save button (shows when dirty) */}
          {isDirty && (
            <Button
              type="primary"
              icon={<SaveOutlined />}
              aria-label="Save dashboard changes"
              onClick={handleSave}
            >
              Save
            </Button>
          )}

          {/* Reset to default button */}
          <Popconfirm
            title="Reset to Default Template"
            description="This will clear all your widgets and restore the default template. Continue?"
            onConfirm={handleReset}
            okText="Reset"
            cancelText="Cancel"
            okButtonProps={{ danger: true }}
          >
            <Button icon={<UndoOutlined />} disabled={!activeDashboard} aria-label="Reset dashboard to default">
              Reset
            </Button>
          </Popconfirm>

          {/* Customize/Done toggle */}
          <Button
            aria-label={isEditing ? "Finish customizing dashboard" : "Customize dashboard"}
            type={isEditing ? "primary" : "default"}
            icon={
              isEditing ? (
                <>
                  {isDirty && (
                    <span
                      style={{
                        display: "inline-block",
                        width: 8,
                        height: 8,
                        borderRadius: "50%",
                        background: token.colorError,
                        marginRight: token.paddingXXS,
                      }}
                    />
                  )}
                  <CheckOutlined />
                </>
              ) : (
                <EditOutlined />
              )
            }
            onClick={handleToggleEdit}
          >
            {isEditing ? "Done" : "Customize"}
          </Button>
        </Space>
      </div>
    </>
  );
}
