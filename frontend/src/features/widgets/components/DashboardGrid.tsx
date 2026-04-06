import { useCallback, useMemo, useRef, useState } from "react";
import { Button, message, theme, Typography } from "antd";
import {
  CheckOutlined,
  EditOutlined,
  LayoutOutlined,
  PlusOutlined,
} from "@ant-design/icons";
import {
  Responsive,
  useContainerWidth,
  type Layout,
} from "react-grid-layout";
import "react-grid-layout/css/styles.css";
import "react-resizable/css/styles.css";
import { useDashboardCompositionStore } from "@/stores/useDashboardCompositionStore";
import { getWidgetDefinition } from "@/features/widgets/registry";
import { WidgetPalette } from "./WidgetPalette";
import {
  WidgetInteractionContext,
  type InteractionMode,
} from "./WidgetInteractionContext";

const { Title, Text } = Typography;

const BREAKPOINTS = { lg: 1200, md: 996, sm: 768, xs: 480 };
const COLS = { lg: 12, md: 10, sm: 6, xs: 4 };
const ROW_HEIGHT = 80;
const MARGIN: [number, number] = [12, 12];
const LAYOUT_DEBOUNCE_MS = 150;

/**
 * Dashboard grid component wrapping react-grid-layout.
 *
 * Renders widget instances from the composition store on a responsive
 * 12-column grid. Each widget component manages its own WidgetShell.
 * Provides edit mode toggle, add-widget modal, and debounced layout
 * persistence.
 */
export function DashboardGrid() {
  const { token } = theme.useToken();
  const { width, containerRef, mounted } = useContainerWidth({
    initialWidth: 1200,
  });
  const [paletteOpen, setPaletteOpen] = useState(false);

  const isEditing = useDashboardCompositionStore((s) => s.isEditing);
  const activeDashboard = useDashboardCompositionStore(
    (s) => s.activeDashboard,
  );
  const setEditing = useDashboardCompositionStore((s) => s.setEditing);
  const removeWidget = useDashboardCompositionStore((s) => s.removeWidget);
  const updateDashboardLayout = useDashboardCompositionStore(
    (s) => s.updateDashboardLayout,
  );

  // Per-widget interaction tracking (move/resize toggle)
  const [activeInteraction, setActiveInteraction] = useState<{
    instanceId: string;
    mode: InteractionMode;
  } | null>(null);

  const clearActiveInteraction = useCallback(() => {
    setActiveInteraction(null);
  }, []);

  // Debounced layout change handler
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const handleLayoutChange = useCallback(
    (layout: Layout) => {
      if (debounceRef.current) {
        clearTimeout(debounceRef.current);
      }
      debounceRef.current = setTimeout(() => {
        const items = layout.map((item) => ({
          i: item.i,
          x: item.x,
          y: item.y,
          w: item.w,
          h: item.h,
        }));
        updateDashboardLayout(items);
      }, LAYOUT_DEBOUNCE_MS);
    },
    [updateDashboardLayout],
  );

  // Convert widget instances to react-grid-layout format
  const layouts = useMemo(() => {
    if (!activeDashboard) return { lg: [] as Layout[] };

    const lgLayout: Layout = activeDashboard.widgets.map((w) => ({
      i: w.instanceId,
      x: w.layout.x,
      y: w.layout.y,
      w: w.layout.w,
      h: w.layout.h,
      minW: getWidgetDefinition(w.typeId)?.sizeConstraints.minW,
      maxW: getWidgetDefinition(w.typeId)?.sizeConstraints.maxW,
      minH: getWidgetDefinition(w.typeId)?.sizeConstraints.minH,
      maxH: getWidgetDefinition(w.typeId)?.sizeConstraints.maxH,
      isDraggable: !!(
        activeInteraction?.instanceId === w.instanceId &&
        activeInteraction.mode === "move"
      ),
      isResizable: !!(
        activeInteraction?.instanceId === w.instanceId &&
        activeInteraction.mode === "resize"
      ),
    }));

    return { lg: lgLayout };
  }, [activeDashboard, activeInteraction]);

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
    <div
      ref={containerRef}
      style={{
        position: "relative",
        minHeight: "100%",
        background: isEditing
          ? `radial-gradient(circle, ${token.colorBorderSecondary} 1px, transparent 1px)`
          : undefined,
        backgroundSize: isEditing ? "24px 24px" : undefined,
        padding: token.paddingSM,
      }}
    >
      {/* Toolbar */}
      <div
        style={{
          position: "absolute",
          top: token.paddingSM,
          right: token.paddingSM,
          zIndex: 10,
          display: "flex",
          gap: token.paddingXS,
        }}
      >
        {isEditing && (
          <Button
            icon={<PlusOutlined />}
            onClick={() => setPaletteOpen(true)}
          >
            Add
          </Button>
        )}
        <Button
          type={isEditing ? "primary" : "default"}
          icon={isEditing ? <CheckOutlined /> : <EditOutlined />}
          onClick={() => {
            if (isEditing) {
              setActiveInteraction(null);
              message.success("Layout saved");
            }
            setEditing(!isEditing);
          }}
        >
          {isEditing ? "Done" : "Customize"}
        </Button>
      </div>

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

      {/* Grid */}
      {mounted && hasWidgets && (
        <Responsive
          width={width}
          breakpoints={BREAKPOINTS}
          cols={COLS}
          layouts={layouts}
          rowHeight={ROW_HEIGHT}
          margin={MARGIN}
          isDraggable={false}
          isResizable={false}
          onLayoutChange={handleLayoutChange}
          onDragStop={clearActiveInteraction}
          onResizeStop={clearActiveInteraction}
          draggableHandle=".react-grid-drag-handle"
        >
          {widgets.map((widget) => {
            const definition = getWidgetDefinition(widget.typeId);

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
              <div key={widget.instanceId}>
                <WidgetComponent
                  config={
                    widget.config as Parameters<typeof WidgetComponent>[0]["config"]
                  }
                  instanceId={widget.instanceId}
                  isEditing={isEditing}
                  onRemove={() => removeWidget(widget.instanceId)}
                />
              </div>
            );
          })}
        </Responsive>
      )}

      {/* Widget catalog modal */}
      <WidgetPalette
        open={paletteOpen}
        onClose={() => setPaletteOpen(false)}
      />
    </div>
    </WidgetInteractionContext.Provider>
  );
}
