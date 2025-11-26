import {
  Badge,
  Box,
  Flex,
  Heading,
  HStack,
  Text,
  VStack,
} from "@chakra-ui/react"
import { useQuery } from "@tanstack/react-query"
import type { ChangeOrderLineItemPublic, ChangeOrderPublic } from "@/client"
import { ChangeOrderLineItemsService, ChangeOrdersService } from "@/client"
import BranchComparisonView from "./BranchComparisonView"
import { formatCurrency, formatDate } from "./changeOrderColumns"

interface ChangeOrderDetailViewProps {
  changeOrderId: string
  projectId: string
}

const ChangeOrderDetailView = ({
  changeOrderId,
  projectId,
}: ChangeOrderDetailViewProps) => {
  const { data: changeOrder, isLoading: isLoadingCO } = useQuery({
    queryFn: () =>
      ChangeOrdersService.readChangeOrder({
        projectId,
        changeOrderId,
      }),
    queryKey: ["change-orders", projectId, changeOrderId],
  })

  const { data: lineItems, isLoading: isLoadingLineItems } = useQuery({
    queryFn: () =>
      ChangeOrderLineItemsService.listChangeOrderLineItems({
        projectId,
        changeOrderId,
      }),
    queryKey: ["change-order-line-items", projectId, changeOrderId],
    enabled: !!changeOrder,
  })

  if (isLoadingCO) {
    return <Text>Loading change order...</Text>
  }

  if (!changeOrder) {
    return <Text>Change order not found</Text>
  }

  const co: ChangeOrderPublic = changeOrder
  const items: ChangeOrderLineItemPublic[] = lineItems ?? []

  // Calculate total financial impact
  const totalCostImpact = items.reduce((sum, item) => {
    const cost = item.budget_change ? parseFloat(item.budget_change) : 0
    return sum + cost
  }, 0)

  const totalRevenueImpact = items.reduce((sum, item) => {
    const revenue = item.revenue_change ? parseFloat(item.revenue_change) : 0
    return sum + revenue
  }, 0)

  return (
    <Box>
      <VStack gap={6} align="stretch">
        {/* Header */}
        <Flex justifyContent="space-between" alignItems="start">
          <VStack align="start" gap={2}>
            <Heading size="lg">{co.title}</Heading>
            <HStack gap={2}>
              <Text fontSize="sm" color="fg.muted">
                {co.change_order_number}
              </Text>
              <Badge>{co.workflow_status}</Badge>
              {co.branch && <Badge colorPalette="blue">{co.branch}</Badge>}
            </HStack>
          </VStack>
        </Flex>

        {/* Details */}
        <Box borderWidth="1px" borderRadius="md" p={4}>
          <VStack align="stretch" gap={3}>
            <Flex justifyContent="space-between">
              <Text fontWeight="medium">Description:</Text>
              <Text>{co.description}</Text>
            </Flex>
            <Flex justifyContent="space-between">
              <Text fontWeight="medium">Requesting Party:</Text>
              <Text>{co.requesting_party}</Text>
            </Flex>
            {co.justification && (
              <Flex justifyContent="space-between">
                <Text fontWeight="medium">Justification:</Text>
                <Text>{co.justification}</Text>
              </Flex>
            )}
            <Flex justifyContent="space-between">
              <Text fontWeight="medium">Effective Date:</Text>
              <Text>{formatDate(co.effective_date)}</Text>
            </Flex>
            <Flex justifyContent="space-between">
              <Text fontWeight="medium">Created:</Text>
              <Text>{formatDate(co.created_at)}</Text>
            </Flex>
          </VStack>
        </Box>

        {/* Financial Impact Summary */}
        <Box borderWidth="1px" borderRadius="md" p={4}>
          <Heading size="sm" mb={3}>
            Financial Impact Summary
          </Heading>
          <VStack align="stretch" gap={2}>
            <Flex justifyContent="space-between">
              <Text fontWeight="medium">Total Cost Impact:</Text>
              <Text>{formatCurrency(totalCostImpact || co.cost_impact)}</Text>
            </Flex>
            <Flex justifyContent="space-between">
              <Text fontWeight="medium">Total Revenue Impact:</Text>
              <Text>
                {formatCurrency(totalRevenueImpact || co.revenue_impact)}
              </Text>
            </Flex>
          </VStack>
        </Box>

        {/* Line Items */}
        <Box borderWidth="1px" borderRadius="md" p={4}>
          <Heading size="sm" mb={3}>
            Line Items
          </Heading>
          {isLoadingLineItems ? (
            <Text>Loading line items...</Text>
          ) : items.length === 0 ? (
            <Text color="fg.muted">No line items</Text>
          ) : (
            <VStack align="stretch" gap={2}>
              {items.map((item, index) => (
                <Box
                  key={index}
                  borderWidth="1px"
                  borderRadius="sm"
                  p={2}
                  bg="bg.subtle"
                >
                  <VStack align="stretch" gap={1}>
                    <HStack justifyContent="space-between">
                      <Badge>{item.operation_type}</Badge>
                      <Text fontSize="sm">{item.target_type}</Text>
                    </HStack>
                    {item.description && (
                      <Text fontSize="sm">{item.description}</Text>
                    )}
                    <HStack justifyContent="space-between">
                      {item.budget_change && (
                        <Text fontSize="sm">
                          Cost: {formatCurrency(item.budget_change)}
                        </Text>
                      )}
                      {item.revenue_change && (
                        <Text fontSize="sm">
                          Revenue: {formatCurrency(item.revenue_change)}
                        </Text>
                      )}
                    </HStack>
                  </VStack>
                </Box>
              ))}
            </VStack>
          )}
        </Box>

        {/* Branch Comparison View */}
        {co.branch && co.branch !== "main" && (
          <Box borderWidth="1px" borderRadius="md" p={4}>
            <BranchComparisonView
              projectId={projectId}
              branch={co.branch}
              baseBranch="main"
            />
          </Box>
        )}
      </VStack>
    </Box>
  )
}

export default ChangeOrderDetailView
