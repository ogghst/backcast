import React, { useCallback, useMemo, useState } from "react";
import { Input, Modal, Tag, theme } from "antd";
import { PlusOutlined } from "@ant-design/icons";
import { useDashboardCompositionStore } from "@/stores/useDashboardCompositionStore";
import { getAllWidgetDefinitions } from "@/features/widgets/registry";
import type { WidgetCategory, WidgetDefinition } from "@/features/widgets/types";

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
};

const CATEGORY_ORDER: WidgetCategory[] = [
  "summary",
  "trend",
  "diagnostic",
  "breakdown",
  "action",
];

export interface WidgetPaletteProps {
  /** Whether the modal is open */
  open: boolean;
  /** Called when the modal should close */
  onClose: () => void;
}

/**
 * Modal-based widget catalog for adding widgets to the dashboard.
 *
 * Opens as an Ant Design Modal (no blocking overlay mask on the grid).
 * Shows all registered widgets grouped by category with search filtering.
 * Closes after each widget is added.
 */
export function WidgetPalette({ open, onClose }: WidgetPaletteProps) {
  const { token } = theme.useToken();
  const [search, setSearch] = useState("");

  const addWidget = useDashboardCompositionStore((s) => s.addWidget);

  const allDefinitions = getAllWidgetDefinitions();

  const filteredBySearch = useMemo(() => {
    if (!search.trim()) return allDefinitions;
    const lower = search.toLowerCase();
    return allDefinitions.filter(
      (def) =>
        def.displayName.toLowerCase().includes(lower) ||
        def.description.toLowerCase().includes(lower),
    );
  }, [allDefinitions, search]);

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
      destroyOnClose
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
        {groupedByCategory.map((group) => (
          <div key={group.category} style={{ marginBottom: token.paddingMD }}>
            <div
              style={{
                fontSize: token.fontSizeXS,
                fontWeight: token.fontWeightSemiBold,
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
                      fontSize: token.fontSizeXS,
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
