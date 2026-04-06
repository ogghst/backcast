import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Button, theme, Typography } from "antd";
import { LayoutOutlined, PlusOutlined } from "@ant-design/icons";
import {
  Responsive,
  useContainerWidth,
  type Layout,
} from "react-grid-layout";
import "react-grid-layout/css/styles.css";
import "react-resizable/css/styles.css";
import { useDashboardCompositionStore } from "@/stores/useDashboardCompositionStore";
import { getWidgetDefinition } from "@/features/widgets/registry";
import { DashboardToolbar } from "./DashboardToolbar";
import { WidgetConfigDrawer } from "./WidgetConfigDrawer";
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
export function DashboardGrid({ onSave }: { onSave: () => Promise<void> }) {
  const { token } = theme.useToken();
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

  // Cleanup debounce timer on unmount
  useEffect(() => {
    return () => {
      if (debounceRef.current) {
        clearTimeout(debounceRef.current);
      }
    };
  }, []);

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

  // Pre-compute widget definitions to avoid repeated lookups
  const widgetMeta = useMemo(() => {
    if (!activeDashboard) return new Map<string, { layout: Layout; definition: ReturnType<typeof getWidgetDefinition> }>();

    const map = new Map<string, { layout: Layout; definition: ReturnType<typeof getWidgetDefinition> }>();
    for (const w of activeDashboard.widgets) {
      const def = getWidgetDefinition(w.typeId);
      map.set(w.instanceId, {
        layout: {
          i: w.instanceId,
          x: w.layout.x,
          y: w.layout.y,
          w: w.layout.w,
          h: w.layout.h,
          minW: def?.sizeConstraints.minW,
          maxW: def?.sizeConstraints.maxW,
          minH: def?.sizeConstraints.minH,
          maxH: def?.sizeConstraints.maxH,
          isDraggable: !!(
            activeInteraction?.instanceId === w.instanceId &&
            activeInteraction.mode === "move"
          ),
          isResizable: !!(
            activeInteraction?.instanceId === w.instanceId &&
            activeInteraction.mode === "resize"
          ),
        },
        definition: def,
      });
    }
    return map;
  }, [activeDashboard, activeInteraction]);

  const layouts = useMemo(() => ({
    lg: activeDashboard ? Array.from(widgetMeta.values()).map(m => m.layout) : [],
  }), [widgetMeta, activeDashboard]);

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
          padding: token.paddingSM,
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
          onDragStop={(layout) => {
            const items = layout.map((item) => ({
              i: item.i, x: item.x, y: item.y, w: item.w, h: item.h,
            }));
            updateDashboardLayout(items);
            clearActiveInteraction();
          }}
          onResizeStop={(layout) => {
            const items = layout.map((item) => ({
              i: item.i, x: item.x, y: item.y, w: item.w, h: item.h,
            }));
            updateDashboardLayout(items);
            clearActiveInteraction();
          }}
          draggableHandle=".react-grid-drag-handle"
        >
          {widgets.map((widget) => {
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
              <div key={widget.instanceId}>
                <WidgetComponent
                  config={
                    widget.config as Parameters<typeof WidgetComponent>[0]["config"]
                  }
                  instanceId={widget.instanceId}
                  isEditing={isEditing}
                  onRemove={() => removeWidget(widget.instanceId)}
                  onConfigure={() => selectWidget(widget.instanceId)}
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

      {/* Widget configuration drawer */}
      <WidgetConfigDrawer />
    </div>
    </WidgetInteractionContext.Provider>
  );
}
