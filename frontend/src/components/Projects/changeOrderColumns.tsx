import { Flex } from "@chakra-ui/react"
import type { ChangeOrderPublic } from "@/client"
import type { ColumnDefExtended } from "@/components/DataTable/types"
import DeleteChangeOrder from "./DeleteChangeOrder"
import EditChangeOrder from "./EditChangeOrder"

export const formatDate = (value: string | undefined) =>
  value ? new Date(value).toLocaleDateString() : "N/A"

export const formatCurrency = (value: string | number | undefined | null) => {
  if (value === null || value === undefined) {
    return "€0.00"
  }
  const numeric = typeof value === "string" ? parseFloat(value) : Number(value)
  if (Number.isNaN(numeric)) {
    return "€0.00"
  }
  return `€${numeric.toLocaleString("en-US", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })}`
}

export function buildChangeOrderColumns(): ColumnDefExtended<ChangeOrderPublic>[] {
  return [
    {
      accessorKey: "change_order_number",
      header: "Change Order Number",
      enableSorting: true,
      enableResizing: true,
      size: 180,
      defaultVisible: true,
      cell: ({ getValue }) => (getValue() as string) ?? "—",
    },
    {
      accessorKey: "title",
      header: "Title",
      enableSorting: true,
      enableResizing: true,
      size: 250,
      defaultVisible: true,
      cell: ({ getValue }) => (getValue() as string) ?? "—",
    },
    {
      accessorKey: "workflow_status",
      header: "Status",
      enableSorting: true,
      enableResizing: true,
      size: 120,
      defaultVisible: true,
      cell: ({ getValue }) => {
        const status = (getValue() as string) ?? "—"
        return status.charAt(0).toUpperCase() + status.slice(1)
      },
    },
    {
      accessorKey: "requesting_party",
      header: "Requesting Party",
      enableSorting: true,
      enableResizing: true,
      size: 180,
      defaultVisible: true,
      cell: ({ getValue }) => (getValue() as string) ?? "—",
    },
    {
      accessorKey: "effective_date",
      header: "Effective Date",
      enableSorting: true,
      enableResizing: true,
      size: 140,
      defaultVisible: true,
      cell: ({ getValue }) => formatDate(getValue() as string),
    },
    {
      accessorKey: "cost_impact",
      header: "Cost Impact",
      enableSorting: true,
      enableResizing: true,
      size: 140,
      defaultVisible: true,
      cell: ({ getValue }) =>
        formatCurrency(getValue() as string | number | null),
    },
    {
      accessorKey: "revenue_impact",
      header: "Revenue Impact",
      enableSorting: true,
      enableResizing: true,
      size: 140,
      defaultVisible: true,
      cell: ({ getValue }) =>
        formatCurrency(getValue() as string | number | null),
    },
    {
      id: "actions",
      header: "Actions",
      enableSorting: false,
      enableResizing: false,
      enableColumnFilter: false,
      size: 160,
      defaultVisible: true,
      cell: ({ row }) => (
        <Flex gap={2}>
          <EditChangeOrder changeOrder={row.original} />
          <DeleteChangeOrder
            changeOrderId={row.original.change_order_id}
            changeOrderNumber={row.original.change_order_number}
            projectId={row.original.project_id}
          />
        </Flex>
      ),
    },
  ]
}
