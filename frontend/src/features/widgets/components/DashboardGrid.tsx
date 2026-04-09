import React, { useMemo, useState } from "react";
import { Button, Result, theme, Typography } from "antd";
import { LayoutOutlined, PlusOutlined, ReloadOutlined } from "@ant-design/icons";
import {
  Responsive,
  useContainerWidth,
} from "react-grid-layout";
import "react-grid-layout/css/styles.css";
import "react-resizable/css/styles.css";
import { useDashboardCompositionStore } from "@/stores/useDashboardCompositionStore";
import { useFullscreenWidgetStore } from "@/stores/useFullscreenWidgetStore";
import { getWidgetDefinition } from "@/features/widgets/registry";
import { DashboardToolbar } from "./DashboardToolbar";
import { WidgetConfigDrawer } from "./WidgetConfigDrawer";
import { WidgetPalette } from "./WidgetPalette";
import { WidgetFullscreenModal } from "./WidgetFullscreenModal";
import {
  WidgetInteractionContext,
  type InteractionMode,
} from "./WidgetInteractionContext";
import { injectWidgetMotionStyles } from "../utils/animations";
import { useUndoRedoKeyboard } from "../hooks/useUndoRedoKeyboard";
import { useResponsiveLayout } from "../hooks/useResponsiveLayout";
import { MobileWidgetSheet } from "./MobileWidgetSheet";

// Inject widget mount animation keyframes once at module load
injectWidgetMotionStyles();

const { Title, Text } = Typography;

/**
 * Error boundary for individual widgets.
 * Catches errors in widget rendering without crashing the entire dashboard.
 */
class WidgetErrorBoundary extends React.Component<
  { children: React.ReactNode; instanceId: string; onRemove: () => void },
  { hasError: boolean; error: Error | null }
> {
  constructor(props: { children: React.ReactNode; instanceId: string; onRemove: () => void }) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error) {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
    console.error(`[WidgetErrorBoundary] Widget ${this.props.instanceId} crashed:`, error, errorInfo);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div style={{ padding: 16, height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
          <Result
            status="warning"
            title="Widget Error"
            subTitle={this.state.error?.message || 'This widget failed to render'}
            extra={[
              <Button key="reload" icon={<ReloadOutlined />} onClick={() => this.setState({ hasError: false, error: null })}>
                Retry
              </Button>,
              <Button key="remove" danger onClick={this.props.onRemove}>
                Remove
              </Button>,
            ]}
          />
        </div>
      );
    }
    return this.props.children;
  }
}

const BREAKPOINTS = { lg: 1200, md: 996, sm: 768, xs: 480 };
const COLS = { lg: 12, md: 10, sm: 6, xs: 4 };
const ROW_HEIGHT = 80;
const MARGIN: [number, number] = [12, 12];
/**
 * Dashboard grid component wrapping react-grid-layout.
 *
 * Renders widget instances from the composition store on a responsive
 * 12-column grid. Each widget component manages its own WidgetShell.
 * Provides edit mode toggle, add-widget modal, and layout persistence.
 */
