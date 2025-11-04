import { Box, Flex, Table } from "@chakra-ui/react"
import {
  flexRender,
  getCoreRowModel,
  getFilteredRowModel,
  getSortedRowModel,
  type Row,
  useReactTable,
} from "@tanstack/react-table"
import { FiChevronDown, FiChevronUp } from "react-icons/fi"
import {
  PaginationItems,
  PaginationNextTrigger,
  PaginationPrevTrigger,
  PaginationRoot,
} from "@/components/ui/pagination"
import { SkeletonText } from "@/components/ui/skeleton"

import { ColumnResizer } from "./ColumnResizer"
import { ColumnVisibilityMenu } from "./ColumnVisibilityMenu"
import { TableFilters } from "./TableFilters"
import type { ColumnDefExtended } from "./types"

export interface DataTableProps<TData> {
  data: TData[]
  columns: ColumnDefExtended<TData>[]
  tableId: string
  onRowClick?: (row: TData) => void
  isLoading?: boolean
  count: number
  page: number
  onPageChange: (page: number) => void
  pageSize?: number
}

/**
 * Base DataTable component using TanStack Table and Chakra UI
 */
export function DataTable<TData>({
  data,
  columns,
  tableId: _tableId, // Reserved for future use (preferences, localStorage)
  onRowClick,
  isLoading = false,
  count,
  page: _page, // Used by pagination component
  onPageChange,
  pageSize = 10,
}: DataTableProps<TData>) {
  // Initialize TanStack Table
  const table = useReactTable({
    data,
    columns,
    getCoreRowModel: getCoreRowModel(),
    getFilteredRowModel: getFilteredRowModel(),
    getSortedRowModel: getSortedRowModel(),
    enableSorting: true,
    enableColumnResizing: true,
    enableColumnFilters: true,
    columnResizeMode: "onChange",
    manualPagination: true, // We handle pagination via URL/search params
  })

  // Loading state
  if (isLoading) {
    return (
      <Table.Root size={{ base: "sm", md: "md" }}>
        <Table.Header>
          <Table.Row>
            {columns.map((column, index) => (
              <Table.ColumnHeader
                key={index}
                w={column.size ? `${column.size}px` : "sm"}
              >
                {typeof column.header === "string"
                  ? column.header
                  : index.toString()}
              </Table.ColumnHeader>
            ))}
          </Table.Row>
        </Table.Header>
        <Table.Body>
          {[...Array(5)].map((_, rowIndex) => (
            <Table.Row key={rowIndex}>
              {columns.map((_, colIndex) => (
                <Table.Cell key={colIndex}>
                  <SkeletonText noOfLines={1} />
                </Table.Cell>
              ))}
            </Table.Row>
          ))}
        </Table.Body>
      </Table.Root>
    )
  }

  return (
    <>
      <Flex justifyContent="space-between" alignItems="center" mb={4}>
        <TableFilters columns={table.getAllColumns()} />
        <ColumnVisibilityMenu columns={table.getAllColumns()} />
      </Flex>
      <Table.Root size={{ base: "sm", md: "md" }}>
        <Table.Header>
          {table.getHeaderGroups().map((headerGroup) => (
            <Table.Row key={headerGroup.id}>
              {headerGroup.headers.map((header) => (
                <Box
                  as="th"
                  key={header.id}
                  position="relative"
                  w={`${header.getSize()}px`}
                >
                  <Table.ColumnHeader
                    cursor={header.column.getCanSort() ? "pointer" : "default"}
                    userSelect="none"
                    onClick={header.column.getToggleSortingHandler()}
                    _hover={
                      header.column.getCanSort() ? { bg: "gray.50" } : undefined
                    }
                  >
                    <Flex alignItems="center" gap={2}>
                      {header.isPlaceholder
                        ? null
                        : flexRender(
                            header.column.columnDef.header,
                            header.getContext(),
                          )}
                      {header.column.getCanSort() && (
                        <Flex direction="column" gap={0}>
                          <FiChevronUp
                            size={12}
                            color={
                              header.column.getIsSorted() === "asc"
                                ? "currentColor"
                                : "#d1d5db"
                            }
                          />
                          <FiChevronDown
                            size={12}
                            color={
                              header.column.getIsSorted() === "desc"
                                ? "currentColor"
                                : "#d1d5db"
                            }
                          />
                        </Flex>
                      )}
                    </Flex>
                  </Table.ColumnHeader>
                  {header.column.getCanResize() && (
                    <ColumnResizer header={header} />
                  )}
                </Box>
              ))}
            </Table.Row>
          ))}
        </Table.Header>
        <Table.Body>
          {table.getRowModel().rows.map((row: Row<TData>) => (
            <Table.Row
              key={row.id}
              cursor={onRowClick ? "pointer" : "default"}
              onClick={() => onRowClick?.(row.original)}
              _hover={onRowClick ? { bg: "gray.100" } : undefined}
            >
              {row.getVisibleCells().map((cell) => (
                <Table.Cell
                  key={cell.id}
                  onClick={(e: React.MouseEvent) => {
                    // Prevent row click when clicking on actions cell
                    if (cell.column.id === "actions") {
                      e.stopPropagation()
                    }
                  }}
                >
                  {flexRender(cell.column.columnDef.cell, cell.getContext())}
                </Table.Cell>
              ))}
            </Table.Row>
          ))}
        </Table.Body>
      </Table.Root>
      <Flex justifyContent="flex-end" mt={4}>
        <PaginationRoot
          count={count}
          pageSize={pageSize}
          onPageChange={({ page: newPage }) => onPageChange(newPage)}
        >
          <Flex>
            <PaginationPrevTrigger />
            <PaginationItems />
            <PaginationNextTrigger />
          </Flex>
        </PaginationRoot>
      </Flex>
    </>
  )
}
