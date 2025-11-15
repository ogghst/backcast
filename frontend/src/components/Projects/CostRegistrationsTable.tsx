import { Box, Flex, Heading } from "@chakra-ui/react"
import { useQuery } from "@tanstack/react-query"
import { useState } from "react"
import type { CostRegistrationPublic } from "@/client"
import { CostRegistrationsService } from "@/client"
import { DataTable } from "@/components/DataTable/DataTable"
import type { ColumnDefExtended } from "@/components/DataTable/types"
import AddCostRegistration from "@/components/Projects/AddCostRegistration"
import DeleteCostRegistration from "@/components/Projects/DeleteCostRegistration"
import EditCostRegistration from "@/components/Projects/EditCostRegistration"
import { useTimeMachine } from "@/context/TimeMachineContext"

interface CostRegistrationsTableProps {
  costElementId: string
}

const PER_PAGE = 10

// Column definitions for Cost Registrations table
const costRegistrationsColumns: ColumnDefExtended<CostRegistrationPublic>[] = [
  {
    accessorKey: "registration_date",
    header: "Date",
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
    accessorKey: "amount",
    header: "Amount",
    enableSorting: true,
    enableResizing: true,
    size: 120,
    defaultVisible: true,
    cell: ({ getValue }) => {
      const amount = getValue() as string | undefined
      return amount
        ? `€${parseFloat(amount).toLocaleString("en-US", {
            minimumFractionDigits: 2,
            maximumFractionDigits: 2,
          })}`
        : "€0.00"
    },
  },
  {
    accessorKey: "cost_category",
    header: "Category",
    enableSorting: true,
    enableResizing: true,
    enableColumnFilter: true,
    filterType: "select",
    filterConfig: {
      type: "select",
      options: ["labor", "materials", "subcontractors"],
    },
    size: 150,
    defaultVisible: true,
    cell: ({ getValue }) => (
      <span style={{ textTransform: "capitalize" }}>
        {(getValue() as string) || "N/A"}
      </span>
    ),
  },
  {
    accessorKey: "invoice_number",
    header: "Invoice Number",
    enableSorting: true,
    enableResizing: true,
    size: 150,
    defaultVisible: true,
    cell: ({ getValue }) => (getValue() as string) || "N/A",
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
  },
  {
    accessorKey: "is_quality_cost",
    header: "Quality Cost",
    enableSorting: true,
    enableResizing: true,
    size: 100,
    defaultVisible: true,
    cell: ({ getValue }) => ((getValue() as boolean) ? "Yes" : "No"),
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
        <EditCostRegistration costRegistration={row.original} />
        <DeleteCostRegistration
          id={row.original.cost_registration_id}
          description={row.original.description}
        />
      </Flex>
    ),
  },
]

function CostRegistrationsTable({
  costElementId,
}: CostRegistrationsTableProps) {
  const [page, setPage] = useState(1)
  const { controlDate } = useTimeMachine()

  const { data, isLoading } = useQuery({
    queryFn: () =>
      CostRegistrationsService.readCostRegistrations({
        costElementId,
        skip: (page - 1) * PER_PAGE,
        limit: PER_PAGE,
      }),
    queryKey: ["cost-registrations", { costElementId, page }, controlDate],
  })

  const costRegistrations = data?.data ?? []
  const count = data?.count ?? 0

  return (
    <Box>
      <Flex alignItems="center" justifyContent="space-between" mb={4}>
        <Heading size="md">Cost Registrations</Heading>
        <AddCostRegistration costElementId={costElementId} />
      </Flex>
      <DataTable
        data={costRegistrations}
        columns={costRegistrationsColumns}
        tableId="cost-registrations-table"
        isLoading={isLoading}
        count={count}
        page={page}
        onPageChange={setPage}
        pageSize={PER_PAGE}
      />
    </Box>
  )
}

export default CostRegistrationsTable
