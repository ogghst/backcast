import {
  Box,
  Grid,
  Heading,
  SkeletonText,
  Text,
  VStack,
} from "@chakra-ui/react"
import { useQuery } from "@tanstack/react-query"
import {
  FiAlertCircle,
  FiCheckCircle,
  FiTrendingUp,
  FiXCircle,
} from "react-icons/fi"
import { type CostSummaryPublic, CostSummaryService } from "@/client"

interface CostSummaryProps {
  level: "cost-element" | "wbe" | "project"
  costElementId?: string
  wbeId?: string
  projectId?: string
  isQualityCost?: boolean
}

export default function CostSummary({
  level,
  costElementId,
  wbeId,
  projectId,
  isQualityCost,
}: CostSummaryProps) {
  const queryKey = [
    "cost-summary",
    level,
    costElementId || wbeId || projectId,
    { isQualityCost },
  ]

  const { data: summary, isLoading } = useQuery<CostSummaryPublic>({
    queryKey,
    queryFn: () => {
      if (level === "cost-element" && costElementId) {
        return CostSummaryService.getCostElementCostSummary({
          costElementId: costElementId,
          isQualityCost: isQualityCost,
        })
      }
      if (level === "wbe" && wbeId) {
        return CostSummaryService.getWbeCostSummary({
          wbeId: wbeId,
          isQualityCost: isQualityCost,
        })
      }
      if (level === "project" && projectId) {
        return CostSummaryService.getProjectCostSummary({
          projectId: projectId,
          isQualityCost: isQualityCost,
        })
      }
      throw new Error("Invalid props: missing required ID")
    },
    enabled:
      (level === "cost-element" && !!costElementId) ||
      (level === "wbe" && !!wbeId) ||
      (level === "project" && !!projectId),
  })

  if (isLoading) {
    return (
      <Box mb={6}>
        <Heading size="md" mb={4}>
          Cost Summary
        </Heading>
        <Grid
          templateColumns={{
            base: "1fr",
            md: "repeat(2, 1fr)",
            lg: "repeat(4, 1fr)",
          }}
          gap={4}
        >
          {[1, 2, 3, 4].map((i) => (
            <Box
              key={i}
              p={4}
              borderWidth="1px"
              borderRadius="md"
              borderColor="gray.200"
            >
              <SkeletonText noOfLines={2} />
            </Box>
          ))}
        </Grid>
      </Box>
    )
  }

  if (!summary) {
    return null
  }

  const totalCost = Number(summary.total_cost || 0)
  const budgetBac = summary.budget_bac ? Number(summary.budget_bac) : null
  const costPercentage = summary.cost_percentage_of_budget || 0
  const registrationCount = summary.cost_registration_count || 0

  // Format currency
  const formatCurrency = (value: number) => {
    return new Intl.NumberFormat("en-US", {
      style: "currency",
      currency: "EUR",
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    }).format(value)
  }

  // Format percentage
  const formatPercentage = (value: number) => {
    return `${value.toFixed(1)}%`
  }

  // Determine color and icon based on cost percentage
  const getCostStatus = (percent: number) => {
    if (percent < 50) {
      return {
        color: "green.500",
        icon: FiCheckCircle,
        label: "Under Budget",
      }
    }
    if (percent < 80) {
      return {
        color: "blue.500",
        icon: FiTrendingUp,
        label: "On Track",
      }
    }
    if (percent < 100) {
      return {
        color: "orange.500",
        icon: FiAlertCircle,
        label: "Approaching Budget",
      }
    }
    return {
      color: "red.500",
      icon: FiXCircle,
      label: "Over Budget",
    }
  }

  const costStatus = budgetBac ? getCostStatus(costPercentage) : null
  const StatusIcon = costStatus?.icon || FiTrendingUp

  return (
    <Box mb={6}>
      <Heading size="md" mb={4}>
        Cost Summary
      </Heading>
      <Grid
        templateColumns={{
          base: "1fr",
          md: "repeat(2, 1fr)",
          lg: "repeat(4, 1fr)",
        }}
        gap={4}
      >
        {/* Card 1: Total Cost */}
        <Box
          p={4}
          borderWidth="1px"
          borderRadius="md"
          borderColor="gray.200"
          bg="white"
        >
          <VStack align="stretch" gap={1}>
            <Text fontSize="sm" color="gray.600" fontWeight="medium">
              Total Cost
            </Text>
            <Text fontSize="xl" fontWeight="bold">
              {formatCurrency(totalCost)}
            </Text>
            <Text fontSize="xs" color="gray.500" mt={1}>
              {registrationCount} registration
              {registrationCount !== 1 ? "s" : ""}
            </Text>
          </VStack>
        </Box>

        {/* Card 2: Budget BAC */}
        {budgetBac !== null && (
          <Box
            p={4}
            borderWidth="1px"
            borderRadius="md"
            borderColor="gray.200"
            bg="white"
          >
            <VStack align="stretch" gap={1}>
              <Text fontSize="sm" color="gray.600" fontWeight="medium">
                Budget BAC
              </Text>
              <Text fontSize="xl" fontWeight="bold">
                {formatCurrency(budgetBac)}
              </Text>
              <Text fontSize="xs" color="gray.500" mt={1}>
                Budget at Completion
              </Text>
            </VStack>
          </Box>
        )}

        {/* Card 3: Cost % of Budget */}
        {budgetBac !== null && costStatus && (
          <Box
            p={4}
            borderWidth="1px"
            borderRadius="md"
            borderColor="gray.200"
            bg="white"
          >
            <VStack align="stretch" gap={1}>
              <Text fontSize="sm" color="gray.600" fontWeight="medium">
                Cost % of Budget
              </Text>
              <Text fontSize="xl" fontWeight="bold" color={costStatus.color}>
                {formatPercentage(costPercentage)}
              </Text>
              <Text fontSize="xs" color={costStatus.color} mt={1}>
                <StatusIcon style={{ display: "inline", marginRight: "4px" }} />
                {costStatus.label}
              </Text>
            </VStack>
          </Box>
        )}

        {/* Card 4: Registration Count (if no budget) */}
        {budgetBac === null && (
          <Box
            p={4}
            borderWidth="1px"
            borderRadius="md"
            borderColor="gray.200"
            bg="white"
          >
            <VStack align="stretch" gap={1}>
              <Text fontSize="sm" color="gray.600" fontWeight="medium">
                Registrations
              </Text>
              <Text fontSize="xl" fontWeight="bold">
                {registrationCount}
              </Text>
              <Text fontSize="xs" color="gray.500" mt={1}>
                Cost registrations
              </Text>
            </VStack>
          </Box>
        )}
      </Grid>

      {/* Quality Cost Filter Notice */}
      {isQualityCost !== undefined && (
        <Box
          mt={4}
          p={3}
          bg="blue.50"
          borderRadius="md"
          borderWidth="1px"
          borderColor="blue.200"
        >
          <Text fontSize="sm" color="blue.700">
            {isQualityCost
              ? "Showing quality costs only"
              : "Showing regular costs only"}
          </Text>
        </Box>
      )}
    </Box>
  )
}
