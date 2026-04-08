import { Modal, theme } from "antd";
import { useCallback } from "react";
import { getWidgetDefinition } from "../registry";
import { useDashboardCompositionStore } from "@/stores/useDashboardCompositionStore";
import { useFullscreenWidgetStore } from "@/stores/useFullscreenWidgetStore";
import type { WidgetInstance } from "../types";

interface WidgetFullscreenModalProps {
  widget: WidgetInstance;
  isEditing: boolean;
}

/**
 * Fullscreen modal rendering a single widget at full viewport size.
 */
export function WidgetFullscreenModal({
  widget,
  isEditing,
}: WidgetFullscreenModalProps) {
  const { token } = theme.useToken();
  const definition = getWidgetDefinition(widget.typeId);
  const removeWidget = useDashboardCompositionStore((s) => s.removeWidget);
  const selectWidget = useDashboardCompositionStore((s) => s.selectWidget);
  const fullscreenInstanceId = useFullscreenWidgetStore(
    (s) => s.fullscreenInstanceId,
  );
  const closeFullscreen = useFullscreenWidgetStore((s) => s.closeFullscreen);

  const open = fullscreenInstanceId === widget.instanceId;

  const handleAfterOpenChange = useCallback((isOpen: boolean) => {
    if (isOpen) {
      setTimeout(() => {
        window.dispatchEvent(new Event("resize"));
      }, 100);
    }
  }, []);

  if (!definition) return null;

  const WidgetComponent = definition.component;

  return (
    <Modal
      open={open}
      onCancel={closeFullscreen}
      footer={null}
      destroyOnClose
      width="100vw"
      style={{ top: 0, padding: 0, maxWidth: "100vw" }}
      styles={{
        body: {
          height: "calc(100vh - 55px)",
          overflow: "auto",
          padding: token.paddingMD,
        },
      }}
      afterOpenChange={handleAfterOpenChange}
      title={definition.displayName}
    >
      <WidgetComponent
        config={
          widget.config as Parameters<typeof WidgetComponent>[0]["config"]
        }
        instanceId={widget.instanceId}
        isEditing={isEditing}
        onRemove={() => {
          removeWidget(widget.instanceId);
          closeFullscreen();
        }}
        onConfigure={() => selectWidget(widget.instanceId)}
      />
    </Modal>
  );
}
