import React, { useCallback, useMemo, useState } from "react";
import { Input, Modal, Tag, theme } from "antd";
import { PlusOutlined } from "@ant-design/icons";
import { useDashboardCompositionStore } from "@/stores/useDashboardCompositionStore";
import { useAuthStore } from "@/stores/useAuthStore";
import { getAllWidgetDefinitions } from "@/features/widgets/registry";
import type { WidgetCategory, WidgetDefinition } from "@/features/widgets/types";
import type { DashboardScope } from "../context/DashboardContextBus";
import { isWidgetInScope, isWidgetPermitted } from "../utils/widgetPermissions";

/**
 * CSS class for widget palette items.
 * Uses pure CSS :hover instead of React state to avoid re-renders during
 * touch sequences on mobile devices.
 */
const PALETTE_ITEM_CLASS = "widget-palette-item";

const CATEGORY_LABELS: Record<WidgetCategory, string> = {
  summary: "Summary",
  trend: "Trends & Charts",
  diagnostic: "Diagnostics",
  breakdown: "Breakdowns",
  action: "Actions",
  schedule: "Schedule",
  settings: "Settings",
};

const CATEGORY_ORDER: WidgetCategory[] = [
  "summary",
  "trend",
  "diagnostic",
  "breakdown",
  "action",
  "schedule",
  "settings",
];

export interface WidgetPaletteProps {
  /** Whether the modal is open */
  open: boolean;
  /** Called when the modal should close */
  onClose: () => void;
  /**
   * Dashboard scope the palette is filtering for. Widgets whose scope does
   * not match (e.g. a portfolio widget on a project dashboard) are hidden.
   * Defaults to `"project"` — preserving the pre-Phase-5 project-dashboard
   * palette verbatim (legacy widgets with no scope set default to project).
   */
  scope?: DashboardScope;
}

/**
 * Modal-based widget catalog for adding widgets to the dashboard.
 *
 * Opens as an Ant Design Modal (no blocking overlay mask on the grid).
 * Shows all registered widgets grouped by category with search filtering.
 * Closes after each widget is added.
 *
 * Widgets are filtered by **scope + permission** (D2 / G19): a project
 * dashboard only offers project widgets a user is permitted to use, a
 * portfolio dashboard only portfolio widgets. The scope+permission filter
 * runs inside the same `useMemo` pass as the registry enumeration so the
 * fresh array returned by `getAllWidgetDefinitions()` is not re-filtered on
 * every render.
 */
