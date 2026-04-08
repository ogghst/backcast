import { Button, Drawer, Switch, Typography, theme } from "antd";
import {
  DeleteOutlined,
  HolderOutlined,
} from "@ant-design/icons";
import { useCallback } from "react";
import { getWidgetDefinition } from "../registry";
import type { WidgetInstance } from "../types";

const { Text } = Typography;

interface MobileWidgetSheetProps {
  open: boolean;
  onClose: () => void;
  widgets: WidgetInstance[];
  onReorder: (fromIndex: number, toIndex: number) => void;
  onRemove: (instanceId: string) => void;
  onToggleHidden: (instanceId: string) => void;
  hiddenWidgets: Set<string>;
}

/**
 * Bottom sheet for managing widgets on mobile devices.
 * Supports reorder, hide/show, and remove operations.
 */
export function MobileWidgetSheet({
  open,
  onClose,
  widgets,
  onReorder,
  onRemove,
  onToggleHidden,
  hiddenWidgets,
}: MobileWidgetSheetProps) {
  const { token } = theme.useToken();

  const handleDragStart = useCallback(
    (e: React.DragEvent, index: number) => {
      e.dataTransfer.setData("text/plain", String(index));
      e.dataTransfer.effectAllowed = "move";
    },
    [],
  );

  const handleDrop = useCallback(
    (e: React.DragEvent, toIndex: number) => {
      e.preventDefault();
      const fromIndex = Number(e.dataTransfer.getData("text/plain"));
      if (fromIndex !== toIndex) {
        onReorder(fromIndex, toIndex);
      }
    },
    [onReorder],
  );

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.dataTransfer.dropEffect = "move";
  }, []);

  return (
    <Drawer
      title="Manage Widgets"
      placement="bottom"
      height="70vh"
      open={open}
      onClose={onClose}
      styles={{
        body: { padding: token.paddingSM, overflow: "auto" },
      }}
    >
      {widgets.map((widget, index) => {
        const definition = getWidgetDefinition(widget.typeId);
        const isHidden = hiddenWidgets.has(widget.instanceId);

        return (
          <div
            key={widget.instanceId}
            draggable
            onDragStart={(e) => handleDragStart(e, index)}
            onDrop={(e) => handleDrop(e, index)}
            onDragOver={handleDragOver}
            style={{
              display: "flex",
              alignItems: "center",
              gap: token.paddingSM,
              padding: token.paddingSM,
              marginBottom: token.paddingXXS,
              background: isHidden
                ? token.colorBgLayout
                : token.colorBgContainer,
              borderRadius: token.borderRadius,
              opacity: isHidden ? 0.5 : 1,
              touchAction: "none",
            }}
          >
            <HolderOutlined
              style={{ fontSize: 18, color: token.colorTextQuaternary }}
            />
            <Text
              ellipsis
              style={{ flex: 1, minWidth: 0 }}
            >
              {definition?.displayName ?? widget.typeId}
            </Text>
            <Switch
              size="small"
              checked={!isHidden}
              onChange={() => onToggleHidden(widget.instanceId)}
            />
            <Button
              type="text"
              size="small"
              icon={<DeleteOutlined />}
              danger
              onClick={() => onRemove(widget.instanceId)}
            />
          </div>
        );
      })}

      {widgets.length === 0 && (
        <div
          style={{
            textAlign: "center",
            padding: token.paddingXL,
            color: token.colorTextSecondary,
          }}
        >
          No widgets on this dashboard
        </div>
      )}
    </Drawer>
  );
}
