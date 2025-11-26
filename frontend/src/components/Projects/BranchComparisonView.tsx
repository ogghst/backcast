import { Box, Grid, Heading, Text, VStack } from "@chakra-ui/react"
import { useQuery } from "@tanstack/react-query"
import { BranchComparisonService } from "@/client"
import { useColorModeValue } from "@/components/ui/color-mode"
import type {
  BranchComparisonChange,
  BranchComparisonResponse,
} from "@/types/branchComparison"

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
  // Theme-aware colors
  const _cardBg = useColorModeValue("bg.surface", "bg.surface")
  const _borderCol = useColorModeValue("border", "border")
  const mutedText = useColorModeValue("fg.muted", "fg.muted")
  const itemBg = useColorModeValue("bg.subtle", "bg.subtle")
  const createBg = useColorModeValue("green.50", "green.950")
  const createBorder = useColorModeValue("green.200", "green.800")
  const createText = useColorModeValue("green.700", "green.300")
  const updateBg = useColorModeValue("yellow.50", "yellow.950")
  const updateBorder = useColorModeValue("yellow.200", "yellow.800")
  const updateText = useColorModeValue("yellow.700", "yellow.300")
  const deleteBg = useColorModeValue("red.50", "red.950")
  const deleteBorder = useColorModeValue("red.200", "red.800")
  const deleteText = useColorModeValue("red.700", "red.300")

  const { data, isLoading, error } = useQuery<BranchComparisonResponse>({
    queryKey: ["branch-comparison", projectId, branch, baseBranch],
    queryFn: async () => {
      const response = await BranchComparisonService.compareBranches({
        projectId,
        branch,
        baseBranch,
      })
      return response as unknown as BranchComparisonResponse
    },
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

  const summary = data.summary
  const creates = data.creates ?? []
  const updates = data.updates ?? []
  const deletes = data.deletes ?? []

  const legacyFinancialImpact = data.financial_impact
  const totalRevenueChange =
    summary?.total_revenue_change ??
    (legacyFinancialImpact
      ? Number(legacyFinancialImpact.total_revenue_change)
      : 0)
  const totalBudgetChange =
    summary?.total_budget_change ??
    (legacyFinancialImpact
      ? Number(legacyFinancialImpact.total_budget_change)
      : 0)

  const formatCurrency = (value: number) => {
    const sign = value > 0 ? "+" : value < 0 ? "-" : ""
    return `${sign}€${Math.abs(value).toLocaleString("en-US", {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    })}`
  }

  const renderChangeList = (
    items: BranchComparisonChange[],
    accent: "green" | "yellow" | "red",
  ) => {
    if (items.length === 0) {
      return (
        <Text fontSize="sm" color={mutedText}>
          No items
        </Text>
      )
    }

    const accentBorder =
      accent === "green"
        ? createBorder
        : accent === "yellow"
          ? updateBorder
          : deleteBorder

    return (
      <VStack gap={2} align="stretch">
        {items.map((item) => (
          <Box
            key={item.entity_id}
            p={2}
            bg={itemBg}
            borderRadius="md"
            borderWidth="1px"
            borderColor={accentBorder}
          >
            <Text fontSize="sm" fontWeight="medium">
              {item.description}
            </Text>
            {typeof item.revenue_change === "number" && (
              <Text fontSize="xs" color={mutedText}>
                Revenue Δ: {formatCurrency(item.revenue_change)}
              </Text>
            )}
            {typeof item.budget_change === "number" && (
              <Text fontSize="xs" color={mutedText}>
                Budget Δ: {formatCurrency(item.budget_change)}
              </Text>
            )}
          </Box>
        ))}
      </VStack>
    )
  }

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
                color={totalRevenueChange >= 0 ? "green.500" : "red.500"}
              >
                {formatCurrency(totalRevenueChange)}
              </Text>
            </Box>
            <Box>
              <Text fontSize="sm" color="fg.muted">
                Total Budget Change
              </Text>
              <Text
                fontSize="lg"
                fontWeight="bold"
                color={totalBudgetChange >= 0 ? "green.500" : "red.500"}
              >
                {formatCurrency(totalBudgetChange)}
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
            bg={createBg}
            borderColor={createBorder}
          >
            <Heading size="sm" mb={2} color={createText}>
              Creates ({creates.length})
            </Heading>
            {renderChangeList(creates, "green")}
          </Box>

          {/* Updates */}
          <Box
            p={4}
            borderWidth="1px"
            borderRadius="lg"
            bg={updateBg}
            borderColor={updateBorder}
          >
            <Heading size="sm" mb={2} color={updateText}>
              Updates ({updates.length})
            </Heading>
            {renderChangeList(updates, "yellow")}
          </Box>
        </Grid>

        {/* Deletes */}
        {deletes.length > 0 && (
          <Box
            p={4}
            borderWidth="1px"
            borderRadius="lg"
            bg={deleteBg}
            borderColor={deleteBorder}
          >
            <Heading size="sm" mb={2} color={deleteText}>
              Deletes ({deletes.length})
            </Heading>
            {renderChangeList(deletes, "red")}
          </Box>
        )}
      </VStack>
    </Box>
  )
}

export default BranchComparisonView
