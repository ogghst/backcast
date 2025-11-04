import { Box } from "@chakra-ui/react"
import type { Header } from "@tanstack/react-table"

export interface ColumnResizerProps<TData> {
  header: Header<TData, unknown>
}

/**
 * Column resize handle component
 */
export function ColumnResizer<TData>({ header }: ColumnResizerProps<TData>) {
  if (!header.column.getCanResize()) {
    return null
  }

  return (
    <Box
      onMouseDown={header.getResizeHandler()}
      onTouchStart={header.getResizeHandler()}
      position="absolute"
      right={0}
      top={0}
      bottom={0}
      w="4px"
      cursor="col-resize"
      userSelect="none"
      _hover={{ bg: "blue.400" }}
      _active={{ bg: "blue.600" }}
    />
  )
}
