import { Button, Result } from "antd";
import { LockOutlined } from "@ant-design/icons";

/**
 * Locked placeholder rendered **in place** of a widget component when the
 * current user lacks the widget's `requiredPermission` (global-dashboard-
 * widgets Phase 5, D2 / G3).
 *
 * The placeholder keeps the react-grid-layout cell stable (it is rendered
 * inside the existing wrapper div + {@link WidgetErrorBoundary}) so the grid
 * does not reflow and saved x/y/w/h stay put. It deliberately does **not**
 * call any data hook or mount the real widget component — no 403 storms, no
 * leaked data.
 *
 * The placeholder exposes **no** `onFullscreen` callback (synthesis G3):
 * locked widgets are not fullscreen-able, so `WidgetFullscreenModal` is
 * unreachable for a locked cell and its render path is intentionally left
 * untouched.
 *
 * Styling mirrors the {@link WidgetErrorBoundary} Result so locked + errored
 * widgets read as one consistent family.
 */
export function WidgetPermissionPlaceholder({
  displayName,
  isEditing,
  onRemove,
}: {
  displayName?: string;
  isEditing: boolean;
  onRemove: () => void;
}) {
  return (
    <div
      style={{
        padding: 16,
        height: "100%",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
      }}
    >
      <Result
        status="403"
        icon={<LockOutlined />}
        title={displayName ?? "Widget"}
        subTitle="Your role doesn't include permission to view this widget."
        extra={
          isEditing ? (
            <Button key="remove" danger onClick={onRemove}>
              Remove
            </Button>
          ) : undefined
        }
      />
    </div>
  );
}
