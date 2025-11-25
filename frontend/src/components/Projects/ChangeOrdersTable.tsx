import { Box, Flex, Heading } from "@chakra-ui/react"
import { useQuery } from "@tanstack/react-query"
import { useState } from "react"

import type { ChangeOrderPublic } from "@/client"
import { ChangeOrdersService } from "@/client"
import { DataTable } from "@/components/DataTable/DataTable"
import { useBranch } from "@/context/BranchContext"
import AddChangeOrder from "./AddChangeOrder"
import { buildChangeOrderColumns } from "./changeOrderColumns"

interface ChangeOrdersTableProps {
  projectId: string
}

const PER_PAGE = 10

const ChangeOrdersTable = ({ projectId }: ChangeOrdersTableProps) => {
  const [page, setPage] = useState(1)
  const { currentBranch } = useBranch()

  const { data, isLoading } = useQuery({
    queryFn: () =>
      ChangeOrdersService.listChangeOrders({
        projectId,
        skip: (page - 1) * PER_PAGE,
        limit: PER_PAGE,
      }),
    queryKey: ["change-orders", projectId, page, currentBranch],
  })

  const changeOrders: ChangeOrderPublic[] = data ?? []
  const count = changeOrders.length

  return (
    <Box>
      <Flex alignItems="center" justifyContent="space-between" mb={4}>
        <Heading size="md">Change Orders</Heading>
        <AddChangeOrder projectId={projectId} />
      </Flex>
      <DataTable
        data={changeOrders}
        columns={buildChangeOrderColumns()}
        tableId="change-orders-table"
        isLoading={isLoading}
        count={count}
        page={page}
        onPageChange={setPage}
        pageSize={PER_PAGE}
      />
    </Box>
  )
}

export default ChangeOrdersTable
