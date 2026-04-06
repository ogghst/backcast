import { useState, useCallback, useMemo } from "react";
import { Button, Drawer, Empty, Spin, theme, Typography } from "antd";
import {
  SettingOutlined,
  CloseOutlined,
  CheckOutlined,
} from "@ant-design/icons";
import { useDashboardCompositionStore } from "@/stores/useDashboardCompositionStore";
import { getWidgetDefinition } from "@/features/widgets/registry";

const { Text } = Typography;

/**
 * Widget configuration drawer.
 *
 * Opens when a widget is selected in edit mode, displaying the widget's
 * configuration form. The drawer supports Apply (save), Cancel (discard),
 * and close actions.
 */
export function WidgetConfigDrawer() {
  const { token } = theme.useToken();

  // Composition store state
  const selectedWidgetId = useDashboardCompositionStore(
    (s) => s.selectedWidgetId,
  );
  const activeDashboard = useDashboardCompositionStore(
    (s) => s.activeDashboard,
  );
  const updateWidgetConfig = useDashboardCompositionStore(
    (s) => s.updateWidgetConfig,
  );
  const selectWidget = useDashboardCompositionStore((s) => s.selectWidget);

  // Local state for pending changes (applies on click Apply)
  const [pendingConfig, setPendingConfig] = useState<
    Record<string, unknown> | null
  >(null);

  // Find the selected widget and its definition
  const { widget, definition, ConfigFormComponent } = useMemo(() => {
    if (!selectedWidgetId || !activeDashboard) {
      return { widget: null, definition: null, ConfigFormComponent: null };
    }

    const widget = activeDashboard.widgets.find(
      (w) => w.instanceId === selectedWidgetId,
    );

    if (!widget) {
      return { widget: null, definition: null, ConfigFormComponent: null };
    }

    const definition = getWidgetDefinition(widget.typeId);

    if (!definition) {
      return { widget, definition: null, ConfigFormComponent: null };
    }

    const ConfigFormComponent = definition.configFormComponent;

    return { widget, definition, ConfigFormComponent };
  }, [selectedWidgetId, activeDashboard]);

  // Current config value (use pending if available, otherwise widget's config)
  const currentConfig = useMemo(() => {
    return pendingConfig ?? widget?.config ?? {};
  }, [pendingConfig, widget?.config]);

  // Whether the drawer is open
  const open = !!selectedWidgetId && !!widget && !!definition;

  // Handle config change from form
  const handleConfigChange = useCallback(
    (partialConfig: Partial<Record<string, unknown>>) => {
      setPendingConfig({ ...currentConfig, ...partialConfig });
    },
    [currentConfig],
  );

  // Handle close (X button, click outside, Escape)
  const handleClose = useCallback(() => {
    setPendingConfig(null);
    selectWidget(null);
  }, [selectWidget]);

  // Handle Apply button
  const handleApply = useCallback(() => {
    if (selectedWidgetId && pendingConfig) {
      updateWidgetConfig(selectedWidgetId, pendingConfig);
      handleClose();
    }
  }, [selectedWidgetId, pendingConfig, updateWidgetConfig, handleClose]);

  // Handle Cancel button
  const handleCancel = useCallback(() => {
    setPendingConfig(null);
    handleClose();
  }, [handleClose]);

  // Whether there are pending changes
  const hasPendingChanges =
    !!pendingConfig &&
    !!widget?.config &&
    JSON.stringify(pendingConfig) !== JSON.stringify(widget.config);

  return (
    <Drawer
      title={
        <span
          style={{
            display: "flex",
            alignItems: "center",
            gap: token.paddingSM,
          }}
        >
          <SettingOutlined />
          <span>
            Configure{" "}
            <Text strong style={{ marginLeft: token.paddingXS }}>
              {definition?.displayName ?? widget?.title ?? "Widget"}
            </Text>
          </span>
        </span>
      }
      placement="right"
      width={400}
      open={open}
      onClose={handleClose}
      closeIcon={<CloseOutlined />}
      styles={{
        footer: {
          display: "flex",
          justifyContent: "flex-end",
          gap: token.paddingSM,
          padding: token.paddingMD,
          borderTop: `1px solid ${token.colorBorderSecondary}`,
        },
      }}
      footer={
        <>
          {/* Cancel button */}
          {hasPendingChanges && (
            <Button onClick={handleCancel}>Cancel</Button>
          )}

          {/* Apply button */}
          <Button
            type="primary"
            icon={<CheckOutlined />}
            onClick={handleApply}
            disabled={!hasPendingChanges}
          >
            Apply
          </Button>
        </>
      }
    >
      {/* Loading state */}
      {!widget && selectedWidgetId && (
        <div style={{ textAlign: "center", padding: token.paddingXL }}>
          <Spin />
        </div>
      )}

      {/* Widget not found */}
      {widget && !definition && (
        <Empty
          description="Widget definition not found"
          image={Empty.PRESENTED_IMAGE_SIMPLE}
        />
      )}

      {/* No config form available */}
      {widget && definition && !ConfigFormComponent && (
        <Empty
          description="This widget does not have any configurable options"
          image={Empty.PRESENTED_IMAGE_SIMPLE}
        />
      )}

      {/* Render config form */}
      {widget && definition && ConfigFormComponent && (
        <ConfigFormComponent
          config={currentConfig}
          onChange={handleConfigChange}
        />
      )}
    </Drawer>
  );
}
