import { Box, Flex, Heading } from "@chakra-ui/react"
import { useQuery } from "@tanstack/react-query"
import type { CostElementSchedulePublic } from "@/client"
import { CostElementSchedulesService } from "@/client"
import { DataTable } from "@/components/DataTable/DataTable"
import type { ColumnDefExtended } from "@/components/DataTable/types"
import AddCostElementSchedule from "@/components/Projects/AddCostElementSchedule"
import DeleteCostElementSchedule from "@/components/Projects/DeleteCostElementSchedule"
import EditCostElementSchedule from "@/components/Projects/EditCostElementSchedule"
import { useTimeMachine } from "@/context/TimeMachineContext"

interface CostElementSchedulesTableProps {
  costElementId: string
}

// Extended type to include fields that exist in backend but are missing from generated types
type CostElementSchedulePublicExtended = CostElementSchedulePublic & {
  registration_date?: string | null
  description?: string | null
}

// Column definitions for Cost Element Schedules table
const costElementSchedulesColumns: ColumnDefExtended<CostElementSchedulePublicExtended>[] =
  [
    {
      accessorKey: "registration_date",
      header: "Registration Date",
      enableSorting: true,
      enableResizing: true,
      size: 150,
      defaultVisible: true,
      cell: ({ getValue }) => {
        const date = getValue() as string | null | undefined
        return date ? new Date(date).toLocaleDateString() : "N/A"
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
      cell: ({ getValue }) => {
        const desc = getValue() as string | null | undefined
        return desc?.trim() || "—"
      },
    },
    {
      accessorKey: "start_date",
      header: "Start Date",
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
      accessorKey: "end_date",
      header: "End Date",
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
      accessorKey: "progression_type",
      header: "Progression Type",
      enableSorting: true,
      enableResizing: true,
      size: 150,
      defaultVisible: true,
      cell: ({ getValue }) => (
        <span style={{ textTransform: "capitalize" }}>
          {(getValue() as string) || "N/A"}
        </span>
      ),
    },
    {
      id: "actions",
      header: "Actions",
      enableSorting: false,
      enableColumnFilter: false,
      size: 120,
      defaultVisible: true,
      cell: ({ row }) => (
        <Flex gap={2}>
          <EditCostElementSchedule schedule={row.original} />
          <DeleteCostElementSchedule
            id={row.original.schedule_id}
            description={row.original.description}
          />
        </Flex>
      ),
    },
  ]

function CostElementSchedulesTable({
  costElementId,
}: CostElementSchedulesTableProps) {
  const { controlDate } = useTimeMachine()
  const { data: scheduleHistoryData = [], isLoading } = useQuery<
    CostElementSchedulePublicExtended[]
  >({
    queryKey: ["cost-element-schedule-history", costElementId, controlDate],
    queryFn: async () =>
      await CostElementSchedulesService.readScheduleHistoryByCostElement({
        costElementId,
      }),
    retry: false,
  })

  return (
    <Box>
      <Flex alignItems="center" justifyContent="space-between" mb={4}>
        <Heading size="md">Schedule</Heading>
        <AddCostElementSchedule costElementId={costElementId} />
      </Flex>
      <DataTable
        data={scheduleHistoryData}
        columns={costElementSchedulesColumns}
        tableId="cost-element-schedules-table"
        isLoading={isLoading}
        count={scheduleHistoryData.length}
        page={1}
        onPageChange={() => {}}
        pageSize={scheduleHistoryData.length || 10}
      />
    </Box>
  )
}

export default CostElementSchedulesTable
