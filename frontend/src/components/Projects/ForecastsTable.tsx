import { Box, EmptyState, Flex, Heading } from "@chakra-ui/react"
import { useQuery } from "@tanstack/react-query"
import { useMemo, useState } from "react"

import type { ForecastPublic, UserPublic } from "@/client"
import { ForecastsService, UsersService } from "@/client"
import { DataTable } from "@/components/DataTable/DataTable"
import AddForecast from "@/components/Projects/AddForecast"
import { buildForecastColumns } from "@/components/Projects/forecastColumns"
import { useTimeMachine } from "@/context/TimeMachineContext"

interface ForecastsTableProps {
  costElementId: string
  budgetBac?: string | number | null
  actualCost?: string | number | null
}

const PER_PAGE = 10

const ForecastsTable = ({
  costElementId,
  budgetBac,
  actualCost,
}: ForecastsTableProps) => {
  const [page, setPage] = useState(1)
  const { controlDate } = useTimeMachine()

  const { data, isLoading } = useQuery({
    queryFn: () =>
      ForecastsService.readForecasts({
        costElementId,
      }),
    queryKey: ["forecasts", { costElementId }, controlDate],
  })

  // Fetch users to map IDs to names
  const { data: usersData } = useQuery({
    queryFn: () => UsersService.readUsers({ skip: 0, limit: 1000 }),
    queryKey: ["users"],
    retry: false, // Don't retry if user doesn't have admin access
  })

  const forecasts: ForecastPublic[] = data ?? []

  // Create a map of user ID to display name (full_name or email)
  const userMap = useMemo(() => {
    const map = new Map<string, string>()
    if (usersData?.data) {
      usersData.data.forEach((user: UserPublic) => {
        const displayName = user.full_name || user.email
        map.set(user.id, displayName)
      })
    }
    return map
  }, [usersData])

  return (
    <Box>
      <Flex alignItems="center" justifyContent="space-between" mb={4}>
        <Heading size="md">Forecasts</Heading>
        <AddForecast
          costElementId={costElementId}
          budgetBac={budgetBac}
          actualCost={actualCost}
        />
      </Flex>
      {forecasts.length === 0 && !isLoading ? (
        <EmptyState.Root>
          <EmptyState.Content>
            <EmptyState.Title>No forecasts created yet</EmptyState.Title>
            <EmptyState.Description>
              Click &quot;Add Forecast&quot; to create your first forecast.
            </EmptyState.Description>
          </EmptyState.Content>
        </EmptyState.Root>
      ) : (
        <DataTable
          data={forecasts}
          columns={buildForecastColumns(
            costElementId,
            budgetBac,
            actualCost,
            userMap,
          )}
          tableId="forecasts-table"
          isLoading={isLoading}
          count={forecasts.length}
          page={page}
          onPageChange={setPage}
          pageSize={PER_PAGE}
        />
      )}
    </Box>
  )
}

export default ForecastsTable
