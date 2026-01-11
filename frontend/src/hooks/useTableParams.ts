import { TablePaginationConfig } from "antd/es/table";
import { FilterValue, SorterResult } from "antd/es/table/interface";
import { useSearchParams } from "react-router-dom";

export interface TableParams<
  TFilters extends Record<string, FilterValue | null> = Record<
    string,
    FilterValue | null
  >,
> {
  pagination?: TablePaginationConfig;
  sortField?: string;
  sortOrder?: string;
  filters?: TFilters;
  search?: string;
}

export const useTableParams = <
  TEntity extends object = Record<string, unknown>,
  TFilters extends Record<string, FilterValue | null> = Record<
    string,
    FilterValue | null
  >,
>() => {
  const [searchParams, setSearchParams] = useSearchParams();

  // Parse initial state from URL
  const current = parseInt(searchParams.get("page") || "1");
  const pageSize = parseInt(searchParams.get("per_page") || "10");
  const sortField = searchParams.get("sort_field");
  const sortOrder = searchParams.get("sort_order");
  const search = searchParams.get("search") || "";

  // Parse Filters from URL (format: key:val1,val2;key2:val3)
  const filtersStr = searchParams.get("filters");
  const filters: Record<string, FilterValue | null> = {};

  if (filtersStr) {
    filtersStr.split(";").forEach((part) => {
      const [key, valStr] = part.split(":");
      if (key && valStr) {
        filters[key] = valStr.split(",");
      }
    });
  }

  const tableParams: TableParams<TFilters> = {
    pagination: {
      current,
      pageSize,
    },
    sortField: sortField || undefined,
    sortOrder: sortOrder || undefined,
    filters: filters as TFilters,
    search,
  };

  const handleTableChange = (
    pagination: TablePaginationConfig,
    filters: Record<string, FilterValue | null>,
    sorter: SorterResult<TEntity> | SorterResult<TEntity>[]
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

    // Update Filters
    const filterParts: string[] = [];
    Object.entries(filters).forEach(([key, values]) => {
      if (values && values.length > 0) {
        const valStr = (values as Array<string | number | boolean>).join(",");
        filterParts.push(`${key}:${valStr}`);
      }
    });

    if (filterParts.length > 0) {
      newParams.set("filters", filterParts.join(";"));
    } else {
      newParams.delete("filters");
    }

    setSearchParams(newParams);
  };

  const handleSearch = (value: string) => {
    const newParams = new URLSearchParams(searchParams);
    if (value) {
      newParams.set("search", value);
    } else {
      newParams.delete("search");
    }
    newParams.set("page", "1"); // Reset to page 1 on search
    setSearchParams(newParams);
  };

  return {
    tableParams,
    handleTableChange,
    handleSearch,
  };
};
