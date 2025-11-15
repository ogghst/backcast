import { Box, EmptyState, Heading, VStack } from "@chakra-ui/react"
import { useQuery } from "@tanstack/react-query"
import { useState } from "react"
import { FiTag } from "react-icons/fi"
import type {
  BaselineCostElementsPublic,
  BaselineCostElementWithCostElementPublic,
} from "@/client"
import { BaselineLogsService } from "@/client"
import { DataTable } from "@/components/DataTable/DataTable"
import type { ColumnDefExtended } from "@/components/DataTable/types"
import { useTimeMachine } from "@/context/TimeMachineContext"

interface BaselineCostElementsTableProps {
  projectId: string
  baselineId: string
}

const PER_PAGE = 50

const formatCurrency = (value: string | number | null | undefined): string => {
  if (value === null || value === undefined) {
    return "N/A"
  }
  const numValue = typeof value === "string" ? Number(value) : value
  if (Number.isNaN(numValue)) {
    return "N/A"
  }
  return `€${numValue.toLocaleString("en-US", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })}`
}

const formatPercent = (value: string | number | null | undefined): string => {
  if (value === null || value === undefined) {
    return "—"
  }
  const numeric = typeof value === "string" ? parseFloat(value) : Number(value)
  if (Number.isNaN(numeric)) {
    return "—"
  }
  return `${numeric.toFixed(2)}%`
}

const costElementsColumns: ColumnDefExtended<BaselineCostElementWithCostElementPublic>[] =
  [
    {
      accessorKey: "wbe_machine_type",
      header: "WBE",
      enableSorting: true,
      enableResizing: true,
      enableColumnFilter: true,
      filterType: "text",
      size: 150,
      defaultVisible: true,
    },
    {
      accessorKey: "department_name",
      header: "Department",
      enableSorting: true,
      enableResizing: true,
      enableColumnFilter: true,
      filterType: "text",
      size: 150,
      defaultVisible: true,
    },
    {
      accessorKey: "department_code",
      header: "Department Code",
      enableSorting: true,
      enableResizing: true,
      enableColumnFilter: true,
      filterType: "text",
      size: 120,
      defaultVisible: true,
    },
    {
      accessorKey: "budget_bac",
      header: "Budget (BAC)",
      enableSorting: true,
      enableResizing: true,
      size: 120,
      defaultVisible: true,
      cell: ({ getValue }) => formatCurrency(getValue() as string),
    },
    {
      accessorKey: "revenue_plan",
      header: "Revenue Plan",
      enableSorting: true,
      enableResizing: true,
      size: 120,
      defaultVisible: true,
      cell: ({ getValue }) => formatCurrency(getValue() as string),
    },
    {
      accessorKey: "planned_value",
      header: "Planned Value",
      enableSorting: true,
      enableResizing: true,
      size: 120,
      defaultVisible: true,
      cell: ({ getValue }) =>
        formatCurrency(getValue() as string | null | undefined),
    },
    {
      accessorKey: "actual_ac",
      header: "Actual AC",
      enableSorting: true,
      enableResizing: true,
      size: 120,
      defaultVisible: true,
      cell: ({ getValue }) => formatCurrency(getValue() as string | null),
    },
    {
      accessorKey: "forecast_eac",
      header: "Forecast EAC",
      enableSorting: true,
      enableResizing: true,
      size: 120,
      defaultVisible: true,
      cell: ({ getValue }) => formatCurrency(getValue() as string | null),
    },
    {
      accessorKey: "earned_ev",
      header: "Earned EV",
      enableSorting: true,
      enableResizing: true,
      size: 120,
      defaultVisible: true,
      cell: ({ getValue }) => formatCurrency(getValue() as string | null),
    },
    {
      accessorKey: "percent_complete",
      header: "Percent Complete",
      enableSorting: true,
      enableResizing: true,
      size: 140,
      defaultVisible: true,
      cell: ({ getValue }) =>
        formatPercent(getValue() as string | number | null),
    },
  ]

export default function BaselineCostElementsTable({
  projectId,
  baselineId,
}: BaselineCostElementsTableProps) {
  const [page, setPage] = useState(1)
  const { controlDate } = useTimeMachine()

  const { data, isLoading } = useQuery<BaselineCostElementsPublic>({
    queryFn: () =>
      BaselineLogsService.getBaselineCostElements({
        projectId: projectId,
        baselineId: baselineId,
        skip: (page - 1) * PER_PAGE,
        limit: PER_PAGE,
      }),
    queryKey: [
      "baseline-cost-elements",
      { projectId, baselineId, page },
      controlDate,
    ],
    enabled: !!projectId && !!baselineId,
  })

  const costElements = data?.data ?? []
  const count = data?.count ?? 0

  if (!isLoading && costElements.length === 0) {
    return (
      <EmptyState.Root>
        <EmptyState.Content>
          <EmptyState.Indicator>
            <FiTag />
          </EmptyState.Indicator>
          <VStack textAlign="center">
            <EmptyState.Title>No cost elements found</EmptyState.Title>
            <EmptyState.Description>
              This baseline has no cost elements
            </EmptyState.Description>
          </VStack>
        </EmptyState.Content>
      </EmptyState.Root>
    )
  }

  return (
    <Box>
      <Heading size="md" mb={4}>
        All Cost Elements
      </Heading>
      <DataTable
        data={costElements}
        columns={costElementsColumns}
        tableId="baseline-cost-elements-table"
        isLoading={isLoading}
        count={count}
        page={page}
        onPageChange={setPage}
        pageSize={PER_PAGE}
      />
    </Box>
  )
}
