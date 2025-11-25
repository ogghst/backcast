import { Box, Grid, Heading, Text, VStack } from "@chakra-ui/react"
import { useQuery } from "@tanstack/react-query"
import { BranchComparisonService } from "@/client"

interface BranchComparisonViewProps {
  projectId: string
  branch: string
  baseBranch?: string
}

const BranchComparisonView = ({
  projectId,
  branch,
  baseBranch = "main",
}: BranchComparisonViewProps) => {
  const { data, isLoading, error } = useQuery({
    queryKey: ["branch-comparison", projectId, branch, baseBranch],
    queryFn: () =>
      BranchComparisonService.compareBranches({
        projectId,
        branch,
        baseBranch,
      }),
    enabled: !!projectId && !!branch && branch !== baseBranch,
  })

  if (isLoading) {
    return (
      <Box p={4}>
        <Text>Loading comparison...</Text>
      </Box>
    )
  }

  if (error) {
    return (
      <Box p={4}>
        <Text color="red.500">Error loading comparison: {String(error)}</Text>
      </Box>
    )
  }

  if (!data) {
    return (
      <Box p={4}>
        <Text>No comparison data available</Text>
      </Box>
    )
  }

  const { creates, updates, deletes, financial_impact } = data

  return (
    <Box p={4}>
      <VStack gap={4} align="stretch">
        <Heading size="md">
          Branch Comparison: {branch} vs {baseBranch}
        </Heading>

        {/* Financial Impact Summary */}
        <Box
          p={4}
          borderWidth="1px"
          borderRadius="lg"
          bg="bg.surface"
          borderColor="border.emphasized"
        >
          <Heading size="sm" mb={2}>
            Financial Impact Summary
          </Heading>
          <Grid templateColumns={{ base: "1fr", md: "repeat(2, 1fr)" }} gap={4}>
            <Box>
              <Text fontSize="sm" color="fg.muted">
                Total Revenue Change
              </Text>
              <Text
                fontSize="lg"
                fontWeight="bold"
                color={
                  parseFloat(financial_impact.total_revenue_change) >= 0
                    ? "green.500"
                    : "red.500"
                }
              >
                {parseFloat(financial_impact.total_revenue_change) >= 0
                  ? "+"
                  : ""}
                €
                {parseFloat(
                  financial_impact.total_revenue_change,
                ).toLocaleString("en-US", {
                  minimumFractionDigits: 2,
                  maximumFractionDigits: 2,
                })}
              </Text>
            </Box>
            <Box>
              <Text fontSize="sm" color="fg.muted">
                Total Budget Change
              </Text>
              <Text
                fontSize="lg"
                fontWeight="bold"
                color={
                  parseFloat(financial_impact.total_budget_change) >= 0
                    ? "green.500"
                    : "red.500"
                }
              >
                {parseFloat(financial_impact.total_budget_change) >= 0
                  ? "+"
                  : ""}
                €
                {parseFloat(
                  financial_impact.total_budget_change,
                ).toLocaleString("en-US", {
                  minimumFractionDigits: 2,
                  maximumFractionDigits: 2,
                })}
              </Text>
            </Box>
          </Grid>
        </Box>

        {/* Side-by-side comparison */}
        <Grid templateColumns={{ base: "1fr", lg: "repeat(2, 1fr)" }} gap={4}>
          {/* Creates */}
          <Box
            p={4}
            borderWidth="1px"
            borderRadius="lg"
            bg="green.50"
            borderColor="green.200"
          >
            <Heading size="sm" mb={2} color="green.700">
              Creates ({creates.length})
            </Heading>
            {creates.length === 0 ? (
              <Text fontSize="sm" color="fg.muted">
                No new entities
              </Text>
            ) : (
              <VStack gap={2} align="stretch">
                {creates.map((item, idx) => (
                  <Box
                    key={idx}
                    p={2}
                    bg="white"
                    borderRadius="md"
                    borderWidth="1px"
                    borderColor="green.300"
                  >
                    <Text fontSize="sm" fontWeight="medium">
                      {item.entity_type === "wbe"
                        ? item.machine_type
                        : item.department_name}
                    </Text>
                    {item.revenue_allocation && (
                      <Text fontSize="xs" color="fg.muted">
                        Revenue: €
                        {parseFloat(item.revenue_allocation).toLocaleString(
                          "en-US",
                          {
                            minimumFractionDigits: 2,
                            maximumFractionDigits: 2,
                          },
                        )}
                      </Text>
                    )}
                  </Box>
                ))}
              </VStack>
            )}
          </Box>

          {/* Updates */}
          <Box
            p={4}
            borderWidth="1px"
            borderRadius="lg"
            bg="yellow.50"
            borderColor="yellow.200"
          >
            <Heading size="sm" mb={2} color="yellow.700">
              Updates ({updates.length})
            </Heading>
            {updates.length === 0 ? (
              <Text fontSize="sm" color="fg.muted">
                No modified entities
              </Text>
            ) : (
              <VStack gap={2} align="stretch">
                {updates.map((item, idx) => (
                  <Box
                    key={idx}
                    p={2}
                    bg="white"
                    borderRadius="md"
                    borderWidth="1px"
                    borderColor="yellow.300"
                  >
                    <Text fontSize="sm" fontWeight="medium">
                      {item.entity_type === "wbe"
                        ? item.machine_type
                        : item.department_name}
                    </Text>
                    {item.revenue_allocation && (
                      <Text fontSize="xs" color="fg.muted">
                        Revenue: €
                        {parseFloat(item.revenue_allocation).toLocaleString(
                          "en-US",
                          {
                            minimumFractionDigits: 2,
                            maximumFractionDigits: 2,
                          },
                        )}
                      </Text>
                    )}
                  </Box>
                ))}
              </VStack>
            )}
          </Box>
        </Grid>

        {/* Deletes */}
        {deletes.length > 0 && (
          <Box
            p={4}
            borderWidth="1px"
            borderRadius="lg"
            bg="red.50"
            borderColor="red.200"
          >
            <Heading size="sm" mb={2} color="red.700">
              Deletes ({deletes.length})
            </Heading>
            <VStack gap={2} align="stretch">
              {deletes.map((item, idx) => (
                <Box
                  key={idx}
                  p={2}
                  bg="white"
                  borderRadius="md"
                  borderWidth="1px"
                  borderColor="red.300"
                >
                  <Text fontSize="sm" fontWeight="medium">
                    {item.entity_type === "wbe"
                      ? item.machine_type
                      : item.department_name}
                  </Text>
                </Box>
              ))}
            </VStack>
          </Box>
        )}
      </VStack>
    </Box>
  )
}

export default BranchComparisonView
