import { useCallback, useMemo } from "react";
import {
  Button,
  Dropdown,
  Popconfirm,
  Space,
  Tooltip,
  Typography,
  message,
  theme,
} from "antd";
import {
  CheckOutlined,
  CloseOutlined,
  EditOutlined,
  PlusOutlined,
  UndoOutlined,
  RedoOutlined,
  AppstoreOutlined,
} from "@ant-design/icons";
import { useDashboardCompositionStore } from "@/stores/useDashboardCompositionStore";
import { useDashboardLayoutTemplates } from "@/features/widgets/api/useDashboardLayouts";
import type { MenuProps } from "antd";

const { Text } = Typography;

/**
 * Toolbar for the dashboard composition page.
 *
 * View mode:  editable name | templates | [Reset] [Customize]
 * Edit mode:  editable name | templates | [Add Widget] [Cancel] [Done]
 *
 * All buttons are icon-only with Tooltip wrappers.
 * Edit mode uses transactional semantics: Done saves, Cancel discards.
 */
export function DashboardToolbar({ onSave }: { onSave: () => Promise<void> }) {
  const { token } = theme.useToken();
  const { message: messageApi, contextHolder } = message.useMessage();

  // Fallback in case messageApi is undefined (shouldn't happen with proper hook usage)
  const showMessage = messageApi ? messageApi.success : message.success;

  // Composition store state
  const isEditing = useDashboardCompositionStore((s) => s.isEditing);
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
  const undoStack = useDashboardCompositionStore((s) => s._undoStack);
  const redoStack = useDashboardCompositionStore((s) => s._redoStack);
  const undo = useDashboardCompositionStore((s) => s.undo);
  const redo = useDashboardCompositionStore((s) => s.redo);

  // Template query
  const { data: templates = [], isLoading: templatesLoading } =
    useDashboardLayoutTemplates();

  // Categorize templates into system and user
  const { systemTemplates, userTemplates } = useMemo(() => {
    const system = templates.filter((t) => t.is_template);
    const user = templates.filter((t) => !t.is_template && t.is_default);
    return { systemTemplates: system, userTemplates: user };
  }, [templates]);

  // Enter edit mode
  const handleCustomize = useCallback(() => {
    setEditing(true);
  }, [setEditing]);

  // Done: save then confirm (exit edit mode)
  const handleDone = useCallback(async () => {
    await onSave();
    useDashboardCompositionStore.getState().confirmChanges();
    showMessage("Dashboard saved");
  }, [onSave, showMessage]);

  // Handle name edit
  const handleNameChange = useCallback(
    (newName: string) => {
      if (newName && newName !== activeDashboard?.name) {
        updateDashboardName(newName);
      }
    },
    [activeDashboard?.name, updateDashboardName],
  );

  // Handle reset to default
  const handleReset = useCallback(() => {
    resetDashboard();
    showMessage("Dashboard reset to default");
  }, [resetDashboard, showMessage]);

  // Handle template selection
  const handleTemplateSelect: MenuProps["onClick"] = useCallback(
    (info) => {
      const templateId = info.key;
      const template = templates.find((t) => t.id === templateId);
      if (template) {
        const store = useDashboardCompositionStore.getState();
        store.loadFromBackend(template, true);
        store.setEditing(true);
        // Use showMessage fallback to avoid undefined issues
        showMessage(`Template "${template.name}" applied`);
      }
    },
    [templates, showMessage],
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
        {/* Left side: Name */}
        <Space
          size="middle"
          style={{ flex: 1, minWidth: 0, overflow: "hidden" }}
        >
          <Text
            editable={
              isEditing
                ? {
                    onChange: handleNameChange,
                    tooltip: "Click to edit dashboard name",
                  }
                : false
            }
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
        </Space>

        {/* Right side: Action buttons (icon-only with tooltips) */}
        <Space size="small" wrap>
          {isEditing ? (
            <>
              {/* Templates */}
              <Dropdown
                menu={{
                  items: templateMenuItems,
                  onClick: handleTemplateSelect,
                  loading: templatesLoading,
                }}
                trigger={["click"]}
                disabled={templatesLoading || templates.length === 0}
              >
                <Tooltip title="Templates">
                  <Button
                    icon={<AppstoreOutlined />}
                    loading={templatesLoading}
                    disabled={templates.length === 0}
                    aria-label="Select dashboard template"
                  />
                </Tooltip>
              </Dropdown>

              {/* Add Widget */}
              <Tooltip title="Add Widget">
                <Button
                  icon={<PlusOutlined />}
                  aria-label="Add widget to dashboard"
                  onClick={() => {
                    useDashboardCompositionStore.getState().setPaletteOpen(true);
                  }}
                />
              </Tooltip>

              {/* Undo */}
              <Tooltip title="Undo (Ctrl+Z)">
                <Button
                  icon={<UndoOutlined />}
                  aria-label="Undo"
                  disabled={undoStack.length === 0}
                  onClick={undo}
                />
              </Tooltip>

              {/* Redo */}
              <Tooltip title="Redo (Ctrl+Shift+Z)">
                <Button
                  icon={<RedoOutlined />}
                  aria-label="Redo"
                  disabled={redoStack.length === 0}
                  onClick={redo}
                />
              </Tooltip>

              {/* Cancel (always confirms discard) */}
              <Popconfirm
                title="Discard unsaved changes?"
                onConfirm={() => {
                  useDashboardCompositionStore.getState().discardChanges();
                }}
                okText="Discard"
                cancelText="Keep Editing"
                okButtonProps={{ danger: true }}
              >
                <Tooltip title="Cancel">
                  <Button
                    icon={<CloseOutlined />}
                    aria-label="Cancel editing"
                  />
                </Tooltip>
              </Popconfirm>

              {/* Done */}
              <Tooltip title="Done">
                <Button
                  type="primary"
                  icon={<CheckOutlined />}
                  aria-label="Save changes and finish editing"
                  onClick={handleDone}
                />
              </Tooltip>
            </>
          ) : (
            <>
              {/* Templates */}
              <Dropdown
                menu={{
                  items: templateMenuItems,
                  onClick: handleTemplateSelect,
                  loading: templatesLoading,
                }}
                trigger={["click"]}
                disabled={templatesLoading || templates.length === 0}
              >
                <Tooltip title="Templates">
                  <Button
                    icon={<AppstoreOutlined />}
                    loading={templatesLoading}
                    disabled={templates.length === 0}
                    aria-label="Select dashboard template"
                  />
                </Tooltip>
              </Dropdown>

              {/* Reset to default */}
              <Popconfirm
                title="Reset to Default Template"
                description="This will clear all your widgets and restore the default template. Continue?"
                onConfirm={handleReset}
                okText="Reset"
                cancelText="Cancel"
                okButtonProps={{ danger: true }}
              >
                <Tooltip title="Reset">
                  <Button
                    icon={<UndoOutlined />}
                    disabled={!activeDashboard}
                    aria-label="Reset dashboard to default"
                  />
                </Tooltip>
              </Popconfirm>

              {/* Customize */}
              <Tooltip title="Customize">
                <Button
                  icon={<EditOutlined />}
                  aria-label="Customize dashboard"
                  onClick={handleCustomize}
                />
              </Tooltip>
            </>
          )}
        </Space>
      </div>
    </>
  );
}
