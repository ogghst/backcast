import type { ReactNode } from "react";
import { useState, useRef, useEffect, useCallback } from "react";
import { Button, Skeleton, theme } from "antd";
import {
  DeleteOutlined,
  DownOutlined,
  DragOutlined,
  ColumnWidthOutlined,
  RightOutlined,
  ReloadOutlined,
  EllipsisOutlined,
  SettingOutlined,
  FullscreenOutlined,
} from "@ant-design/icons";
import { ErrorBoundary } from "react-error-boundary";
import { useWidgetInteraction } from "./WidgetInteractionContext";
import { WidgetExportMenu } from "./WidgetExportMenu";

/**
 * Props for the WidgetShell component.
 *
 * Wraps widget content with a minimized header pattern,
 * loading/error states, and edit-mode behaviors.
 */
export interface WidgetShellProps {
  /** Unique instance identifier */
  instanceId: string;
  /** Widget title displayed in the toolbar */
  title: string;
  /** Optional icon displayed in the trigger and toolbar */
  icon?: ReactNode;
  /** Whether the dashboard is in edit mode */
  isEditing: boolean;
  /** Show loading skeleton overlay */
  isLoading?: boolean;
  /** Error to display */
  error?: Error | null;
  /** Called when the remove button is clicked */
  onRemove: () => void;
  /** Called when the refresh button is clicked */
  onRefresh?: () => void;
  /** Called when the settings button is clicked (edit mode) */
  onConfigure?: () => void;
  /** Called when the fullscreen button is clicked */
  onFullscreen?: () => void;
  /** Widget type identifier for export filenames */
  widgetType?: string;
  /** Dashboard name for export filenames */
  dashboardName?: string;
  /** Provide an ECharts-compatible instance for PNG export */
  getChartInstance?: (() => {
    getDataURL: (opts: {
      type: string;
      pixelRatio: number;
      backgroundColor: string;
    }) => string;
  } | null) | undefined;
  /** Provide table data for CSV export */
  getTableData?:
    | (() => { columns: string[]; rows: string[][] })
    | undefined;
  /** Provide raw data for JSON export */
  getRawData?: (() => unknown) | undefined;
  /** Whether the widget data is stale (exceeded refresh interval) */
  isStale?: boolean;
  /** Widget content */
  children: ReactNode;
}

/** Height of the persistent edit-mode action bar */
const EDIT_BAR_HEIGHT = 28;

const WIDGET_SHELL_CSS = `
@keyframes widget-toolbar-slide {
  from { opacity: 0; transform: translateY(-8px); }
  to { opacity: 1; transform: translateY(0); }
}
@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.4; }
}
.widget-shell {
  transition: border-color 0.2s ease, transform 0.3s cubic-bezier(0.34, 1.56, 0.64, 1);
}
.widget-shell:hover {
  border-color: var(--widget-shell-hover-border) !important;
}
.widget-shell.widget-shell--editing:hover {
  border-color: var(--widget-shell-edit-border) !important;
}
.widget-trigger-icon {
  opacity: 0.35;
  pointer-events: auto;
  transition: transform 0.15s ease, box-shadow 0.15s ease, opacity 0.2s ease;
}
.widget-shell:hover .widget-trigger-icon,
.widget-trigger-icon.force-visible {
  opacity: 1;
}
.widget-trigger-icon:hover {
  transform: scale(1.15);
  box-shadow: 0 2px 6px rgba(0,0,0,0.15);
}
.react-resizable-handle {
  width: 20px !important;
  height: 20px !important;
}
`;

/** Error fallback rendered inside the widget when a child throws */
function WidgetErrorFallback({
  error,
  resetErrorBoundary,
}: {
  error: Error;
  resetErrorBoundary: () => void;
}) {
  const { token } = theme.useToken();

  return (
    <div
      style={{
        padding: token.paddingMD,
        textAlign: "center",
        color: token.colorError,
      }}
    >
      <p style={{ margin: 0, fontSize: token.fontSizeSM }}>
        Something went wrong
      </p>
      <p
        style={{
          margin: `${token.paddingXXS}px 0`,
          fontSize: token.fontSizeSM,
          color: token.colorTextSecondary,
        }}
      >
        {error.message}
      </p>
      <Button size="small" type="link" onClick={resetErrorBoundary}>
        Retry
      </Button>
    </div>
  );
}

