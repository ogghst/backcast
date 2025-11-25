import { Box, Heading, Text } from "@chakra-ui/react"
import { useQuery } from "@tanstack/react-query"
import { ChangeOrderLineItemsService } from "@/client"
import { DataTable } from "@/components/DataTable/DataTable"
import type { ColumnDefExtended } from "@/components/DataTable/types"

interface ChangeOrderLineItemsTableProps {
  projectId: string
  changeOrderId: string
}

const ChangeOrderLineItemsTable = ({
  projectId,
  changeOrderId,
}: ChangeOrderLineItemsTableProps) => {
  const { data: lineItems, isLoading } = useQuery({
    queryKey: ["change-order-line-items", projectId, changeOrderId],
    queryFn: () =>
      ChangeOrderLineItemsService.listChangeOrderLineItems({
        projectId,
        changeOrderId,
      }),
    enabled: !!projectId && !!changeOrderId,
  })

  const columns: ColumnDefExtended<any>[] = [
    {
      accessorKey: "operation_type",
      header: "Operation",
      enableSorting: true,
      size: 100,
      defaultVisible: true,
      cell: ({ getValue }) => (
        <span style={{ textTransform: "capitalize" }}>
          {String(getValue())}
        </span>
      ),
    },
    {
      accessorKey: "target_type",
      header: "Target Type",
      enableSorting: true,
      size: 120,
      defaultVisible: true,
      cell: ({ getValue }) => (
        <span style={{ textTransform: "uppercase" }}>{String(getValue())}</span>
      ),
    },
    {
      accessorKey: "budget_change",
      header: "Budget Change",
      enableSorting: true,
      size: 120,
      defaultVisible: true,
      cell: ({ getValue }) => {
        const value = parseFloat(String(getValue() || "0"))
        return (
          <Text
            color={value >= 0 ? "green.500" : "red.500"}
            fontWeight="medium"
          >
            {value >= 0 ? "+" : ""}€
            {value.toLocaleString("en-US", {
              minimumFractionDigits: 2,
              maximumFractionDigits: 2,
            })}
          </Text>
        )
      },
    },
    {
      accessorKey: "revenue_change",
      header: "Revenue Change",
      enableSorting: true,
      size: 120,
      defaultVisible: true,
      cell: ({ getValue }) => {
        const value = parseFloat(String(getValue() || "0"))
        return (
          <Text
            color={value >= 0 ? "green.500" : "red.500"}
            fontWeight="medium"
          >
            {value >= 0 ? "+" : ""}€
            {value.toLocaleString("en-US", {
              minimumFractionDigits: 2,
              maximumFractionDigits: 2,
            })}
          </Text>
        )
      },
    },
  ]

  if (isLoading) {
    return (
      <Box p={4}>
        <Text>Loading line items...</Text>
      </Box>
    )
  }

  if (!lineItems || lineItems.length === 0) {
    return (
      <Box p={4}>
        <Heading size="sm" mb={2}>
          Line Items
        </Heading>
        <Text color="fg.muted">No line items found for this change order.</Text>
      </Box>
    )
  }

  return (
    <Box>
      <Heading size="sm" mb={4}>
        Line Items
      </Heading>
      <DataTable
        data={lineItems}
        columns={columns}
        tableId="change-order-line-items-table"
        isLoading={isLoading}
        count={lineItems.length}
        page={1}
        onPageChange={() => {}}
        pageSize={lineItems.length}
      />
    </Box>
  )
}

export default ChangeOrderLineItemsTable
