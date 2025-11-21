import {
  Box,
  Grid,
  Heading,
  SkeletonText,
  Text,
  VStack,
} from "@chakra-ui/react"
import { useQuery } from "@tanstack/react-query"
import type { BaselineSummaryPublic } from "@/client"
import { BaselineLogsService } from "@/client"
import { useColorModeValue } from "@/components/ui/color-mode"
import { useTimeMachine } from "@/context/TimeMachineContext"

interface BaselineSummaryProps {
  projectId: string
  baselineId: string
}

export default function BaselineSummary({
  projectId,
  baselineId,
}: BaselineSummaryProps) {
  const { controlDate } = useTimeMachine()
  // Theme-aware colors (declare before early returns)
  const cardBg = useColorModeValue("bg.surface", "bg.surface")
  const borderCol = useColorModeValue("border", "border")
  const mutedText = useColorModeValue("fg.muted", "fg.muted")

  const queryKey = [
    "baseline-snapshot-summary",
    projectId,
    baselineId,
    controlDate,
  ]

  const { data: summary, isLoading } = useQuery<BaselineSummaryPublic>({
    queryKey,
    queryFn: () =>
      BaselineLogsService.getBaselineSnapshotSummary({
        projectId: projectId,
        baselineId: baselineId,
      }),
    enabled: !!projectId && !!baselineId,
  })

  const formatCurrency = (
    value: string | number | null | undefined,
  ): string => {
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

  if (isLoading) {
    return (
      <Box mb={6}>
        <Heading size="md" mb={4}>
          Baseline Summary
        </Heading>
        <Grid
          templateColumns={{
            base: "1fr",
            md: "repeat(2, 1fr)",
            lg: "repeat(3, 1fr)",
          }}
          gap={4}
        >
          {[1, 2, 3, 4, 5, 6, 7].map((i) => (
            <Box
              key={i}
              p={4}
              borderWidth="1px"
              borderRadius="md"
              borderColor={borderCol}
              bg={cardBg}
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

  const totalBudgetBac = Number(summary.total_budget_bac)
  const totalRevenuePlan = Number(summary.total_revenue_plan)
  const totalPlannedValue = Number(summary.total_planned_value)
  const totalActualAc = summary.total_actual_ac
    ? Number(summary.total_actual_ac)
    : null
  const totalForecastEac = summary.total_forecast_eac
    ? Number(summary.total_forecast_eac)
    : null
  const totalEarnedEv = summary.total_earned_ev
    ? Number(summary.total_earned_ev)
    : null
  const costElementCount = summary.cost_element_count

  return (
    <Box mb={6}>
      <Heading size="md" mb={4}>
        Baseline Snapshot Summary
      </Heading>
      <Grid
        templateColumns={{
          base: "1fr",
          md: "repeat(2, 1fr)",
          lg: "repeat(3, 1fr)",
        }}
        gap={4}
      >
        {/* Card 1: Total Budget BAC */}
        <Box
          p={4}
          borderWidth="1px"
          borderRadius="md"
          borderColor={borderCol}
          bg={cardBg}
        >
          <VStack align="stretch" gap={1}>
            <Text fontSize="sm" color={mutedText} fontWeight="medium">
              Total Budget BAC
            </Text>
            <Text fontSize="xl" fontWeight="bold">
              {formatCurrency(totalBudgetBac)}
            </Text>
            <Text fontSize="xs" color={mutedText} mt={1}>
              Budget at Completion
            </Text>
          </VStack>
        </Box>

        {/* Card 2: Total Revenue Plan */}
        <Box
          p={4}
          borderWidth="1px"
          borderRadius="md"
          borderColor={borderCol}
          bg={cardBg}
        >
          <VStack align="stretch" gap={1}>
            <Text fontSize="sm" color={mutedText} fontWeight="medium">
              Total Revenue Plan
            </Text>
            <Text fontSize="xl" fontWeight="bold">
              {formatCurrency(totalRevenuePlan)}
            </Text>
            <Text fontSize="xs" color={mutedText} mt={1}>
              Planned Revenue
            </Text>
          </VStack>
        </Box>

        {/* Card 3: Total Planned Value */}
        <Box
          p={4}
          borderWidth="1px"
          borderRadius="md"
          borderColor={borderCol}
          bg={cardBg}
        >
          <VStack align="stretch" gap={1}>
            <Text fontSize="sm" color={mutedText} fontWeight="medium">
              Total Planned Value
            </Text>
            <Text fontSize="xl" fontWeight="bold">
              {formatCurrency(totalPlannedValue)}
            </Text>
            <Text fontSize="xs" color={mutedText} mt={1}>
              Planned Value
            </Text>
          </VStack>
        </Box>

        {/* Card 4: Total Actual AC */}
        <Box
          p={4}
          borderWidth="1px"
          borderRadius="md"
          borderColor={borderCol}
          bg={cardBg}
        >
          <VStack align="stretch" gap={1}>
            <Text fontSize="sm" color={mutedText} fontWeight="medium">
              Total Actual AC
            </Text>
            <Text fontSize="xl" fontWeight="bold">
              {formatCurrency(totalActualAc)}
            </Text>
            <Text fontSize="xs" color={mutedText} mt={1}>
              Actual Cost
            </Text>
          </VStack>
        </Box>

        {/* Card 5: Total Forecast EAC */}
        <Box
          p={4}
          borderWidth="1px"
          borderRadius="md"
          borderColor={borderCol}
          bg={cardBg}
        >
          <VStack align="stretch" gap={1}>
            <Text fontSize="sm" color={mutedText} fontWeight="medium">
              Total Forecast EAC
            </Text>
            <Text fontSize="xl" fontWeight="bold">
              {formatCurrency(totalForecastEac)}
            </Text>
            <Text fontSize="xs" color={mutedText} mt={1}>
              Estimate at Completion
            </Text>
          </VStack>
        </Box>

        {/* Card 6: Total Earned EV */}
        <Box
          p={4}
          borderWidth="1px"
          borderRadius="md"
          borderColor={borderCol}
          bg={cardBg}
        >
          <VStack align="stretch" gap={1}>
            <Text fontSize="sm" color={mutedText} fontWeight="medium">
              Total Earned EV
            </Text>
            <Text fontSize="xl" fontWeight="bold">
              {formatCurrency(totalEarnedEv)}
            </Text>
            <Text fontSize="xs" color={mutedText} mt={1}>
              Earned Value
            </Text>
          </VStack>
        </Box>

        {/* Card 7: Cost Element Count */}
        <Box
          p={4}
          borderWidth="1px"
          borderRadius="md"
          borderColor={borderCol}
          bg={cardBg}
        >
          <VStack align="stretch" gap={1}>
            <Text fontSize="sm" color={mutedText} fontWeight="medium">
              Cost Elements
            </Text>
            <Text fontSize="xl" fontWeight="bold">
              {costElementCount}
            </Text>
            <Text fontSize="xs" color={mutedText} mt={1}>
              Total cost elements in baseline
            </Text>
          </VStack>
        </Box>
      </Grid>
    </Box>
  )
}
