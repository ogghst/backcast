import { Table, TableProps, Input, theme } from "antd";
import { TablePaginationConfig } from "antd/es/table";
import { FilterValue, SorterResult } from "antd/es/table/interface";
import React, { useEffect, useState } from "react";

export interface TableParams {
  pagination?: TablePaginationConfig;
  sortField?: string;
  sortOrder?: string;
  filters?: Record<string, FilterValue | null>;
  search?: string;
}

interface StandardTableProps<T> extends Omit<
  TableProps<T>,
  "pagination" | "onChange"
> {
  tableParams: TableParams;
  onChange: (
    pagination: TablePaginationConfig,
    filters: Record<string, FilterValue | null>,
    sorter: SorterResult<T> | SorterResult<T>[]
  ) => void;
  // Optional toolbar slot
  toolbar?: React.ReactNode;
  // Search props
  searchable?: boolean;
  searchPlaceholder?: string;
  onSearch?: (value: string) => void;
}

export const StandardTable = <T extends object>({
  tableParams,
  onChange,
  toolbar,
  searchable,
  searchPlaceholder,
  onSearch,
  ...props
}: StandardTableProps<T>) => {
  const { token } = theme.useToken();
  const [searchValue, setSearchValue] = useState(tableParams.search || "");

  useEffect(() => {
    // eslint-disable-next-line
    setSearchValue(tableParams.search || "");
  }, [tableParams.search]);

  useEffect(() => {
    const timer = setTimeout(() => {
      if (onSearch && searchValue !== (tableParams.search || "")) {
        onSearch(searchValue);
      }
    }, 300);
    return () => clearTimeout(timer);
  }, [searchValue, onSearch, tableParams.search]);

  const handleSearchChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setSearchValue(e.target.value);
  };

  const handleSearch = (value: string) => {
    setSearchValue(value);
    onSearch?.(value);
  };

  return (
    <div>
      {(toolbar || searchable) && (
        <div
          style={{
            marginBottom: token.marginMD,
            display: "flex",
            gap: token.marginMD,
            justifyContent: "space-between",
            alignItems: "center",
          }}
        >
          {searchable && (
            <Input.Search
              placeholder={searchPlaceholder || "Search..."}
              allowClear
              value={searchValue}
              onChange={handleSearchChange}
              onSearch={handleSearch}
              style={{ width: 300 }}
            />
          )}
          {toolbar && <div style={{ flex: 1 }}>{toolbar}</div>}
        </div>
      )}
      <Table<T>
        {...props}
        pagination={{
          ...tableParams.pagination,
          showSizeChanger: true,
          pageSizeOptions: ["10", "20", "50", "100"],
          showTotal: (total, range) =>
            `${range[0]}-${range[1]} of ${total} items`,
        }}
        onChange={onChange}
      />
    </div>
  );
};
