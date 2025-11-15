import { Box, EmptyState, Heading, VStack } from "@chakra-ui/react"
import { useQuery } from "@tanstack/react-query"
import { useState } from "react"
import { FiTrendingUp } from "react-icons/fi"
import type {
  BaselineCostElementsPublic,
  BaselineCostElementWithCostElementPublic,
} from "@/client"
import { BaselineLogsService } from "@/client"
import { DataTable } from "@/components/DataTable/DataTable"
import { buildBaselineEarnedValueColumns } from "@/components/Projects/earnedValueColumns"
import { useTimeMachine } from "@/context/TimeMachineContext"

interface BaselineEarnedValueEntriesTableProps {
  projectId: string
  baselineId: string
}

const PER_PAGE = 50

export default function BaselineEarnedValueEntriesTable({
  projectId,
  baselineId,
}: BaselineEarnedValueEntriesTableProps) {
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
      "baseline-earned-value-snapshots",
      { projectId, baselineId, page },
      controlDate,
    ],
    enabled: !!projectId && !!baselineId,
  })

  const entries: BaselineCostElementWithCostElementPublic[] = data?.data ?? []
  const count = data?.count ?? 0

  if (!isLoading && entries.length === 0) {
    return (
      <EmptyState.Root>
        <EmptyState.Content>
          <EmptyState.Indicator>
            <FiTrendingUp />
          </EmptyState.Indicator>
          <VStack textAlign="center">
            <EmptyState.Title>No earned value snapshots</EmptyState.Title>
            <EmptyState.Description>
              Capture earned value to populate percent complete snapshots.
            </EmptyState.Description>
          </VStack>
        </EmptyState.Content>
      </EmptyState.Root>
    )
  }

  return (
    <Box>
      <Heading size="md" mb={4}>
        Earned Value Snapshot
      </Heading>
      <DataTable
        data={entries}
        columns={buildBaselineEarnedValueColumns()}
        tableId="baseline-earned-value-entries-table"
        isLoading={isLoading}
        count={count}
        page={page}
        onPageChange={setPage}
        pageSize={PER_PAGE}
      />
    </Box>
  )
}
