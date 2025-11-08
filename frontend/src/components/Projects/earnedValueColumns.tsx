import { Flex } from "@chakra-ui/react"
import type { EarnedValueEntryPublic } from "@/client"
import type { ColumnDefExtended } from "@/components/DataTable/types"
import DeleteEarnedValueEntry from "@/components/Projects/DeleteEarnedValueEntry"
import EditEarnedValueEntry from "@/components/Projects/EditEarnedValueEntry"

const formatDate = (value: string | undefined) =>
  value ? new Date(value).toLocaleDateString() : "N/A"

const formatPercent = (value: string | number | undefined) => {
  const numeric = typeof value === "string" ? parseFloat(value) : Number(value)
  if (Number.isNaN(numeric)) {
    return "0.00%"
  }
  return `${numeric.toFixed(2)}%`
}

const formatCurrency = (value: string | number | undefined | null) => {
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

export function buildEarnedValueColumns(
  costElementId: string,
  budgetBac?: string | number | null,
): ColumnDefExtended<EarnedValueEntryPublic>[] {
  void costElementId
  return [
    {
      accessorKey: "completion_date",
      header: "Completion Date",
      enableSorting: true,
      enableResizing: true,
      size: 140,
      defaultVisible: true,
      cell: ({ getValue }) => formatDate(getValue() as string),
    },
    {
      accessorKey: "percent_complete",
      header: "Percent Complete",
      enableSorting: true,
      enableResizing: true,
      size: 140,
      defaultVisible: true,
      cell: ({ getValue }) => formatPercent(getValue() as string | number),
    },
    {
      accessorKey: "earned_value",
      header: "Earned Value",
      enableSorting: true,
      enableResizing: true,
      size: 140,
      defaultVisible: true,
      cell: ({ getValue }) =>
        formatCurrency(getValue() as string | number | null),
    },
    {
      accessorKey: "deliverables",
      header: "Deliverables",
      enableSorting: true,
      enableResizing: true,
      size: 220,
      defaultVisible: true,
      cell: ({ getValue }) => (getValue() as string) ?? "—",
    },
    {
      accessorKey: "description",
      header: "Description",
      enableSorting: true,
      enableResizing: true,
      size: 220,
      defaultVisible: true,
      cell: ({ getValue }) => (getValue() as string) ?? "—",
    },
    {
      accessorKey: "baseline_id",
      header: "Baseline",
      enableSorting: true,
      enableResizing: true,
      size: 160,
      defaultVisible: true,
      cell: ({ getValue }) => (getValue() as string | null) ?? "Not linked",
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
          <EditEarnedValueEntry
            earnedValueEntry={row.original}
            budgetBac={budgetBac}
          />
          <DeleteEarnedValueEntry
            earnedValueId={row.original.earned_value_id}
            description={row.original.deliverables ?? "Earned value entry"}
          />
        </Flex>
      ),
    },
  ]
}
