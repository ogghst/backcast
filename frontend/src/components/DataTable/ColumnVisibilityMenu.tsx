import { IconButton } from "@chakra-ui/react"
import type { Column } from "@tanstack/react-table"
import { FiSettings } from "react-icons/fi"

import {
  MenuCheckboxItem,
  MenuContent,
  MenuRoot,
  MenuSeparator,
  MenuTrigger,
} from "@/components/ui/menu"

export interface ColumnVisibilityMenuProps<TData> {
  columns: Column<TData>[]
}

/**
 * Menu component for toggling column visibility
 */
export function ColumnVisibilityMenu<TData>({
  columns,
}: ColumnVisibilityMenuProps<TData>) {
  return (
    <MenuRoot>
      <MenuTrigger>
        <IconButton aria-label="Column settings" variant="ghost" size="sm">
          <FiSettings />
        </IconButton>
      </MenuTrigger>
      <MenuContent>
        {columns.map((column) => (
          <MenuCheckboxItem
            key={column.id}
            value={column.id}
            checked={column.getIsVisible()}
            onCheckedChange={(checked) => {
              column.toggleVisibility(checked)
            }}
          >
            {typeof column.columnDef.header === "string"
              ? column.columnDef.header
              : column.id}
          </MenuCheckboxItem>
        ))}
        <MenuSeparator />
        <MenuCheckboxItem
          value="show-all"
          checked={columns.every((col) => col.getIsVisible())}
          onCheckedChange={(checked) => {
            columns.forEach((col) => {
              col.toggleVisibility(checked)
            })
          }}
        >
          Show All
        </MenuCheckboxItem>
      </MenuContent>
    </MenuRoot>
  )
}
