import { Box, Flex, Heading } from "@chakra-ui/react"
import { useQuery } from "@tanstack/react-query"
import { useState } from "react"

import type { EarnedValueEntryPublic } from "@/client"
import { EarnedValueEntriesService } from "@/client"
import { DataTable } from "@/components/DataTable/DataTable"
import AddEarnedValueEntry from "@/components/Projects/AddEarnedValueEntry"
import { buildEarnedValueColumns } from "@/components/Projects/earnedValueColumns"
import { useTimeMachine } from "@/context/TimeMachineContext"

interface EarnedValueEntriesTableProps {
  costElementId: string
  budgetBac?: string | number | null
}

const PER_PAGE = 10

const EarnedValueEntriesTable = ({
  costElementId,
  budgetBac,
}: EarnedValueEntriesTableProps) => {
  const [page, setPage] = useState(1)
  const { controlDate } = useTimeMachine()

  const { data, isLoading } = useQuery({
    queryFn: () =>
      EarnedValueEntriesService.readEarnedValueEntries({
        costElementId,
        skip: (page - 1) * PER_PAGE,
        limit: PER_PAGE,
      }),
    queryKey: ["earned-value-entries", { costElementId, page }, controlDate],
  })

  const entries: EarnedValueEntryPublic[] = data?.data ?? []
  const count = data?.count ?? 0

  return (
    <Box>
      <Flex alignItems="center" justifyContent="space-between" mb={4}>
        <Heading size="md">Earned Value Entries</Heading>
        <AddEarnedValueEntry
          costElementId={costElementId}
          budgetBac={budgetBac}
        />
      </Flex>
      <DataTable
        data={entries}
        columns={buildEarnedValueColumns(costElementId, budgetBac)}
        tableId="earned-value-entries-table"
        isLoading={isLoading}
        count={count}
        page={page}
        onPageChange={setPage}
        pageSize={PER_PAGE}
      />
    </Box>
  )
}

export default EarnedValueEntriesTable
