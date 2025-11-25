import { Box, Heading } from "@chakra-ui/react"
import { useQuery } from "@tanstack/react-query"
import { ChangeOrdersService } from "@/client"
import { DataTable } from "@/components/DataTable/DataTable"
import type { ColumnDefExtended } from "@/components/DataTable/types"
import { useBranch } from "@/context/BranchContext"

interface BranchManagementProps {
  projectId: string
}

const BranchManagement = ({ projectId }: BranchManagementProps) => {
  const { availableBranches } = useBranch()

  const { data: changeOrders, isLoading } = useQuery({
    queryKey: ["change-orders", projectId],
    queryFn: () =>
      ChangeOrdersService.listChangeOrders({
        projectId,
        skip: 0,
        limit: 1000,
      }),
    enabled: !!projectId,
  })

  // Create branch data from change orders
  const branchData = availableBranches.map((branch) => {
    const changeOrder = changeOrders?.find((co) => co.branch === branch)
    return {
      branch,
      changeOrderNumber: changeOrder?.change_order_number || "N/A",
      status: changeOrder?.workflow_status || "N/A",
      title: changeOrder?.title || "N/A",
    }
  })

  const columns: ColumnDefExtended<(typeof branchData)[0]>[] = [
    {
      accessorKey: "branch",
      header: "Branch",
      enableSorting: true,
      size: 150,
      defaultVisible: true,
    },
    {
      accessorKey: "changeOrderNumber",
      header: "Change Order",
      enableSorting: true,
      size: 150,
      defaultVisible: true,
    },
    {
      accessorKey: "title",
      header: "Title",
      enableSorting: true,
      size: 200,
      defaultVisible: true,
    },
    {
      accessorKey: "status",
      header: "Status",
      enableSorting: true,
      size: 120,
      defaultVisible: true,
      cell: ({ getValue }) => (
        <span style={{ textTransform: "capitalize" }}>
          {String(getValue())}
        </span>
      ),
    },
  ]

  return (
    <Box p={4}>
      <Heading size="md" mb={4}>
        Branch Management
      </Heading>
      <DataTable
        data={branchData}
        columns={columns}
        tableId="branch-management-table"
        isLoading={isLoading}
        count={branchData.length}
        page={1}
        onPageChange={() => {}}
        pageSize={branchData.length}
      />
    </Box>
  )
}

export default BranchManagement
