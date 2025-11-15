import { Badge, Box, Button, Flex, Heading, Text } from "@chakra-ui/react"
import { useQuery } from "@tanstack/react-query"
import { FiEye } from "react-icons/fi"
import type { BaselineLogPublic } from "@/client"
import { BaselineLogsService } from "@/client"
import { DataTable } from "@/components/DataTable/DataTable"
import type { ColumnDefExtended } from "@/components/DataTable/types"
import AddBaselineLog from "@/components/Projects/AddBaselineLog"
import CancelBaselineLog from "@/components/Projects/CancelBaselineLog"
import EditBaselineLog from "@/components/Projects/EditBaselineLog"
import ViewBaseline from "@/components/Projects/ViewBaseline"
import { useTimeMachine } from "@/context/TimeMachineContext"

interface BaselineLogsTableProps {
  projectId: string
}

// Valid baseline types for display
const BASELINE_TYPE_LABELS: Record<string, string> = {
  schedule: "Schedule",
  earned_value: "Earned Value",
  budget: "Budget",
  forecast: "Forecast",
  combined: "Combined",
}

// Valid milestone types for display
const MILESTONE_TYPE_LABELS: Record<string, string> = {
  kickoff: "Kickoff",
  bom_release: "BOM Release",
  engineering_complete: "Engineering Complete",
  procurement_complete: "Procurement Complete",
  manufacturing_start: "Manufacturing Start",
  shipment: "Shipment",
  site_arrival: "Site Arrival",
  commissioning_start: "Commissioning Start",
  commissioning_complete: "Commissioning Complete",
  closeout: "Closeout",
}

function BaselineLogsTable({ projectId }: BaselineLogsTableProps) {
  const { controlDate } = useTimeMachine()
  // Column definitions for Baseline Logs table
  const baselineLogsColumns: ColumnDefExtended<BaselineLogPublic>[] = [
    {
      accessorKey: "baseline_date",
      header: "Baseline Date",
      enableSorting: true,
      enableResizing: true,
      size: 120,
      defaultVisible: true,
      cell: ({ getValue }) => {
        const date = getValue() as string
        return date ? new Date(date).toLocaleDateString() : "N/A"
      },
    },
    {
      accessorKey: "baseline_type",
      header: "Type",
      enableSorting: true,
      enableResizing: true,
      enableColumnFilter: true,
      filterType: "select",
      filterConfig: {
        type: "select",
        options: Object.keys(BASELINE_TYPE_LABELS),
      },
      size: 150,
      defaultVisible: true,
      cell: ({ getValue }) => {
        const type = getValue() as string
        return (
          <span style={{ textTransform: "capitalize" }}>
            {BASELINE_TYPE_LABELS[type] || type}
          </span>
        )
      },
    },
    {
      accessorKey: "milestone_type",
      header: "Milestone",
      enableSorting: true,
      enableResizing: true,
      enableColumnFilter: true,
      filterType: "select",
      filterConfig: {
        type: "select",
        options: Object.keys(MILESTONE_TYPE_LABELS),
      },
      size: 180,
      defaultVisible: true,
      cell: ({ getValue }) => {
        const milestone = getValue() as string
        return (
          <span style={{ textTransform: "capitalize" }}>
            {MILESTONE_TYPE_LABELS[milestone] || milestone}
          </span>
        )
      },
    },
    {
      accessorKey: "description",
      header: "Description",
      enableSorting: true,
      enableResizing: true,
      enableColumnFilter: true,
      filterType: "text",
      size: 300,
      defaultVisible: true,
      cell: ({ getValue, row }) => {
        const description = (getValue() as string) || "N/A"
        const isCancelled = row.original.is_cancelled
        return (
          <Text
            as={isCancelled ? "span" : undefined}
            textDecoration={isCancelled ? "line-through" : undefined}
            color={isCancelled ? "gray.500" : undefined}
          >
            {description}
          </Text>
        )
      },
    },
    {
      accessorKey: "is_cancelled",
      header: "Status",
      enableSorting: true,
      enableResizing: true,
      enableColumnFilter: true,
      filterType: "select",
      filterConfig: {
        type: "select",
        options: ["true", "false"],
      },
      size: 100,
      defaultVisible: true,
      cell: ({ getValue }) => {
        const isCancelled = getValue() as boolean
        return (
          <Badge colorPalette={isCancelled ? "red" : "green"}>
            {isCancelled ? "Cancelled" : "Active"}
          </Badge>
        )
      },
    },
    {
      accessorKey: "created_at",
      header: "Created",
      enableSorting: true,
      enableResizing: true,
      size: 150,
      defaultVisible: true,
      cell: ({ getValue }) => {
        const date = getValue() as string
        return date ? new Date(date).toLocaleDateString() : "N/A"
      },
    },
    {
      id: "actions",
      header: "Actions",
      enableSorting: false,
      enableColumnFilter: false,
      size: 120,
      defaultVisible: true,
      cell: ({ row }) => {
        const baseline = row.original
        return (
          <Flex gap={2}>
            <ViewBaseline
              baseline={baseline}
              projectId={projectId}
              trigger={
                <Button variant="ghost" size="sm" aria-label="View baseline">
                  <FiEye fontSize="16px" />
                </Button>
              }
            />
            <EditBaselineLog baseline={baseline} projectId={projectId} />
            {!baseline.is_cancelled && (
              <CancelBaselineLog
                baselineId={baseline.baseline_id}
                projectId={projectId}
                description={baseline.description ?? undefined}
              />
            )}
          </Flex>
        )
      },
    },
  ]

  const { data: baselines, isLoading } = useQuery({
    queryFn: () =>
      BaselineLogsService.listBaselineLogs({
        projectId,
        excludeCancelled: false, // Show all by default, user can filter
      }),
    queryKey: ["baseline-logs", { projectId }, controlDate],
  })

  const baselineList = baselines ?? []

  return (
    <Box>
      <Flex alignItems="center" justifyContent="space-between" mb={4}>
        <Heading size="md">Baselines</Heading>
        <AddBaselineLog projectId={projectId} />
      </Flex>
      {baselineList.length === 0 && !isLoading ? (
        <Text color="gray.500" textAlign="center" py={8}>
          No baselines found. Create a baseline to get started.
        </Text>
      ) : (
        <DataTable
          data={baselineList}
          columns={baselineLogsColumns}
          tableId="baseline-logs-table"
          isLoading={isLoading}
          count={baselineList.length}
          page={1}
          onPageChange={() => {}} // No pagination for baseline logs (endpoint returns all)
          pageSize={baselineList.length || 10}
        />
      )}
    </Box>
  )
}

export default BaselineLogsTable
