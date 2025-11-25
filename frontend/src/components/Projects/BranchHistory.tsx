import { Box, Heading, Text, VStack } from "@chakra-ui/react"
import { useQuery } from "@tanstack/react-query"
import { ChangeOrdersService } from "@/client"

interface BranchHistoryProps {
  projectId: string
  branch: string
}

const BranchHistory = ({ projectId, branch }: BranchHistoryProps) => {
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

  const changeOrder = changeOrders?.find((co) => co.branch === branch)

  if (isLoading) {
    return (
      <Box p={4}>
        <Text>Loading branch history...</Text>
      </Box>
    )
  }

  if (!changeOrder) {
    return (
      <Box p={4}>
        <Text>No history found for branch: {branch}</Text>
      </Box>
    )
  }

  return (
    <Box p={4}>
      <Heading size="sm" mb={4}>
        Branch History: {branch}
      </Heading>
      <VStack gap={3} align="stretch">
        <Box p={3} borderWidth="1px" borderRadius="md" bg="bg.surface">
          <Text fontWeight="medium">
            Change Order: {changeOrder.change_order_number}
          </Text>
          <Text fontSize="sm" color="fg.muted">
            Title: {changeOrder.title}
          </Text>
          <Text fontSize="sm" color="fg.muted">
            Status: {changeOrder.workflow_status}
          </Text>
          {changeOrder.created_at && (
            <Text fontSize="xs" color="fg.muted">
              Created: {new Date(changeOrder.created_at).toLocaleString()}
            </Text>
          )}
        </Box>
      </VStack>
    </Box>
  )
}

export default BranchHistory