export function WidgetPalette({ open, onClose, scope = "project" }: WidgetPaletteProps) {
  const { token } = theme.useToken();
  const [search, setSearch] = useState("");

  const addWidget = useDashboardCompositionStore((s) => s.addWidget);
  const hasPermission = useAuthStore((s) => s.hasPermission);
  const hasAllPermissions = useAuthStore((s) => s.hasAllPermissions);

  // One memo pass: enumerate the registry, then keep only in-scope + permitted
  // widgets. Runs the text search over THAT list so neither the registry
  // enumeration nor the permission check repeats on unrelated re-renders.
  const filteredBySearch = useMemo(() => {
    const visible = getAllWidgetDefinitions().filter(
      (def) =>
        isWidgetInScope(def, scope) &&
        isWidgetPermitted(def, hasPermission, hasAllPermissions),
    );
    if (!search.trim()) return visible;
    const lower = search.toLowerCase();
    return visible.filter(
      (def) =>
        def.displayName.toLowerCase().includes(lower) ||
        def.description.toLowerCase().includes(lower),
    );
  }, [scope, hasPermission, hasAllPermissions, search]);

  const groupedByCategory = useMemo(() => {
    const groups: Array<{
      category: WidgetCategory;
      label: string;
      widgets: WidgetDefinition[];
    }> = [];

    for (const category of CATEGORY_ORDER) {
      const categoryWidgets = filteredBySearch.filter(
        (def) => def.category === category,
      );
      if (categoryWidgets.length > 0) {
        groups.push({
          category,
          label: CATEGORY_LABELS[category],
          widgets: categoryWidgets,
        });
      }
    }

    const covered = new Set(CATEGORY_ORDER);
    for (const def of filteredBySearch) {
      if (!covered.has(def.category)) {
        const existing = groups.find((g) => g.category === def.category);
        if (!existing) {
          const categoryWidgets = filteredBySearch.filter(
            (d) => d.category === def.category,
          );
          groups.push({
            category: def.category,
            label: def.category,
            widgets: categoryWidgets,
          });
        }
      }
    }

    return groups;
  }, [filteredBySearch]);

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent, typeId: Parameters<typeof addWidget>[0]) => {
      if (e.key === "Enter" || e.key === " ") {
        e.preventDefault();
        addWidget(typeId);
        onClose();
      }
    },
    [addWidget, onClose],
  );

  return (
    <Modal
      title="Widget Catalog"
      open={open}
      onCancel={onClose}
      footer={null}
      width={520}
      destroyOnHidden
    >
      <style>{`
        .${PALETTE_ITEM_CLASS}:hover {
          background: ${token.colorFillQuaternary} !important;
        }
      `}</style>

      <Input.Search
        placeholder="Search widgets..."
        value={search}
        onChange={(e) => setSearch(e.target.value)}
        allowClear
        style={{ marginBottom: token.paddingMD }}
      />

      <div style={{ maxHeight: "60vh", overflow: "auto" }}>
        {groupedByCategory.length === 0 && (
          <div
            style={{
              textAlign: "center",
              color: token.colorTextTertiary,
              padding: `${token.paddingXL}px ${token.paddingMD}px`,
            }}
          >
            No widgets available for your role
          </div>
        )}
        {groupedByCategory.map((group) => (
          <div key={group.category} style={{ marginBottom: token.paddingMD }}>
            <div
              style={{
                fontSize: token.fontSizeSM,
                fontWeight: 600,
                color: token.colorTextSecondary,
                marginBottom: token.paddingXS,
                textTransform: "uppercase",
                letterSpacing: "0.5px",
              }}
            >
              {group.label}
            </div>
            {group.widgets.map((def) => (
              <button
                key={def.typeId}
                type="button"
                className={PALETTE_ITEM_CLASS}
                onClick={() => {
                  addWidget(def.typeId);
                  onClose();
                }}
                onKeyDown={(e) => handleKeyDown(e, def.typeId)}
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: token.paddingSM,
                  padding: `${token.paddingSM}px`,
                  minHeight: 44,
                  cursor: "pointer",
                  borderRadius: token.borderRadiusSM,
                  WebkitTapHighlightColor: "transparent",
                  userSelect: "none",
                  touchAction: "manipulation",
                  background: "transparent",
                  transition: "background 0.15s ease",
                  border: "none",
                  outline: "none",
                  width: "100%",
                  textAlign: "left",
                  fontFamily: "inherit",
                  fontSize: "inherit",
                  lineHeight: "inherit",
                  color: "inherit",
                }}
              >
                <span style={{ fontSize: 18, flexShrink: 0 }}>
                  {def.icon}
                </span>
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{ fontSize: token.fontSizeSM }}>
                    {def.displayName}
                  </div>
                  <div
                    style={{
                      fontSize: token.fontSizeSM,
                      color: token.colorTextSecondary,
                      whiteSpace: "nowrap",
                      overflow: "hidden",
                      textOverflow: "ellipsis",
                    }}
                  >
                    {def.description}
                  </div>
                </div>
                <Tag style={{ margin: 0, flexShrink: 0 }}>{`${def.sizeConstraints.defaultW}x${def.sizeConstraints.defaultH}`}</Tag>
                <PlusOutlined
                  style={{
                    fontSize: 16,
                    color: token.colorTextSecondary,
                    flexShrink: 0,
                  }}
                />
              </button>
            ))}
          </div>
        ))}
      </div>
    </Modal>
  );
}
