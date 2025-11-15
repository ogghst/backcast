import {
  Box,
  Button,
  Collapsible,
  EmptyState,
  Flex,
  Heading,
  IconButton,
  SkeletonText,
  Text,
  VStack,
} from "@chakra-ui/react"
import { useQuery } from "@tanstack/react-query"
import { useState } from "react"
import { FiChevronDown, FiChevronUp } from "react-icons/fi"
import type {
  BaselineCostElementsByWBEPublic,
  BaselineCostElementWithCostElementPublic,
} from "@/client"
import { BaselineLogsService } from "@/client"
import { DataTable } from "@/components/DataTable/DataTable"
import type { ColumnDefExtended } from "@/components/DataTable/types"
import { useTimeMachine } from "@/context/TimeMachineContext"

interface BaselineCostElementsByWBETableProps {
  projectId: string
  baselineId: string
}

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

const costElementColumns: ColumnDefExtended<BaselineCostElementWithCostElementPublic>[] =
  [
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
  ]

export default function BaselineCostElementsByWBETable({
  projectId,
  baselineId,
}: BaselineCostElementsByWBETableProps) {
  const { controlDate } = useTimeMachine()
  const queryKey = [
    "baseline-cost-elements-by-wbe",
    projectId,
    baselineId,
    controlDate,
  ]

  const { data, isLoading } = useQuery<BaselineCostElementsByWBEPublic>({
    queryKey,
    queryFn: () =>
      BaselineLogsService.getBaselineCostElementsByWbe({
        projectId: projectId,
        baselineId: baselineId,
      }),
    enabled: !!projectId && !!baselineId,
  })

  if (isLoading) {
    return (
      <Box>
        <SkeletonText noOfLines={10} gap={4} />
      </Box>
    )
  }

  if (!data || !data.wbes || data.wbes.length === 0) {
    return (
      <EmptyState.Root>
        <EmptyState.Content>
          <EmptyState.Title>No cost elements found</EmptyState.Title>
          <EmptyState.Description>
            This baseline has no cost elements
          </EmptyState.Description>
        </EmptyState.Content>
      </EmptyState.Root>
    )
  }

  return (
    <VStack align="stretch" gap={4}>
      {data.wbes.map((wbe) => (
        <WBEAccordionItem key={wbe.wbe_id} wbe={wbe} />
      ))}
    </VStack>
  )
}

function WBEAccordionItem({
  wbe,
}: {
  wbe: {
    wbe_id: string
    machine_type: string
    serial_number?: string | null
    cost_elements?: Array<BaselineCostElementWithCostElementPublic> | null
    wbe_total_budget_bac: string
    wbe_total_revenue_plan: string
    wbe_total_planned_value: string
    wbe_total_actual_ac?: string | null
    wbe_total_forecast_eac?: string | null
    wbe_total_earned_ev?: string | null
  }
}) {
  const [isOpen, setIsOpen] = useState(false)

  return (
    <Box borderWidth="1px" borderRadius="md" borderColor="gray.200" bg="white">
      <Collapsible.Root open={isOpen} onOpenChange={(e) => setIsOpen(e.open)}>
        <Collapsible.Trigger asChild>
          <Button
            variant="ghost"
            width="100%"
            justifyContent="space-between"
            p={4}
          >
            <Flex
              justifyContent="space-between"
              alignItems="center"
              width="100%"
            >
              <VStack align="start" gap={1}>
                <Text fontWeight="bold">{wbe.machine_type}</Text>
                {wbe.serial_number && (
                  <Text fontSize="sm" color="gray.600">
                    Serial: {wbe.serial_number}
                  </Text>
                )}
              </VStack>
              <VStack align="end" gap={1}>
                <Text fontSize="sm" color="gray.600">
                  {wbe.cost_elements?.length || 0} cost elements
                </Text>
                <Text fontSize="sm" fontWeight="medium">
                  Total BAC: {formatCurrency(wbe.wbe_total_budget_bac)}
                </Text>
              </VStack>
              <IconButton
                aria-label={isOpen ? "Collapse" : "Expand"}
                variant="ghost"
                size="sm"
              >
                {isOpen ? <FiChevronUp /> : <FiChevronDown />}
              </IconButton>
            </Flex>
          </Button>
        </Collapsible.Trigger>
        <Collapsible.Content>
          <Box mt={4}>
            {/* WBE Totals Summary */}
            <Box
              p={4}
              mb={4}
              borderWidth="1px"
              borderRadius="md"
              borderColor="gray.200"
              bg="gray.50"
            >
              <Heading size="sm" mb={3}>
                WBE Totals
              </Heading>
              <Flex gap={4} wrap="wrap">
                <Box>
                  <Text fontSize="xs" color="gray.600">
                    Total Budget BAC
                  </Text>
                  <Text fontWeight="bold">
                    {formatCurrency(wbe.wbe_total_budget_bac)}
                  </Text>
                </Box>
                <Box>
                  <Text fontSize="xs" color="gray.600">
                    Total Planned Value
                  </Text>
                  <Text fontWeight="bold">
                    {formatCurrency(wbe.wbe_total_planned_value)}
                  </Text>
                </Box>
                <Box>
                  <Text fontSize="xs" color="gray.600">
                    Total Revenue Plan
                  </Text>
                  <Text fontWeight="bold">
                    {formatCurrency(wbe.wbe_total_revenue_plan)}
                  </Text>
                </Box>
                {wbe.wbe_total_actual_ac && (
                  <Box>
                    <Text fontSize="xs" color="gray.600">
                      Total Actual AC
                    </Text>
                    <Text fontWeight="bold">
                      {formatCurrency(wbe.wbe_total_actual_ac)}
                    </Text>
                  </Box>
                )}
                {wbe.wbe_total_forecast_eac && (
                  <Box>
                    <Text fontSize="xs" color="gray.600">
                      Total Forecast EAC
                    </Text>
                    <Text fontWeight="bold">
                      {formatCurrency(wbe.wbe_total_forecast_eac)}
                    </Text>
                  </Box>
                )}
                {wbe.wbe_total_earned_ev && (
                  <Box>
                    <Text fontSize="xs" color="gray.600">
                      Total Earned EV
                    </Text>
                    <Text fontWeight="bold">
                      {formatCurrency(wbe.wbe_total_earned_ev)}
                    </Text>
                  </Box>
                )}
              </Flex>
            </Box>

            {/* Cost Elements Table */}
            {wbe.cost_elements && wbe.cost_elements.length > 0 ? (
              <DataTable
                data={wbe.cost_elements}
                columns={costElementColumns}
                tableId={`baseline-cost-elements-wbe-${wbe.wbe_id}`}
                isLoading={false}
                count={wbe.cost_elements.length}
                page={1}
                onPageChange={() => {}}
                pageSize={wbe.cost_elements.length}
              />
            ) : (
              <EmptyState.Root>
                <EmptyState.Content>
                  <EmptyState.Title>
                    No cost elements for this WBE
                  </EmptyState.Title>
                </EmptyState.Content>
              </EmptyState.Root>
            )}
          </Box>
        </Collapsible.Content>
      </Collapsible.Root>
    </Box>
  )
}
