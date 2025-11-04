import { Flex, Input } from "@chakra-ui/react"
import type { Column } from "@tanstack/react-table"
import { useMemo } from "react"

import type { ColumnDefExtended } from "./types"

export interface TableFiltersProps<TData> {
  columns: Column<TData>[]
}

/**
 * Table filters component - renders filter inputs based on column definitions
 */
export function TableFilters<TData>({ columns }: TableFiltersProps<TData>) {
  const filterableColumns = useMemo(() => {
    return columns.filter((col) => {
      const columnDef = col.columnDef as ColumnDefExtended<TData>
      return columnDef.enableColumnFilter && columnDef.filterType
    })
  }, [columns])

  if (filterableColumns.length === 0) {
    return null
  }

  return (
    <Flex gap={2} flexWrap="wrap" display={{ base: "none", md: "flex" }}>
      {filterableColumns.map((column) => {
        const columnDef = column.columnDef as ColumnDefExtended<TData>
        const filterValue = column.getFilterValue()

        // Text filter
        if (columnDef.filterType === "text") {
          return (
            <Input
              key={column.id}
              placeholder={`Filter ${typeof columnDef.header === "string" ? columnDef.header : column.id}...`}
              value={(filterValue as string) || ""}
              onChange={(e) => column.setFilterValue(e.target.value)}
              size="sm"
              maxW="200px"
            />
          )
        }

        // Select filter
        if (
          columnDef.filterType === "select" &&
          columnDef.filterConfig?.options
        ) {
          return (
            <select
              key={column.id}
              value={(filterValue as string) || ""}
              onChange={(e) =>
                column.setFilterValue(e.target.value || undefined)
              }
              style={{
                width: "200px",
                padding: "6px 8px",
                borderRadius: "4px",
                border: "1px solid #e2e8f0",
                fontSize: "14px",
              }}
            >
              <option value="">All</option>
              {columnDef.filterConfig.options.map((option) => (
                <option key={option} value={option}>
                  {option}
                </option>
              ))}
            </select>
          )
        }

        return null
      })}
    </Flex>
  )
}
