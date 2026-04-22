import { Empty, Input, Pagination, Select, Spin, Table, Grid, theme } from "antd";
import type { ColumnType } from "antd/es/table";
import {
  SortAscendingOutlined,
  SortDescendingOutlined,
} from "@ant-design/icons";
import React, { useCallback, useEffect, useRef, useState } from "react";
import type { ViewMode } from "@/hooks/useViewMode";

export interface SortOption {
  /** Display label: "Name", "Budget", "Code" */
  label: string;
  /** API field name: "name", "budget_allocation", "code" */
  value: string;
}

interface EntityGridProps<T> {
  /** Array of entity items to display */
  items: T[];
  /** Total count for pagination */
  total: number;
  /** Loading state */
  loading: boolean;

  /** Render function for each card */
  renderCard: (item: T) => React.ReactNode;
  /** Extract unique key from item */
  keyExtractor: (item: T) => string;

  /** Toolbar title node (icon + text) */
  title: React.ReactNode;
  /** Slot for the "Add" button */
  addContent?: React.ReactNode;

  /** Current search value */
  searchValue: string;
  /** Search change handler */
  onSearch: (value: string) => void;
  /** Placeholder for search input */
  searchPlaceholder?: string;

  /** Available sort options */
  sortOptions: SortOption[];
  /** Currently active sort field */
  sortField?: string;
  /** Currently active sort order */
  sortOrder?: string;
  /** Handler when sort changes */
  onSortChange: (field: string, order: "ascend" | "descend") => void;

  /** Slot for entity-specific filter controls */
  filters?: React.ReactNode;

  /** Pagination state */
  pagination: {
    current: number;
    pageSize: number;
  };
  /** Pagination change handler */
  onPageChange: (page: number, pageSize: number) => void;

  /** Minimum card width for CSS grid (default: 300) */
  minCardWidth?: number;

  /** Layout variant: "table" | "card" | "auto" (default: "card") */
  variant?: ViewMode;

  /** Table columns — required when variant resolves to "table" */
  columns?: ColumnType<T>[];

  /** Row click handler — makes table rows clickable */
  onRowClick?: (item: T) => void;
}

export const EntityGrid = <T,>({
  items,
  total,
  loading,
  renderCard,
  keyExtractor,
  title,
  addContent,
  searchValue,
  onSearch,
  searchPlaceholder,
  sortOptions,
  sortField,
  sortOrder,
  onSortChange,
  filters,
  pagination,
  onPageChange,
  minCardWidth = 300,
  variant = "card",
  columns,
  onRowClick,
}: EntityGridProps<T>) => {
  const { token } = theme.useToken();
  const screens = Grid.useBreakpoint();
  const isMobile = !screens.md;

  const useTable = variant === "table" || (variant === "auto" && !isMobile);

  const [localSearch, setLocalSearch] = useState(searchValue);
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    setLocalSearch(searchValue);
  }, [searchValue]);

  useEffect(() => {
    return () => {
      if (debounceRef.current) clearTimeout(debounceRef.current);
    };
  }, []);

  const handleSearchInput = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const val = e.target.value;
      setLocalSearch(val);
      if (debounceRef.current) clearTimeout(debounceRef.current);
      debounceRef.current = setTimeout(() => onSearch(val), 300);
    },
    [onSearch],
  );

  const handleSearchSubmit = useCallback(
    (val: string) => {
      setLocalSearch(val);
      if (debounceRef.current) clearTimeout(debounceRef.current);
      onSearch(val);
    },
    [onSearch],
  );

  const handleSortFieldChange = useCallback(
    (field: string) => {
      onSortChange(field, (sortOrder as "ascend" | "descend") || "ascend");
    },
    [onSortChange, sortOrder],
  );

  const toggleSortOrder = useCallback(() => {
    if (sortField) {
      const next =
        sortOrder === "ascend" || !sortOrder ? "descend" : "ascend";
      onSortChange(sortField, next);
    }
  }, [onSortChange, sortField, sortOrder]);

  const controlsRow = (
    <div
      style={{
        display: "flex",
        gap: token.marginSM,
        alignItems: "center",
        marginBottom: token.marginMD,
        flexWrap: "wrap",
      }}
    >
      <Input.Search
        placeholder={searchPlaceholder || "Search..."}
        allowClear
        value={localSearch}
        onChange={handleSearchInput}
        onSearch={handleSearchSubmit}
        style={{ width: 260 }}
      />

      <Select
        value={sortField}
        onChange={handleSortFieldChange}
        placeholder="Sort by"
        style={{ minWidth: 140 }}
        options={sortOptions.map((opt) => ({
          label: opt.label,
          value: opt.value,
        }))}
      />

      <span
        onClick={sortField ? toggleSortOrder : undefined}
        style={{
          cursor: sortField ? "pointer" : "default",
          display: "inline-flex",
          alignItems: "center",
          color: sortField ? token.colorPrimary : token.colorTextTertiary,
          fontSize: token.fontSizeLG,
        }}
      >
        {sortOrder === "descend" ? (
          <SortDescendingOutlined />
        ) : (
          <SortAscendingOutlined />
        )}
      </span>

      {filters}
    </div>
  );

  const titleBar = (
    <div
      style={{
        display: "flex",
        justifyContent: "space-between",
        alignItems: "center",
        marginBottom: token.marginMD,
      }}
    >
      <div
        style={{
          fontSize: token.fontSizeXL,
          fontWeight: token.fontWeightSemiBold ?? 600,
          color: token.colorText,
          display: "flex",
          alignItems: "center",
          gap: token.marginSM,
        }}
      >
        {title}
      </div>
      {addContent}
    </div>
  );

  const showPagination = total > pagination.pageSize;

  if (useTable) {
    return (
      <div>
        {titleBar}
        {controlsRow}
        <Table
          dataSource={items}
          columns={columns || []}
          rowKey={keyExtractor}
          loading={loading}
          scroll={{ x: isMobile ? 500 : undefined }}
          onRow={
            onRowClick
              ? (record) => ({
                  onClick: () => onRowClick(record),
                  style: { cursor: "pointer" },
                })
              : undefined
          }
          pagination={{
            current: pagination.current,
            pageSize: pagination.pageSize,
            total,
            onChange: onPageChange,
            showSizeChanger: true,
            showTotal: (t) => `Total ${t} items`,
            position: ["bottomRight"] as ["bottomRight"],
          }}
        />
      </div>
    );
  }

  return (
    <div>
      {titleBar}
      {controlsRow}
      {loading ? (
        <div
          style={{
            display: "flex",
            justifyContent: "center",
            alignItems: "center",
            minHeight: 200,
          }}
        >
          <Spin />
        </div>
      ) : items.length === 0 ? (
        <Empty description="No items found" />
      ) : (
        <div
          style={{
            display: "grid",
            gridTemplateColumns: `repeat(auto-fill, minmax(${minCardWidth}px, 1fr))`,
            gap: token.marginMD,
            alignItems: "stretch",
          }}
        >
          {items.map((item) => (
            <React.Fragment key={keyExtractor(item)}>
              {renderCard(item)}
            </React.Fragment>
          ))}
        </div>
      )}

      {showPagination && (
        <div
          style={{
            display: "flex",
            justifyContent: "center",
            marginTop: token.marginLG,
          }}
        >
          <Pagination
            current={pagination.current}
            pageSize={pagination.pageSize}
            total={total}
            onChange={onPageChange}
            showSizeChanger={false}
            size="small"
          />
        </div>
      )}
    </div>
  );
};
