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
  type EarnedValueCostElementPublic,
  type EarnedValueProjectPublic,
  EarnedValueService,
  type EarnedValueWBEPublic,
} from "@/client"
import { useColorModeValue } from "@/components/ui/color-mode"
import { useTimeMachine } from "@/context/TimeMachineContext"

interface EarnedValueSummaryProps {
  level: "project" | "wbe" | "cost-element"
  projectId?: string
  wbeId?: string
  costElementId?: string
}

export default function EarnedValueSummary({
  level,
  projectId,
  wbeId,
  costElementId,
}: EarnedValueSummaryProps) {
  const { controlDate } = useTimeMachine()
  // Theme-aware colors (declare before early returns)
  const cardBg = useColorModeValue("bg.surface", "bg.surface")
  const borderCol = useColorModeValue("border", "border")
  const mutedText = useColorModeValue("fg.muted", "fg.muted")

  const queryKey = [
    "earned-value",
    level,
    level === "project" ? projectId : level === "wbe" ? wbeId : costElementId,
    controlDate,
  ]

  const { data: earnedValue, isLoading } = useQuery<
    | EarnedValueProjectPublic
    | EarnedValueWBEPublic
    | EarnedValueCostElementPublic
  >({
    queryKey,
    queryFn: () => {
      if (level === "project" && projectId) {
        return EarnedValueService.getProjectEarnedValue({
          projectId: projectId,
        })
      }
      if (level === "wbe" && wbeId && projectId) {
        return EarnedValueService.getWbeEarnedValue({
          projectId: projectId,
          wbeId: wbeId,
        })
      }
      if (level === "cost-element" && costElementId && projectId) {
        return EarnedValueService.getCostElementEarnedValue({
          projectId: projectId,
          costElementId: costElementId,
        })
      }
      throw new Error(
        "Invalid props: missing required IDs for earned value query",
      )
    },
    enabled:
      (level === "project" && !!projectId) ||
      (level === "wbe" && !!wbeId && !!projectId) ||
      (level === "cost-element" && !!costElementId && !!projectId),
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

  const formatPercent = (value: string | number | null | undefined): string => {
    if (value === null || value === undefined) {
      return "N/A"
    }
    const numValue = typeof value === "string" ? Number(value) : value
    if (Number.isNaN(numValue)) {
      return "N/A"
    }
    return `${(numValue * 100).toFixed(2)}%`
  }

  if (isLoading) {
    return (
      <Box mb={6}>
        <Heading size="md" mb={4}>
          Earned Value Summary
        </Heading>
        <Grid
          templateColumns={{
            base: "1fr",
            md: "repeat(2, 1fr)",
            lg: "repeat(3, 1fr)",
          }}
          gap={4}
        >
          {[1, 2, 3].map((i) => (
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

  if (!earnedValue) {
    return null
  }

  const earnedValueNum = Number(earnedValue.earned_value || 0)
  const budgetBacNum = Number(earnedValue.budget_bac || 0)
  const percentCompleteNum = Number(earnedValue.percent_complete || 0)

  return (
    <Box mb={6}>
      <Heading size="md" mb={4}>
        Earned Value Summary
      </Heading>
      <Text fontSize="sm" color={mutedText} mb={4}>
        Control Date: {new Date(controlDate).toLocaleDateString()}
      </Text>
      <Grid
        templateColumns={{
          base: "1fr",
          md: "repeat(2, 1fr)",
          lg: "repeat(3, 1fr)",
        }}
        gap={4}
      >
        {/* Card 1: Earned Value */}
        <Box
          p={4}
          borderWidth="1px"
          borderRadius="md"
          borderColor={borderCol}
          bg={cardBg}
        >
          <VStack align="stretch" gap={1}>
            <Text fontSize="sm" color={mutedText} fontWeight="medium">
              Earned Value (EV)
            </Text>
            <Text fontSize="xl" fontWeight="bold">
              {formatCurrency(earnedValueNum)}
            </Text>
            <Text fontSize="xs" color={mutedText} mt={1}>
              Budgeted Cost of Work Performed
            </Text>
          </VStack>
        </Box>

        {/* Card 2: Budget at Completion */}
        <Box
          p={4}
          borderWidth="1px"
          borderRadius="md"
          borderColor={borderCol}
          bg={cardBg}
        >
          <VStack align="stretch" gap={1}>
            <Text fontSize="sm" color={mutedText} fontWeight="medium">
              Budget at Completion (BAC)
            </Text>
            <Text fontSize="xl" fontWeight="bold">
              {formatCurrency(budgetBacNum)}
            </Text>
            <Text fontSize="xs" color={mutedText} mt={1}>
              Total Planned Budget
            </Text>
          </VStack>
        </Box>

        {/* Card 3: Percent Complete */}
        <Box
          p={4}
          borderWidth="1px"
          borderRadius="md"
          borderColor={borderCol}
          bg={cardBg}
        >
          <VStack align="stretch" gap={1}>
            <Text fontSize="sm" color={mutedText} fontWeight="medium">
              Physical Completion
            </Text>
            <Text fontSize="xl" fontWeight="bold">
              {formatPercent(percentCompleteNum)}
            </Text>
            <Text fontSize="xs" color={mutedText} mt={1}>
              EV / BAC
            </Text>
          </VStack>
        </Box>
      </Grid>
    </Box>
  )
}