export function DashboardGrid({ onSave }: { onSave: () => Promise<void> }) {
  const { token } = theme.useToken();
  useUndoRedoKeyboard();
  const responsiveConfig = useResponsiveLayout();
  const { isMobile } = responsiveConfig;
  const [mobileSheetOpen, setMobileSheetOpen] = useState(false);
  const { width, containerRef, mounted } = useContainerWidth({
    initialWidth: 1200,
  });
  const isEditing = useDashboardCompositionStore((s) => s.isEditing);
  const activeDashboard = useDashboardCompositionStore(
    (s) => s.activeDashboard,
  );
  const setEditing = useDashboardCompositionStore((s) => s.setEditing);
  const removeWidget = useDashboardCompositionStore((s) => s.removeWidget);
  const selectWidget = useDashboardCompositionStore((s) => s.selectWidget);
  const updateDashboardLayout = useDashboardCompositionStore(
    (s) => s.updateDashboardLayout,
  );
  const paletteOpen = useDashboardCompositionStore((s) => s.paletteOpen);
  const setPaletteOpen = useDashboardCompositionStore((s) => s.setPaletteOpen);
  const openFullscreen = useFullscreenWidgetStore((s) => s.openFullscreen);
  const fullscreenInstanceId = useFullscreenWidgetStore(
    (s) => s.fullscreenInstanceId,
  );

  // Per-widget interaction tracking (move/resize toggle)
  const [activeInteraction, setActiveInteraction] = useState<{
    instanceId: string;
    mode: InteractionMode;
  } | null>(null);

  // Pre-compute widget definitions to avoid repeated lookups
  const widgetMeta = useMemo(() => {
    if (!activeDashboard) return new Map<string, { definition: ReturnType<typeof getWidgetDefinition> }>();

    const map = new Map<string, { definition: ReturnType<typeof getWidgetDefinition> }>();
    for (const w of activeDashboard.widgets) {
      const def = getWidgetDefinition(w.typeId);
      map.set(w.instanceId, { definition: def });
    }
    return map;
  }, [activeDashboard]);

  // Position-aware key so the layouts memo recomputes after drag/resize store updates.
  // Includes coordinates so that when updateDashboardLayout writes new positions,
  // the memo produces fresh layouts that match RGL's internal state (preventing snap-back).
  const layoutsKey = activeDashboard?.widgets.map((w) =>
    `${w.instanceId}:${w.typeId}:${w.layout.x},${w.layout.y},${w.layout.w},${w.layout.h}`,
  ).join(",") ?? "";

  const layouts = useMemo(() => {
    if (!activeDashboard) return {};
    const widgetLayouts = activeDashboard.widgets.map((w) => {
      const def = getWidgetDefinition(w.typeId);
      const isActiveWidget =
        activeInteraction?.instanceId === w.instanceId;
      return {
        i: w.instanceId,
        x: w.layout.x,
        y: w.layout.y,
        w: w.layout.w,
        h: w.layout.h,
        minW: def?.sizeConstraints.minW,
        maxW: def?.sizeConstraints.maxW,
        minH: def?.sizeConstraints.minH,
        maxH: def?.sizeConstraints.maxH,
        isDraggable: isActiveWidget && activeInteraction.mode === "move",
        isResizable: isActiveWidget && activeInteraction.mode === "resize",
      };
    });
    return {
      lg: widgetLayouts,
      md: widgetLayouts.map((l) => ({ ...l, x: l.x % 8, w: Math.min(l.w, 8) })),
      sm: widgetLayouts.map((l) => ({ ...l, x: 0, w: 1 })),
      xs: widgetLayouts.map((l) => ({ ...l, x: 0, w: 1 })),
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps -- layoutsKey is a stable primitive string
  }, [layoutsKey, activeInteraction]);

  // Context value for child widgets to read/toggle interaction mode
  const interactionContextValue = useMemo(
    () => ({
      getInteraction: (instanceId: string): InteractionMode | null => {
        if (!activeInteraction) return null;
        return activeInteraction.instanceId === instanceId
          ? activeInteraction.mode
          : null;
      },
      setInteraction: (instanceId: string, mode: InteractionMode) => {
        setActiveInteraction((prev) => {
          if (
            prev?.instanceId === instanceId &&
            prev.mode === mode
          ) {
            return null;
          }
          return { instanceId, mode };
        });
      },
      clearInteraction: () => setActiveInteraction(null),
      activeInteraction,
    }),
    [activeInteraction],
  );

  const widgets = activeDashboard?.widgets ?? [];
  const hasWidgets = widgets.length > 0;

  return (
    <WidgetInteractionContext.Provider value={interactionContextValue}>
      {/* Dashboard toolbar */}
      <DashboardToolbar onSave={onSave} />

      <div
        ref={containerRef}
        style={{
          position: "relative",
          minHeight: "100%",
          background: isEditing
            ? `radial-gradient(circle, ${token.colorBorderSecondary} 1px, transparent 1px)`
            : undefined,
          backgroundSize: isEditing ? "24px 24px" : undefined,
        }}
      >
        {/* Empty state */}
      {!hasWidgets && (
        <div
          style={{
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            justifyContent: "center",
            minHeight: 400,
            gap: token.paddingMD,
          }}
        >
          <LayoutOutlined
            style={{ fontSize: 48, color: token.colorTextQuaternary }}
          />
          <div style={{ textAlign: "center" }}>
            <Title
              level={4}
              style={{ margin: 0, color: token.colorTextSecondary }}
            >
              Build Your Dashboard
            </Title>
            <Text type="secondary" style={{ fontSize: token.fontSizeSM }}>
              Add widgets to track your project metrics at a glance
            </Text>
          </div>
          <Button
            type="primary"
            size="large"
            icon={<PlusOutlined />}
            onClick={() => {
              setEditing(true);
              setPaletteOpen(true);
            }}
          >
            Get Started
          </Button>
        </div>
      )}

      {/* Mobile: stacked layout */}
      {isMobile && hasWidgets && (
        <div style={{ display: "flex", flexDirection: "column", gap: token.paddingSM }}>
          {widgets.map((widget) => {
            const definition = getWidgetDefinition(widget.typeId);
            if (!definition) return null;
            const WidgetComponent = definition.component;
            return (
              <div key={widget.instanceId} style={{ minHeight: 200 }}>
                <WidgetErrorBoundary
                  instanceId={widget.instanceId}
                  onRemove={() => removeWidget(widget.instanceId)}
                >
                  <WidgetComponent
                    config={
                      widget.config as Parameters<typeof WidgetComponent>[0]["config"]
                    }
                    instanceId={widget.instanceId}
                    isEditing={isEditing}
                    onRemove={() => removeWidget(widget.instanceId)}
                    onConfigure={() => selectWidget(widget.instanceId)}
                    onFullscreen={() => openFullscreen(widget.instanceId)}
                    widgetType={widget.typeId as string}
                    dashboardName={activeDashboard?.name ?? "dashboard"}
                  />
                </WidgetErrorBoundary>
              </div>
            );
          })}
        </div>
      )}

      {/* Grid (non-mobile only) */}
      {!isMobile && mounted && hasWidgets && (
        <>
        {/* CSS to hide resize handles and drag cursor on non-active widgets.
            react-grid-layout's onDragStart/onResizeStart guards do NOT cancel
            the interaction, so we use CSS to visually enforce single-widget mode. */}
        <style>{`
          .react-grid-item:not(.widget-resize-active) .react-resizable-handle {
            display: none !important;
          }
          .react-grid-item:not(.widget-drag-active) {
            cursor: default !important;
          }
        `}</style>
        <Responsive
          width={width}
          breakpoints={BREAKPOINTS}
          cols={COLS}
          layouts={layouts}
          rowHeight={ROW_HEIGHT}
          margin={MARGIN}
          containerPadding={[12, 12]}
          isDraggable={false}
          isResizable={false}
          onDragStop={(layout) => {
            const items = layout.map((item) => ({
              i: item.i, x: item.x, y: item.y, w: item.w, h: item.h,
            }));
            updateDashboardLayout(items);
            setActiveInteraction(null);
          }}
          onResizeStop={(layout) => {
            const items = layout.map((item) => ({
              i: item.i, x: item.x, y: item.y, w: item.w, h: item.h,
            }));
            updateDashboardLayout(items);
            setActiveInteraction(null);
          }}
        >
          {widgets.map((widget, index) => {
            try {
              const meta = widgetMeta.get(widget.instanceId);
              const definition = meta?.definition;

              if (!definition) {
                return (
                  <div
                    key={widget.instanceId}
                    style={{
                      padding: token.paddingMD,
                      color: token.colorTextSecondary,
                      textAlign: "center",
                    }}
                  >
                    Widget type &quot;{widget.typeId}&quot; not found in registry
                  </div>
                );
              }

              const WidgetComponent = definition.component;

              return (
                <div
                    key={widget.instanceId}
                    className={[
                      "widget-enter",
                      activeInteraction?.mode === "move" && activeInteraction.instanceId === widget.instanceId ? "widget-drag-active" : "",
                      activeInteraction?.mode === "resize" && activeInteraction.instanceId === widget.instanceId ? "widget-resize-active" : "",
                    ].filter(Boolean).join(" ")}
                    style={{ "--widget-stagger-delay": `${Math.min(index * 50, 400)}ms` } as React.CSSProperties}
                  >
                  <WidgetErrorBoundary
                    instanceId={widget.instanceId}
                    onRemove={() => removeWidget(widget.instanceId)}
                  >
                    <WidgetComponent
                      config={
                        widget.config as Parameters<typeof WidgetComponent>[0]["config"]
                      }
                      instanceId={widget.instanceId}
                      isEditing={isEditing}
                      onRemove={() => removeWidget(widget.instanceId)}
                      onConfigure={() => selectWidget(widget.instanceId)}
                      onFullscreen={() => openFullscreen(widget.instanceId)}
                      widgetType={widget.typeId as string}
                      dashboardName={activeDashboard?.name ?? "dashboard"}
                    />
                  </WidgetErrorBoundary>
                </div>
              );
            } catch (error) {
              console.error(`Error rendering widget ${widget.instanceId}:`, error);
              return (
                <div
                  key={widget.instanceId}
                  style={{
                    padding: token.paddingMD,
                    color: token.colorError,
                    textAlign: "center",
                  }}
                >
                  Widget failed to load
                </div>
              );
            }
          })}
        </Responsive>
        </>
      )}

      {/* Widget catalog modal */}
      <WidgetPalette
        open={paletteOpen}
        onClose={() => setPaletteOpen(false)}
      />

      {/* Widget configuration drawer */}
      <WidgetConfigDrawer />

      {/* Fullscreen widget modal */}
      {fullscreenInstanceId &&
        activeDashboard &&
        (() => {
          const widget = activeDashboard.widgets.find(
            (w) => w.instanceId === fullscreenInstanceId,
          );
          if (!widget) return null;
          return (
            <WidgetFullscreenModal
              key={widget.instanceId}
              widget={widget}
              isEditing={isEditing}
            />
          );
        })()}

      {/* Mobile manage widgets button */}
      {isMobile && hasWidgets && (
        <div style={{ textAlign: "center", padding: token.paddingSM }}>
          <Button
            onClick={() => setMobileSheetOpen(true)}
            icon={<LayoutOutlined />}
          >
            Manage Widgets
          </Button>
        </div>
      )}

      {/* Mobile widget management sheet */}
      <MobileWidgetSheet
        open={mobileSheetOpen}
        onClose={() => setMobileSheetOpen(false)}
        widgets={widgets}
        onReorder={(fromIndex, toIndex) => {
          const reordered = [...widgets];
          const [moved] = reordered.splice(fromIndex, 1);
          reordered.splice(toIndex, 0, moved);
          updateDashboardLayout(
            reordered.map((w, i) => ({
              i: w.instanceId,
              x: 0,
              y: i,
              w: w.layout.w,
              h: w.layout.h,
            })),
          );
        }}
        onRemove={(instanceId) => removeWidget(instanceId)}
        onToggleHidden={() => {/* Hidden state managed per widget config */}}
        hiddenWidgets={new Set()}
      />
    </div>
    </WidgetInteractionContext.Provider>
  );
}
