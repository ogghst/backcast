import type { ColumnDef } from "@tanstack/react-table"

/**
 * Filter types supported by the DataTable component
 */
export type FilterType = "text" | "select" | "dateRange" | "numberRange"

/**
 * Configuration for column filters
 */
export interface FilterConfig {
  type: FilterType
  options?: string[] // For 'select' type filters
  placeholder?: string
}

/**
 * Additional properties for DataTable columns beyond standard ColumnDef
 */
export interface ColumnDefExtensions {
  /**
   * Whether this column can be sorted
   * @default false
   */
  enableSorting?: boolean

  /**
   * Whether this column can be resized
   * @default false
   */
  enableResizing?: boolean

  /**
   * Whether this column can be filtered
   * @default false
   */
  enableColumnFilter?: boolean

  /**
   * Type of filter to display for this column
   */
  filterType?: FilterType

  /**
   * Configuration for column filter (if enableColumnFilter is true)
   */
  filterConfig?: FilterConfig

  /**
   * Initial width of the column in pixels
   * @default 150
   */
  size?: number

  /**
   * Minimum width in pixels when resizing
   * @default 50
   */
  minSize?: number

  /**
   * Maximum width in pixels when resizing
   */
  maxSize?: number

  /**
   * Whether this column should be visible by default
   * @default true
   */
  defaultVisible?: boolean
}

/**
 * Extended column definition that includes filter configuration
 * Intersection of TanStack Table's ColumnDef with additional properties
 */
export type ColumnDefExtended<TData, TValue = unknown> = ColumnDef<
  TData,
  TValue
> &
  ColumnDefExtensions

/**
 * Re-export TanStack Table types for convenience
 */
export type { ColumnDef } from "@tanstack/react-table"