/**
 * Shell component wrapping every widget on the dashboard.
 *
 * Two distinct modes:
 * - **Edit mode** (isEditing=true): Persistent action bar with drag handle,
 *   title, and delete button. No trigger icon or floating toolbar.
 * - **View mode** (isEditing=false): Slightly visible trigger icon that opens
 *   a floating toolbar with title, collapse, and refresh actions.
 */
export function WidgetShell({
  instanceId,
  title,
  icon,
  isEditing,
  isLoading,
  error,
  onRemove,
  onRefresh,
  onConfigure,
  onFullscreen,
  widgetType,
  dashboardName,
  getChartInstance,
  getTableData,
  getRawData,
  isStale,
  children,
}: WidgetShellProps) {
  const { token } = theme.useToken();
  const [isCollapsed, setIsCollapsed] = useState(false);
  const [isToolbarOpen, setIsToolbarOpen] = useState(false);
  const [isConfirmingRemove, setIsConfirmingRemove] = useState(false);
  const { mode: interactionMode, setMode, clear } = useWidgetInteraction(instanceId);
  const toolbarRef = useRef<HTMLDivElement>(null);
  const triggerRef = useRef<HTMLButtonElement>(null);
  const deleteBtnRef = useRef<HTMLSpanElement>(null);
  const confirmTimerRef = useRef<ReturnType<typeof setTimeout>>(null);

  // Click-outside dismissal for the floating toolbar (view mode only)
  useEffect(() => {
    if (!isToolbarOpen || isEditing) return;
    const handler = (e: MouseEvent) => {
      const target = e.target as Node;
      if (
        toolbarRef.current?.contains(target) ||
        triggerRef.current?.contains(target)
      ) {
        return;
      }
      setIsToolbarOpen(false);
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, [isToolbarOpen, isEditing]);

  // Auto-reset confirm state after 3 seconds
  useEffect(() => {
    if (!isConfirmingRemove) return;
    confirmTimerRef.current = setTimeout(() => {
      setIsConfirmingRemove(false);
    }, 3000);
    return () => {
      if (confirmTimerRef.current) clearTimeout(confirmTimerRef.current);
    };
  }, [isConfirmingRemove]);

  // Click-outside cancellation for the delete confirm state
  useEffect(() => {
    if (!isConfirmingRemove) return;
    const handler = (e: MouseEvent) => {
      if (deleteBtnRef.current?.contains(e.target as Node)) return;
      setIsConfirmingRemove(false);
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, [isConfirmingRemove]);

  // Two-tap delete handler
  const handleDeleteClick = useCallback(() => {
    if (isConfirmingRemove) {
      setIsConfirmingRemove(false);
      onRemove();
    } else {
      setIsConfirmingRemove(true);
    }
  }, [isConfirmingRemove, onRemove]);

  // Build class names for the outer shell
  const shellClassName = [
    "widget-shell",
    isEditing && "widget-shell--editing",
  ]
    .filter(Boolean)
    .join(" ");

  const triggerClassName = [
    "widget-trigger-icon",
    isToolbarOpen && "force-visible",
  ]
    .filter(Boolean)
    .join(" ");

  return (
    <>
      <style>{WIDGET_SHELL_CSS}</style>
      <div
        className={shellClassName}
        style={
          {
            position: "relative",
            height: "100%",
            borderRadius: token.borderRadiusLG,
            border: isEditing
              ? `1px dashed ${token.colorPrimary}`
              : "1px solid transparent",
            overflow: "visible",
            background: token.colorBgContainer,
            "--widget-shell-hover-border": token.colorBorderSecondary,
            "--widget-shell-edit-border": token.colorPrimary,
          } as React.CSSProperties
        }
      >
        {/* ---- EDIT MODE: Persistent action bar ---- */}
        {isEditing && (
          <div
            style={{
              position: "absolute",
              top: 0,
              left: 0,
              right: 0,
              height: EDIT_BAR_HEIGHT,
              zIndex: 2,
              display: "flex",
              alignItems: "center",
              gap: token.paddingXS,
              padding: `0 ${token.paddingXS}px`,
              background: `linear-gradient(180deg, ${token.colorPrimaryBg}, ${token.colorBgContainer})`,
              borderBottom: `1px dashed ${token.colorPrimaryBorder}`,
              borderRadius: `${token.borderRadiusLG}px ${token.borderRadiusLG}px 0 0`,
            }}
          >
            {/* Move button — drag handle when active */}
            <Button
              type="text"
              size="small"
              icon={<DragOutlined />}
              className={
                interactionMode === "move" ? "react-grid-drag-handle" : undefined
              }
              onClick={() => {
                if (interactionMode === "move") {
                  clear();
                } else {
                  setMode("move");
                }
              }}
              style={{
                flexShrink: 0,
                touchAction: interactionMode === "move" ? "none" : undefined,
                cursor: interactionMode === "move" ? "grab" : "pointer",
                ...(interactionMode === "move" && {
                  background: token.colorPrimaryBg,
                }),
              }}
            />

            {/* Resize button — toggles resize handle visibility */}
            <Button
              type="text"
              size="small"
              icon={<ColumnWidthOutlined />}
              onClick={() => {
                if (interactionMode === "resize") {
                  clear();
                } else {
                  setMode("resize");
                }
              }}
              style={{
                flexShrink: 0,
                ...(interactionMode === "resize" && {
                  background: token.colorPrimaryBg,
                }),
              }}
            />

            {/* Settings button — opens config drawer */}
            {onConfigure && (
              <Button
                type="text"
                size="small"
                icon={<SettingOutlined />}
                onClick={onConfigure}
                style={{ flexShrink: 0 }}
                title="Configure widget"
              />
            )}

            {/* Title */}
            <span
              style={{
                fontSize: token.fontSizeSM,
                fontWeight: token.fontWeightSemiBold,
                color: token.colorPrimary,
                overflow: "hidden",
                textOverflow: "ellipsis",
                whiteSpace: "nowrap",
                flex: 1,
                minWidth: 0,
              }}
            >
              {title}
            </span>

            {/* Delete button — two-tap inline confirmation */}
            <span ref={deleteBtnRef}>
              <Button
                type="text"
                size="small"
                danger
                icon={<DeleteOutlined />}
                onClick={handleDeleteClick}
                style={{
                  flexShrink: 0,
                  ...(isConfirmingRemove && {
                    background: token.colorErrorBg,
                    fontWeight: token.fontWeightSemiBold,
                  }),
                }}
              >
                {isConfirmingRemove && (
                  <span style={{ fontSize: token.fontSizeXS, marginLeft: -2 }}>
                    Sure?
                  </span>
                )}
              </Button>
            </span>
          </div>
        )}

        {/* ---- VIEW MODE: Subtle title label ---- */}
        {!isEditing && !isToolbarOpen && (
          <div
            aria-hidden="true"
            style={{
              position: "absolute",
              top: 2,
              left: 8,
              zIndex: 1,
              fontSize: 11,
              color: token.colorTextTertiary,
              fontWeight: 500,
              lineHeight: 1,
              pointerEvents: "none",
              overflow: "hidden",
              textOverflow: "ellipsis",
              whiteSpace: "nowrap",
              maxWidth: "calc(100% - 60px)",
            }}
          >
            {title}
          </div>
        )}

        {/* ---- VIEW MODE: Trigger icon ---- */}
        {!isEditing && (
          <button
            ref={triggerRef}
            className={triggerClassName}
            onClick={() => setIsToolbarOpen((prev) => !prev)}
            onPointerDown={(e) => e.stopPropagation()}
            aria-label={title}
            style={{
              position: "absolute",
              top: -12,
              right: 8,
              width: 26,
              height: 26,
              borderRadius: "50%",
              background: token.colorBgElevated,
              border: `1px solid ${token.colorBorderSecondary}`,
              zIndex: 3,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              cursor: "pointer",
              padding: 0,
              boxShadow: "0 1px 3px rgba(0,0,0,0.1)",
              color: token.colorTextSecondary,
            }}
          >
            {icon ?? <EllipsisOutlined style={{ fontSize: 11 }} />}
          </button>
        )}

        {/* ---- VIEW MODE: Floating toolbar ---- */}
        {!isEditing && isToolbarOpen && (
          <div
            ref={toolbarRef}
            role="toolbar"
            aria-label={`${title} controls`}
            style={{
              position: "absolute",
              top: 0,
              right: 0,
              zIndex: 4,
              background: token.colorBgElevated,
              borderRadius: `0 0 0 ${token.borderRadiusLG}px`,
              boxShadow: token.boxShadowSecondary,
              padding: `${token.paddingXS}px ${token.paddingSM}px`,
              display: "flex",
              alignItems: "center",
              gap: token.paddingXS,
              animation: "widget-toolbar-slide 0.15s ease-out",
              maxWidth: "70%",
            }}
          >
            <span
              style={{
                display: "inline-flex",
                alignItems: "center",
                gap: token.paddingXS,
                fontSize: token.fontSizeSM,
                fontWeight: token.fontWeightSemiBold,
                whiteSpace: "nowrap",
              }}
            >
              {icon}
              <span>{title}</span>
              {isStale && (
                <span
                  style={{
                    display: "inline-block",
                    width: 6,
                    height: 6,
                    borderRadius: "50%",
                    background: token.colorWarning,
                    animation: "pulse 2s infinite",
                  }}
                />
              )}
            </span>
            <Button
              type="text"
              size="small"
              icon={isCollapsed ? <RightOutlined /> : <DownOutlined />}
              onClick={() => setIsCollapsed(!isCollapsed)}
            />
            {onFullscreen && (
              <Button
                type="text"
                size="small"
                icon={<FullscreenOutlined />}
                onClick={onFullscreen}
                title="Fullscreen"
              />
            )}
            {(widgetType || getChartInstance || getTableData || getRawData) && (
              <WidgetExportMenu
                widgetType={widgetType ?? ""}
                dashboardName={dashboardName ?? "dashboard"}
                getChartInstance={getChartInstance}
                getTableData={getTableData}
                getRawData={getRawData}
              />
            )}
            {onRefresh && (
              <Button
                type="text"
                size="small"
                icon={<ReloadOutlined />}
                onClick={onRefresh}
              />
            )}
          </div>
        )}

        {/* Content area */}
        <div
          style={{
            padding: isCollapsed ? 0 : token.paddingMD,
            paddingTop:
              isCollapsed
                ? 0
                : isEditing
                  ? EDIT_BAR_HEIGHT + token.paddingXS
                  : token.paddingMD,
            overflow: "auto",
            height: "100%",
            borderRadius: token.borderRadiusLG,
            display: "flex",
            flexDirection: "column",
          }}
        >
          {!isCollapsed && (
            <ErrorBoundary FallbackComponent={WidgetErrorFallback}>
              {isLoading ? (
                <Skeleton active paragraph={{ rows: 3 }} />
              ) : error ? (
                <div
                  style={{
                    padding: token.paddingMD,
                    textAlign: "center",
                    color: token.colorError,
                  }}
                >
                  <p style={{ margin: 0 }}>{error.message}</p>
                  {onRefresh && (
                    <Button size="small" type="link" onClick={onRefresh}>
                      Retry
                    </Button>
                  )}
                </div>
              ) : (
                children
              )}
            </ErrorBoundary>
          )}
        </div>
      </div>
    </>
  );
}
