import { Table, TableProps } from "antd";
import { TablePaginationConfig } from "antd/es/table";
import { FilterValue, SorterResult } from "antd/es/table/interface";
import React from "react";

export interface TableParams {
  pagination?: TablePaginationConfig;
  sortField?: string;
  sortOrder?: string;
  filters?: Record<string, FilterValue | null>;
}

interface StandardTableProps<T> extends Omit<
  TableProps<T>,
  "pagination" | "onChange"
> {
  tableParams: TableParams;
  onChange: (
    pagination: TablePaginationConfig,
    filters: Record<string, FilterValue | null>,
    sorter: SorterResult<T> | SorterResult<T>[],
  ) => void;
  // Optional toolbar slot
  toolbar?: React.ReactNode;
}

export const StandardTable = <T extends object>({
  tableParams,
  onChange,
  toolbar,
  ...props
}: StandardTableProps<T>) => {
  return (
    <div>
      {toolbar && <div style={{ marginBottom: 16 }}>{toolbar}</div>}
      <Table<T>
        {...props}
        pagination={tableParams.pagination}
        onChange={onChange}
      />
    </div>
  );
};
