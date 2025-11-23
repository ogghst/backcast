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
  FiMinus,
  FiTrendingDown,
  FiTrendingUp,
} from "react-icons/fi"
import {
  type EarnedValueCostElementPublic,
  type EarnedValueProjectPublic,
  EarnedValueService,
  type EarnedValueWBEPublic,
  type EVMIndicesCostElementPublic,
  type EVMIndicesProjectPublic,
  type EVMIndicesWBEPublic,
  EvmMetricsService,
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

  const { data: earnedValue, isLoading: isLoadingEarnedValue } = useQuery<
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

  const evmMetricsQueryKey = [
    "evm-metrics",
    level,
    level === "project" ? projectId : level === "wbe" ? wbeId : costElementId,
    controlDate,
  ]

  const { data: evmMetrics, isLoading: isLoadingEvmMetrics } = useQuery<
    EVMIndicesProjectPublic | EVMIndicesWBEPublic | EVMIndicesCostElementPublic
  >({
    queryKey: evmMetricsQueryKey,
    queryFn: () => {
      if (level === "project" && projectId) {
        return EvmMetricsService.getProjectEvmMetricsEndpoint({
          projectId: projectId,
        })
      }
      if (level === "wbe" && wbeId && projectId) {
        return EvmMetricsService.getWbeEvmMetricsEndpoint({
          projectId: projectId,
          wbeId: wbeId,
        })
      }
      if (level === "cost-element" && costElementId && projectId) {
        return EvmMetricsService.getCostElementEvmMetricsEndpoint({
          projectId: projectId,
          costElementId: costElementId,
        })
      }
      throw new Error(
        "Invalid props: missing required IDs for EVM metrics query",
      )
    },
    enabled:
      (level === "project" && !!projectId) ||
      (level === "wbe" && !!wbeId && !!projectId) ||
      (level === "cost-element" && !!costElementId && !!projectId),
  })

  const isLoading = isLoadingEarnedValue || isLoadingEvmMetrics

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

  const formatIndex = (value: string | number | null | undefined): string => {
    if (value === null || value === undefined) {
      return "N/A"
    }
    const numValue = typeof value === "string" ? Number(value) : value
    if (Number.isNaN(numValue)) {
      return "N/A"
    }
    return numValue.toFixed(2)
  }

  const formatTcpi = (value: string | number | null | undefined): string => {
    if (value === null || value === undefined) {
      return "N/A"
    }
    if (value === "overrun") {
      return "overrun"
    }
    const numValue = typeof value === "string" ? Number(value) : value
    if (Number.isNaN(numValue)) {
      return "N/A"
    }
    return numValue.toFixed(2)
  }

  const formatVariance = (
    value: string | number | null | undefined,
  ): string => {
    return formatCurrency(value)
  }

  type StatusIndicator = {
    color: string
    icon: typeof FiTrendingUp
    label: string
  }

  const getCpiStatus = (cpi: string | null | undefined): StatusIndicator => {
    if (cpi === null || cpi === undefined) {
      return {
        color: "gray.500",
        icon: FiMinus,
        label: "N/A",
      }
    }
    const numValue = Number(cpi)
    if (Number.isNaN(numValue)) {
      return {
        color: "gray.500",
        icon: FiMinus,
        label: "N/A",
      }
    }
    if (numValue < 0.95) {
      return {
        color: "red.500",
        icon: FiTrendingDown,
        label: "Over Budget",
      }
    }
    if (numValue < 1.0) {
      return {
        color: "yellow.500",
        icon: FiMinus,
        label: "On Target",
      }
    }
    return {
      color: "green.500",
      icon: FiTrendingUp,
      label: "Under Budget",
    }
  }

  const getSpiStatus = (spi: string | null | undefined): StatusIndicator => {
    if (spi === null || spi === undefined) {
      return {
        color: "gray.500",
        icon: FiMinus,
        label: "N/A",
      }
    }
    const numValue = Number(spi)
    if (Number.isNaN(numValue)) {
      return {
        color: "gray.500",
        icon: FiMinus,
        label: "N/A",
      }
    }
    if (numValue < 0.95) {
      return {
        color: "red.500",
        icon: FiTrendingDown,
        label: "Behind Schedule",
      }
    }
    if (numValue < 1.0) {
      return {
        color: "yellow.500",
        icon: FiMinus,
        label: "On Schedule",
      }
    }
    return {
      color: "green.500",
      icon: FiTrendingUp,
      label: "Ahead of Schedule",
    }
  }

  const getTcpiStatus = (tcpi: string | null | undefined): StatusIndicator => {
    if (tcpi === null || tcpi === undefined) {
      return {
        color: "gray.500",
        icon: FiMinus,
        label: "N/A",
      }
    }
    if (tcpi === "overrun") {
      return {
        color: "red.500",
        icon: FiAlertCircle,
        label: "Overrun",
      }
    }
    const numValue = Number(tcpi)
    if (Number.isNaN(numValue)) {
      return {
        color: "gray.500",
        icon: FiMinus,
        label: "N/A",
      }
    }
    if (numValue <= 1.0) {
      return {
        color: "green.500",
        icon: FiTrendingUp,
        label: "On Track",
      }
    }
    if (numValue <= 1.1) {
      return {
        color: "yellow.500",
        icon: FiMinus,
        label: "At Risk",
      }
    }
    return {
      color: "red.500",
      icon: FiTrendingDown,
      label: "Over Target",
    }
  }

  const getCvStatus = (
    cv: string | number | null | undefined,
  ): StatusIndicator => {
    if (cv === null || cv === undefined) {
      return {
        color: "gray.500",
        icon: FiMinus,
        label: "N/A",
      }
    }
    const numValue = typeof cv === "string" ? Number(cv) : cv
    if (Number.isNaN(numValue)) {
      return {
        color: "gray.500",
        icon: FiMinus,
        label: "N/A",
      }
    }
    if (numValue < 0) {
      return {
        color: "red.500",
        icon: FiTrendingDown,
        label: "Over Budget",
      }
    }
    if (numValue === 0) {
      return {
        color: "yellow.500",
        icon: FiMinus,
        label: "On Budget",
      }
    }
    return {
      color: "green.500",
      icon: FiTrendingUp,
      label: "Under Budget",
    }
  }

  const getSvStatus = (
    sv: string | number | null | undefined,
  ): StatusIndicator => {
    if (sv === null || sv === undefined) {
      return {
        color: "gray.500",
        icon: FiMinus,
        label: "N/A",
      }
    }
    const numValue = typeof sv === "string" ? Number(sv) : sv
    if (Number.isNaN(numValue)) {
      return {
        color: "gray.500",
        icon: FiMinus,
        label: "N/A",
      }
    }
    if (numValue < 0) {
      return {
        color: "red.500",
        icon: FiTrendingDown,
        label: "Behind Schedule",
      }
    }
    if (numValue === 0) {
      return {
        color: "yellow.500",
        icon: FiMinus,
        label: "On Schedule",
      }
    }
    return {
      color: "green.500",
      icon: FiTrendingUp,
      label: "Ahead of Schedule",
    }
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
            lg: "repeat(4, 1fr)",
          }}
          gap={4}
        >
          {[1, 2, 3, 4, 5, 6, 7, 8, 9].map((i) => (
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
  // Get EAC from evmMetrics (preferred) or earnedValue (fallback)
  const forecastEac = evmMetrics?.eac ?? earnedValue?.eac
  const forecastedQuality = earnedValue?.forecasted_quality

  // EVM metrics data (may be null/undefined)
  const cpi = evmMetrics?.cpi
  const spi = evmMetrics?.spi
  const tcpi = evmMetrics?.tcpi
  const costVariance = evmMetrics?.cost_variance
  const scheduleVariance = evmMetrics?.schedule_variance

  // Status indicators
  const cpiStatus = getCpiStatus(cpi)
  const spiStatus = getSpiStatus(spi)
  const tcpiStatus = getTcpiStatus(tcpi)
  const cvStatus = getCvStatus(costVariance)
  const svStatus = getSvStatus(scheduleVariance)

  // Icon components
  const CpiIcon = cpiStatus.icon
  const SpiIcon = spiStatus.icon
  const TcpiIcon = tcpiStatus.icon
  const CvIcon = cvStatus.icon
  const SvIcon = svStatus.icon

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
          lg: "repeat(4, 1fr)",
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

        {/* Card 3: Estimate at Completion (EAC) */}
        <Box
          p={4}
          borderWidth="1px"
          borderRadius="md"
          borderColor={borderCol}
          bg={cardBg}
        >
          <VStack align="stretch" gap={1}>
            <Text fontSize="sm" color={mutedText} fontWeight="medium">
              Estimate at Completion (EAC)
            </Text>
            <Text fontSize="xl" fontWeight="bold">
              {formatCurrency(forecastEac)}
            </Text>
            <Text fontSize="xs" color={mutedText} mt={1}>
              Current Forecast
            </Text>
          </VStack>
        </Box>

        {/* Card 4: Percent Complete */}
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

        {/* Card 5: Cost Performance Index (CPI) */}
        <Box
          p={4}
          borderWidth="1px"
          borderRadius="md"
          borderColor={borderCol}
          bg={cardBg}
        >
          <VStack align="stretch" gap={1}>
            <Text fontSize="sm" color={mutedText} fontWeight="medium">
              Cost Performance Index (CPI)
            </Text>
            <Text fontSize="xl" fontWeight="bold" color={cpiStatus.color}>
              {formatIndex(cpi)}
            </Text>
            <Text fontSize="xs" color={cpiStatus.color} mt={1}>
              <CpiIcon style={{ display: "inline", marginRight: "4px" }} />
              {cpiStatus.label}
            </Text>
          </VStack>
        </Box>

        {/* Card 6: Schedule Performance Index (SPI) */}
        <Box
          p={4}
          borderWidth="1px"
          borderRadius="md"
          borderColor={borderCol}
          bg={cardBg}
        >
          <VStack align="stretch" gap={1}>
            <Text fontSize="sm" color={mutedText} fontWeight="medium">
              Schedule Performance Index (SPI)
            </Text>
            <Text fontSize="xl" fontWeight="bold" color={spiStatus.color}>
              {formatIndex(spi)}
            </Text>
            <Text fontSize="xs" color={spiStatus.color} mt={1}>
              <SpiIcon style={{ display: "inline", marginRight: "4px" }} />
              {spiStatus.label}
            </Text>
          </VStack>
        </Box>

        {/* Card 7: To-Complete Performance Index (TCPI) */}
        <Box
          p={4}
          borderWidth="1px"
          borderRadius="md"
          borderColor={borderCol}
          bg={cardBg}
        >
          <VStack align="stretch" gap={1}>
            <Text fontSize="sm" color={mutedText} fontWeight="medium">
              To-Complete Performance Index (TCPI)
            </Text>
            <Text fontSize="xl" fontWeight="bold" color={tcpiStatus.color}>
              {formatTcpi(tcpi)}
            </Text>
            <Text fontSize="xs" color={tcpiStatus.color} mt={1}>
              <TcpiIcon style={{ display: "inline", marginRight: "4px" }} />
              {tcpiStatus.label}
            </Text>
          </VStack>
        </Box>

        {/* Card 8: Cost Variance (CV) */}
        <Box
          p={4}
          borderWidth="1px"
          borderRadius="md"
          borderColor={borderCol}
          bg={cardBg}
        >
          <VStack align="stretch" gap={1}>
            <Text fontSize="sm" color={mutedText} fontWeight="medium">
              Cost Variance (CV)
            </Text>
            <Text fontSize="xl" fontWeight="bold" color={cvStatus.color}>
              {formatVariance(costVariance)}
            </Text>
            <Text fontSize="xs" color={cvStatus.color} mt={1}>
              <CvIcon style={{ display: "inline", marginRight: "4px" }} />
              {cvStatus.label}
            </Text>
          </VStack>
        </Box>

        {/* Card 9: Schedule Variance (SV) */}
        <Box
          p={4}
          borderWidth="1px"
          borderRadius="md"
          borderColor={borderCol}
          bg={cardBg}
        >
          <VStack align="stretch" gap={1}>
            <Text fontSize="sm" color={mutedText} fontWeight="medium">
              Schedule Variance (SV)
            </Text>
            <Text fontSize="xl" fontWeight="bold" color={svStatus.color}>
              {formatVariance(scheduleVariance)}
            </Text>
            <Text fontSize="xs" color={svStatus.color} mt={1}>
              <SvIcon style={{ display: "inline", marginRight: "4px" }} />
              {svStatus.label}
            </Text>
          </VStack>
        </Box>

        {/* Card 10: Forecasted Quality */}
        <Box
          p={4}
          borderWidth="1px"
          borderRadius="md"
          borderColor={borderCol}
          bg={cardBg}
        >
          <VStack align="stretch" gap={1}>
            <Text fontSize="sm" color={mutedText} fontWeight="medium">
              Forecasted Quality
            </Text>
            <Text fontSize="xl" fontWeight="bold">
              {formatPercent(forecastedQuality)}
            </Text>
            <Text fontSize="xs" color={mutedText} mt={1}>
              Percentage of EAC from forecasts
            </Text>
          </VStack>
        </Box>
      </Grid>
    </Box>
  )
}
