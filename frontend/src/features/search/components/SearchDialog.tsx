import React, { useState, useCallback, useEffect, useRef, useMemo } from "react";
import { Modal, Input, List, Tag, Typography, Space, Spin, theme } from "antd";
import { SearchOutlined } from "@ant-design/icons";
import { useNavigate } from "react-router-dom";
import { useGlobalSearch } from "../api/useGlobalSearch";
import type { SearchResultItem, EntityType } from "../types";

const ENTITY_COLORS: Record<EntityType, string> = {
  project: "blue",
  wbe: "green",
  cost_element: "orange",
  schedule_baseline: "cyan",
  change_order: "red",
  cost_registration: "gold",
  forecast: "purple",
  quality_event: "magenta",
  progress_entry: "geekblue",
  user: "volcano",
  department: "lime",
  cost_element_type: "turquoise",
};

const ENTITY_LABELS: Record<EntityType, string> = {
  project: "Project",
  wbe: "WBE",
  cost_element: "Cost Element",
  schedule_baseline: "Schedule Baseline",
  change_order: "Change Order",
  cost_registration: "Cost Registration",
  forecast: "Forecast",
  quality_event: "Quality Event",
  progress_entry: "Progress Entry",
  user: "User",
  department: "Department",
  cost_element_type: "Cost Element Type",
};

function getEntityRoute(result: SearchResultItem): string {
  switch (result.entity_type) {
    case "project":
      return `/projects/${result.root_id}`;
    case "wbe":
      return result.project_id
        ? `/projects/${result.project_id}/wbes/${result.root_id}`
        : "/";
    case "cost_element":
      return result.wbe_id && result.project_id
        ? `/projects/${result.project_id}/wbes/${result.wbe_id}`
        : "/";
    case "change_order":
      return result.project_id
        ? `/projects/${result.project_id}/change-orders/${result.root_id}`
        : "/";
    case "user":
      return "/admin/users";
    case "department":
      return "/admin/departments";
    case "cost_element_type":
      return "/admin/cost-element-types";
    default:
      return "/";
  }
}

function getResultTitle(result: SearchResultItem): string {
  const parts: string[] = [];
  if (result.code) parts.push(result.code);
  if (result.name) parts.push(result.name);
  return parts.join(" - ") || "Untitled";
}

interface SearchDialogProps {
  open: boolean;
  onClose: () => void;
}

export const SearchDialog: React.FC<SearchDialogProps> = ({
  open,
  onClose,
}) => {
  const [query, setQuery] = useState("");
  const [debouncedQuery, setDebouncedQuery] = useState("");
  const [selectedIndex, setSelectedIndex] = useState(-1);
  const inputRef = useRef<HTMLInputElement>(null);
  const navigate = useNavigate();
  const { token } = theme.useToken();

  // Debounce input by 300ms; component is re-mounted on each open (destroyOnClose)
  useEffect(() => {
    if (!open) return;

    const timer = setTimeout(() => {
      setDebouncedQuery(query);
      setSelectedIndex(-1);
    }, 300);
    return () => clearTimeout(timer);
  }, [query, open]);

  const { data, isLoading } = useGlobalSearch({ q: debouncedQuery });
  const results = useMemo(() => data?.results ?? [], [data?.results]);

  const handleSelect = useCallback(
    (result: SearchResultItem) => {
      const route = getEntityRoute(result);
      navigate(route);
      onClose();
    },
    [navigate, onClose],
  );

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key === "ArrowDown") {
        e.preventDefault();
        setSelectedIndex((prev) =>
          prev < results.length - 1 ? prev + 1 : prev,
        );
      } else if (e.key === "ArrowUp") {
        e.preventDefault();
        setSelectedIndex((prev) => (prev > 0 ? prev - 1 : prev));
      } else if (e.key === "Enter" && selectedIndex >= 0 && results[selectedIndex]) {
        e.preventDefault();
        handleSelect(results[selectedIndex]);
      }
    },
    [results, selectedIndex, handleSelect],
  );

  // Auto-focus input when modal opens
  useEffect(() => {
    if (open) {
      setTimeout(() => inputRef.current?.focus(), 100);
    }
  }, [open]);

  return (
    <Modal
      open={open}
      onCancel={onClose}
      footer={null}
      title={null}
      closable={false}
      width={560}
      styles={{
        body: { padding: 0 },
        content: { top: 80 },
      }}
      destroyOnClose
    >
      <div style={{ padding: `${token.paddingMD}px ${token.paddingLG}px` }}>
        <Input
          ref={inputRef as React.Ref<HTMLInputElement>}
          placeholder="Search entities..."
          prefix={<SearchOutlined />}
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={handleKeyDown}
          size="large"
          allowClear
        />
      </div>

      {isLoading && (
        <div
          style={{
            textAlign: "center",
            padding: token.paddingLG,
          }}
        >
          <Spin />
        </div>
      )}

      {!isLoading && debouncedQuery.length >= 1 && results.length === 0 && (
        <div
          style={{
            textAlign: "center",
            padding: token.paddingLG,
            color: token.colorTextSecondary,
          }}
        >
          <Typography.Text type="secondary">
            No results found for &quot;{debouncedQuery}&quot;
          </Typography.Text>
        </div>
      )}

      {results.length > 0 && (
        <List
          style={{ maxHeight: 400, overflowY: "auto" }}
          dataSource={results}
          footer={
            data?.total !== undefined ? (
              <div
                style={{
                  textAlign: "center",
                  padding: token.paddingXS,
                  color: token.colorTextSecondary,
                  fontSize: token.fontSizeSM,
                }}
              >
                {results.length} of {data.total} results
              </div>
            ) : null
          }
          renderItem={(item, index) => (
            <List.Item
              onClick={() => handleSelect(item)}
              style={{
                padding: `${token.paddingSM}px ${token.paddingLG}px`,
                cursor: "pointer",
                background:
                  index === selectedIndex
                    ? token.colorPrimaryBg
                    : "transparent",
                transition: "background 0.15s",
              }}
              onMouseEnter={() => setSelectedIndex(index)}
              onMouseLeave={() => setSelectedIndex(-1)}
            >
              <List.Item.Meta
                title={
                  <Space size="small">
                    <Tag color={ENTITY_COLORS[item.entity_type]}>
                      {ENTITY_LABELS[item.entity_type]}
                    </Tag>
                    <span>{getResultTitle(item)}</span>
                    {item.status && (
                      <Typography.Text
                        type="secondary"
                        style={{ fontSize: token.fontSizeSM }}
                      >
                        ({item.status})
                      </Typography.Text>
                    )}
                  </Space>
                }
                description={
                  item.description ? (
                    <Typography.Text
                      type="secondary"
                      ellipsis
                      style={{ maxWidth: 480 }}
                    >
                      {item.description}
                    </Typography.Text>
                  ) : undefined
                }
              />
            </List.Item>
          )}
        />
      )}
    </Modal>
  );
};
