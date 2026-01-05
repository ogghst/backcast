import { TablePaginationConfig } from "antd/es/table";
import { FilterValue, SorterResult } from "antd/es/table/interface";
import { useSearchParams } from "react-router-dom";

interface TableParams {
  pagination?: TablePaginationConfig;
  sortField?: string;
  sortOrder?: string;
  filters?: Record<string, FilterValue | null>;
}

export const useTableParams = <
  T extends object = Record<string, unknown>,
>() => {
  const [searchParams, setSearchParams] = useSearchParams();

  // Parse initial state from URL
  const current = parseInt(searchParams.get("page") || "1");
  const pageSize = parseInt(searchParams.get("per_page") || "10");

  const tableParams: TableParams = {
    pagination: {
      current,
      pageSize,
    },
  };

  const handleTableChange = (
    pagination: TablePaginationConfig,
    filters: Record<string, FilterValue | null>,
    sorter: SorterResult<T> | SorterResult<T>[],
  ) => {
    const newParams = new URLSearchParams(searchParams);

    // Update pagination
    if (pagination.current) {
      newParams.set("page", pagination.current.toString());
    }
    if (pagination.pageSize) {
      newParams.set("per_page", pagination.pageSize.toString());
    }

    // Update Sorter (Single sorter support for now)
    if (!Array.isArray(sorter) && sorter.field && sorter.order) {
      newParams.set("sort_field", sorter.field as string);
      newParams.set("sort_order", sorter.order);
    } else {
      newParams.delete("sort_field");
      newParams.delete("sort_order");
    }

    // Update Filters (Optional: simplistic serialization)
    // For now we just sync pagination/sort as MVP

    setSearchParams(newParams);
  };

  return {
    tableParams,
    handleTableChange,
  };
};
