import {
  Badge,
  Box,
  Flex,
  Heading,
  HStack,
  IconButton,
  SkeletonText,
  Stack,
  Text,
  Tooltip,
} from "@chakra-ui/react"
import { useQuery } from "@tanstack/react-query"
import { useNavigate } from "@tanstack/react-router"
import { useState } from "react"
import {
  FiAlertCircle,
  FiHelpCircle,
  FiMinus,
  FiTrendingDown,
  FiTrendingUp,
} from "react-icons/fi"
import {
  ReportsService,
  type VarianceAnalysisReportPublic,
  type VarianceAnalysisReportRowPublic,
} from "@/client"
import { DataTable } from "@/components/DataTable/DataTable"
import type { ColumnDefExtended } from "@/components/DataTable/types"
import VarianceTrendChart from "@/components/Reports/VarianceTrendChart"
import { Checkbox } from "@/components/ui/checkbox"
import { useColorModeValue } from "@/components/ui/color-mode"
import { Radio, RadioGroup } from "@/components/ui/radio"
import { useTimeMachine } from "@/context/TimeMachineContext"

// Formatting helpers
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

const formatPercentage = (
  value: string | number | null | undefined,
): string => {
  if (value === null || value === undefined) {
    return "N/A"
  }
  const numValue = typeof value === "string" ? Number(value) : value
  if (Number.isNaN(numValue)) {
    return "N/A"
  }
  return `${numValue.toFixed(2)}%`
}

// Status indicator helpers
type StatusIndicator = {
  color: string
  icon: typeof FiTrendingUp
  label: string
}

const getVarianceStatus = (
  value: string | number | null | undefined,
): StatusIndicator => {
  if (value === null || value === undefined) {
    return {
      color: "gray.500",
      icon: FiMinus,
      label: "N/A",
    }
  }
  const numValue = typeof value === "string" ? Number(value) : value
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
      label: "Negative",
    }
  }
  if (numValue === 0) {
    return {
      color: "gray.500",
      icon: FiMinus,
      label: "Zero",
    }
  }
  return {
    color: "green.500",
    icon: FiTrendingUp,
    label: "Positive",
  }
}

const getSeverityStatus = (
  severity: string | null | undefined,
): StatusIndicator => {
  if (!severity) {
    return {
      color: "gray.500",
      icon: FiMinus,
      label: "N/A",
    }
  }
  switch (severity) {
    case "critical":
      return {
        color: "red.500",
        icon: FiAlertCircle,
        label: "Critical",
      }
    case "warning":
      return {
        color: "yellow.500",
        icon: FiAlertCircle,
        label: "Warning",
      }
    case "normal":
      return {
        color: "green.500",
        icon: FiMinus,
        label: "Normal",
      }
    default:
      return {
        color: "gray.500",
        icon: FiMinus,
        label: "N/A",
      }
  }
}

// Column definitions for variance analysis report (emphasizing variance metrics)
const reportColumns: ColumnDefExtended<VarianceAnalysisReportRowPublic>[] = [
  // Hierarchy columns
  {
    accessorKey: "wbe_name",
    header: "WBE",
    enableSorting: true,
    enableResizing: true,
    enableColumnFilter: true,
    filterType: "text",
    size: 150,
    defaultVisible: true,
  },
  {
    accessorKey: "wbe_serial_number",
    header: "Serial Number",
    enableSorting: true,
    enableResizing: true,
    size: 120,
    defaultVisible: true,
    cell: ({ getValue }) => (getValue() as string | null) || "N/A",
  },
  {
    accessorKey: "department_code",
    header: "Dept Code",
    enableSorting: true,
    enableResizing: true,
    enableColumnFilter: true,
    filterType: "text",
    size: 100,
    defaultVisible: true,
  },
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
  // Core metrics (for context)
  {
    accessorKey: "budget_bac",
    header: "BAC",
    enableSorting: true,
    enableResizing: true,
    size: 120,
    defaultVisible: true,
    cell: ({ getValue }) =>
      formatCurrency(getValue() as string | number | null | undefined),
  },
  // Variance metrics (PRIMARY FOCUS)
  {
    accessorKey: "cost_variance",
    header: () => (
      <Flex alignItems="center" gap={1}>
        <Text>CV</Text>
        <Tooltip.Root openDelay={200}>
          <Tooltip.Trigger asChild>
            <IconButton size="xs" variant="ghost" aria-label="Help">
              <FiHelpCircle size={14} />
            </IconButton>
          </Tooltip.Trigger>
          <Tooltip.Positioner>
            <Tooltip.Content maxW="300px">
              <Text fontSize="sm">
                <strong>Cost Variance (CV):</strong> CV = EV - AC. Negative
                values indicate over-budget (spent more than earned). Positive
                values indicate under-budget.
              </Text>
              <Tooltip.Arrow>
                <Tooltip.ArrowTip />
              </Tooltip.Arrow>
            </Tooltip.Content>
          </Tooltip.Positioner>
        </Tooltip.Root>
      </Flex>
    ),
    enableSorting: true,
    enableResizing: true,
    size: 120,
    defaultVisible: true,
    cell: ({ getValue }) => {
      const value = getValue() as string | number | null | undefined
      const status = getVarianceStatus(value)
      const StatusIcon = status.icon
      return (
        <Flex alignItems="center" gap={2}>
          <StatusIcon color={status.color} />
          <Text color={status.color} fontWeight="medium">
            {formatCurrency(value)}
          </Text>
        </Flex>
      )
    },
  },
  {
    accessorKey: "cv_percentage",
    header: () => (
      <Flex alignItems="center" gap={1}>
        <Text>CV%</Text>
        <Tooltip.Root openDelay={200}>
          <Tooltip.Trigger asChild>
            <IconButton size="xs" variant="ghost" aria-label="Help">
              <FiHelpCircle size={14} />
            </IconButton>
          </Tooltip.Trigger>
          <Tooltip.Positioner>
            <Tooltip.Content maxW="300px">
              <Text fontSize="sm">
                <strong>Cost Variance %:</strong> CV% = (CV / BAC) × 100. Shows
                cost variance as a percentage of budget. Critical/Warning
                thresholds are configurable.
              </Text>
              <Tooltip.Arrow>
                <Tooltip.ArrowTip />
              </Tooltip.Arrow>
            </Tooltip.Content>
          </Tooltip.Positioner>
        </Tooltip.Root>
      </Flex>
    ),
    enableSorting: true,
    enableResizing: true,
    size: 100,
    defaultVisible: true,
    cell: ({ getValue }) => {
      const value = getValue() as string | number | null | undefined
      const status = getVarianceStatus(value)
      const StatusIcon = status.icon
      return (
        <Flex alignItems="center" gap={2}>
          <StatusIcon color={status.color} />
          <Text color={status.color} fontWeight="medium">
            {formatPercentage(value)}
          </Text>
        </Flex>
      )
    },
  },
  {
    accessorKey: "schedule_variance",
    header: () => (
      <Flex alignItems="center" gap={1}>
        <Text>SV</Text>
        <Tooltip.Root openDelay={200}>
          <Tooltip.Trigger asChild>
            <IconButton size="xs" variant="ghost" aria-label="Help">
              <FiHelpCircle size={14} />
            </IconButton>
          </Tooltip.Trigger>
          <Tooltip.Positioner>
            <Tooltip.Content maxW="300px">
              <Text fontSize="sm">
                <strong>Schedule Variance (SV):</strong> SV = EV - PV. Negative
                values indicate behind-schedule (earned less than planned).
                Positive values indicate ahead-of-schedule.
              </Text>
              <Tooltip.Arrow>
                <Tooltip.ArrowTip />
              </Tooltip.Arrow>
            </Tooltip.Content>
          </Tooltip.Positioner>
        </Tooltip.Root>
      </Flex>
    ),
    enableSorting: true,
    enableResizing: true,
    size: 120,
    defaultVisible: true,
    cell: ({ getValue }) => {
      const value = getValue() as string | number | null | undefined
      const status = getVarianceStatus(value)
      const StatusIcon = status.icon
      return (
        <Flex alignItems="center" gap={2}>
          <StatusIcon color={status.color} />
          <Text color={status.color} fontWeight="medium">
            {formatCurrency(value)}
          </Text>
        </Flex>
      )
    },
  },
  {
    accessorKey: "sv_percentage",
    header: () => (
      <Flex alignItems="center" gap={1}>
        <Text>SV%</Text>
        <Tooltip.Root openDelay={200}>
          <Tooltip.Trigger asChild>
            <IconButton size="xs" variant="ghost" aria-label="Help">
              <FiHelpCircle size={14} />
            </IconButton>
          </Tooltip.Trigger>
          <Tooltip.Positioner>
            <Tooltip.Content maxW="300px">
              <Text fontSize="sm">
                <strong>Schedule Variance %:</strong> SV% = (SV / BAC) × 100.
                Shows schedule variance as a percentage of budget.
                Critical/Warning thresholds are configurable.
              </Text>
              <Tooltip.Arrow>
                <Tooltip.ArrowTip />
              </Tooltip.Arrow>
            </Tooltip.Content>
          </Tooltip.Positioner>
        </Tooltip.Root>
      </Flex>
    ),
    enableSorting: true,
    enableResizing: true,
    size: 100,
    defaultVisible: true,
    cell: ({ getValue }) => {
      const value = getValue() as string | number | null | undefined
      const status = getVarianceStatus(value)
      const StatusIcon = status.icon
      return (
        <Flex alignItems="center" gap={2}>
          <StatusIcon color={status.color} />
          <Text color={status.color} fontWeight="medium">
            {formatPercentage(value)}
          </Text>
        </Flex>
      )
    },
  },
  {
    accessorKey: "variance_severity",
    header: () => (
      <Flex alignItems="center" gap={1}>
        <Text>Severity</Text>
        <Tooltip.Root openDelay={200}>
          <Tooltip.Trigger asChild>
            <IconButton size="xs" variant="ghost" aria-label="Help">
              <FiHelpCircle size={14} />
            </IconButton>
          </Tooltip.Trigger>
          <Tooltip.Positioner>
            <Tooltip.Content maxW="300px">
              <Text fontSize="sm">
                <strong>Variance Severity:</strong> Overall severity based on
                CV% and SV% compared to configured thresholds. Critical =
                exceeds critical threshold, Warning = exceeds warning threshold,
                Normal = within acceptable range.
              </Text>
              <Tooltip.Arrow>
                <Tooltip.ArrowTip />
              </Tooltip.Arrow>
            </Tooltip.Content>
          </Tooltip.Positioner>
        </Tooltip.Root>
      </Flex>
    ),
    enableSorting: true,
    enableResizing: true,
    size: 120,
    defaultVisible: true,
    cell: ({ getValue }) => {
      const severity = getValue() as string | null | undefined
      const status = getSeverityStatus(severity)
      return (
        <Badge
          colorScheme={
            status.color === "red.500"
              ? "red"
              : status.color === "yellow.500"
                ? "yellow"
                : "green"
          }
          variant="subtle"
        >
          {status.label}
        </Badge>
      )
    },
  },
  // Performance indices (secondary, for context)
  {
    accessorKey: "cpi",
    header: "CPI",
    enableSorting: true,
    enableResizing: true,
    size: 100,
    defaultVisible: false,
    cell: ({ getValue }) => {
      const value = getValue() as string | number | null | undefined
      if (value === null || value === undefined) {
        return "N/A"
      }
      const numValue = typeof value === "string" ? Number(value) : value
      return Number.isNaN(numValue) ? "N/A" : numValue.toFixed(2)
    },
  },
  {
    accessorKey: "spi",
    header: "SPI",
    enableSorting: true,
    enableResizing: true,
    size: 100,
    defaultVisible: false,
    cell: ({ getValue }) => {
      const value = getValue() as string | number | null | undefined
      if (value === null || value === undefined) {
        return "N/A"
      }
      const numValue = typeof value === "string" ? Number(value) : value
      return Number.isNaN(numValue) ? "N/A" : numValue.toFixed(2)
    },
  },
]

interface VarianceAnalysisReportProps {
  projectId: string
}

export default function VarianceAnalysisReport({
  projectId,
}: VarianceAnalysisReportProps) {
  const { controlDate } = useTimeMachine()
  const mutedText = useColorModeValue("fg.muted", "fg.muted")
  const surfaceBg = useColorModeValue("bg.surface", "bg.surface")
  const [page, setPage] = useState(1)
  const pageSize = 25
  const navigate = useNavigate()

  // Filter and sort state
  const [showOnlyProblems, setShowOnlyProblems] = useState(true)
  const [sortBy, setSortBy] = useState<"cv" | "sv">("cv")

  const queryKey = [
    "variance-analysis-report",
    projectId,
    controlDate,
    showOnlyProblems,
    sortBy,
  ]

  const {
    data: report,
    isLoading,
    error,
  } = useQuery<VarianceAnalysisReportPublic>({
    queryKey,
    // NOTE: This method requires the OpenAPI client to be regenerated.
    // Run: bash scripts/generate-client.sh (requires backend to be running or Python deps installed)
    queryFn: () =>
      ReportsService.getProjectVarianceAnalysisReportEndpoint({
        projectId: projectId,
        showOnlyProblems: showOnlyProblems,
        sortBy: sortBy,
      }),
    enabled: !!projectId,
  })

  // Loading state
  if (isLoading) {
    return (
      <Box>
        <Stack gap={4}>
          <SkeletonText noOfLines={1} width="200px" />
          <SkeletonText noOfLines={5} width="100%" />
        </Stack>
      </Box>
    )
  }

  // Error state
  if (error) {
    return (
      <Box>
        <Stack gap={4}>
          <Box display="flex" alignItems="center" gap={2} color="fg.error">
            <FiAlertCircle />
            <Text>Error loading variance analysis report</Text>
          </Box>
          <Text fontSize="sm" color={mutedText}>
            {error instanceof Error ? error.message : "Unknown error"}
          </Text>
        </Stack>
      </Box>
    )
  }

  // Empty state
  if (!report || !report.rows || report.rows.length === 0) {
    return (
      <Box>
        <Stack gap={4}>
          <Heading size="md">Variance Analysis Report</Heading>
          <Text color={mutedText}>
            {showOnlyProblems
              ? "No problem areas found. All cost elements are performing on or ahead of plan."
              : "No cost elements found for this project."}
          </Text>
        </Stack>
      </Box>
    )
  }

  // Report data available
  const summary = report.summary

  return (
    <Box>
      <Stack gap={4}>
        <HStack justify="space-between" align="flex-start">
          <Box>
            <Heading size="md">Variance Analysis Report</Heading>
            <Text fontSize="sm" color={mutedText}>
              Control Date: {new Date(report.control_date).toLocaleDateString()}
            </Text>
          </Box>
        </HStack>

        {/* Summary Section */}
        <Flex gap={{ base: 2, md: 4 }} wrap="wrap">
          <Box
            borderWidth="1px"
            borderRadius="md"
            p={{ base: 3, md: 4 }}
            bg={surfaceBg}
            minW={{ base: "100%", sm: "150px" }}
            flex={{ base: "1", sm: "0" }}
          >
            <Text fontSize={{ base: "xs", md: "sm" }} color={mutedText} mb={1}>
              Problem Areas
            </Text>
            <Text fontSize={{ base: "xl", md: "2xl" }} fontWeight="bold">
              {report.total_problem_areas}
            </Text>
            <Text fontSize="xs" color={mutedText}>
              of{" "}
              {report.rows.length +
                (showOnlyProblems ? 0 : report.total_problem_areas)}{" "}
              cost elements
            </Text>
          </Box>
          <Box
            borderWidth="1px"
            borderRadius="md"
            p={{ base: 3, md: 4 }}
            bg={surfaceBg}
            minW={{ base: "100%", sm: "150px" }}
            flex={{ base: "1", sm: "0" }}
          >
            <Text fontSize={{ base: "xs", md: "sm" }} color={mutedText} mb={1}>
              Total CV
            </Text>
            <Text
              fontSize={{ base: "xl", md: "2xl" }}
              fontWeight="bold"
              color={summary.cost_variance < 0 ? "red.500" : "green.500"}
            >
              {formatCurrency(summary.cost_variance)}
            </Text>
          </Box>
          <Box
            borderWidth="1px"
            borderRadius="md"
            p={{ base: 3, md: 4 }}
            bg={surfaceBg}
            minW={{ base: "100%", sm: "150px" }}
            flex={{ base: "1", sm: "0" }}
          >
            <Text fontSize={{ base: "xs", md: "sm" }} color={mutedText} mb={1}>
              Total SV
            </Text>
            <Text
              fontSize={{ base: "xl", md: "2xl" }}
              fontWeight="bold"
              color={summary.schedule_variance < 0 ? "red.500" : "green.500"}
            >
              {formatCurrency(summary.schedule_variance)}
            </Text>
          </Box>
        </Flex>

        {/* Help Section - Variance Explanations */}
        <Box
          borderWidth="1px"
          borderRadius="md"
          p={{ base: 3, md: 4 }}
          bg={surfaceBg}
          borderColor="blue.200"
        >
          <HStack gap={2} mb={2} flexWrap="wrap">
            <FiHelpCircle color="blue.500" size={18} />
            <Heading size={{ base: "xs", md: "sm" }} color="blue.600">
              Understanding Variance Metrics
            </Heading>
          </HStack>
          <Stack gap={2} fontSize={{ base: "xs", md: "sm" }} color={mutedText}>
            <Text>
              <strong>Cost Variance (CV):</strong> CV = EV - AC. Measures cost
              performance. Negative values indicate over-budget (spent more than
              earned value).
            </Text>
            <Text>
              <strong>Schedule Variance (SV):</strong> SV = EV - PV. Measures
              schedule performance. Negative values indicate behind-schedule
              (earned less than planned value).
            </Text>
            <Text>
              <strong>Variance Percentages (CV%, SV%):</strong> Express
              variances as percentages of Budget at Completion (BAC). Helps
              compare variances across cost elements of different sizes.
            </Text>
            <Text>
              <strong>Severity Levels:</strong> Based on configurable
              thresholds. Critical = exceeds critical threshold, Warning =
              exceeds warning threshold, Normal = within acceptable range. Hover
              over column headers for detailed explanations.
            </Text>
          </Stack>
        </Box>

        {/* Variance Trend Chart - Hide on very small screens */}
        <Box display={{ base: "none", md: "block" }}>
          <VarianceTrendChart projectId={projectId} />
        </Box>

        {/* Filter and Sort Controls */}
        <HStack gap={{ base: 2, md: 4 }} wrap="wrap">
          <Flex alignItems="center" gap={2}>
            <Checkbox
              checked={showOnlyProblems}
              onCheckedChange={({ checked }) => setShowOnlyProblems(checked)}
            >
              Show only problem areas
            </Checkbox>
            <Text fontSize="sm" color={mutedText}>
              Filter to negative variances only
            </Text>
          </Flex>
          <Flex alignItems="center" gap={2}>
            <Text fontSize="sm" fontWeight="medium">
              Sort by:
            </Text>
            <RadioGroup
              value={sortBy}
              onValueChange={(e) => setSortBy(e.value as "cv" | "sv")}
            >
              <HStack gap={2}>
                <Radio value="cv">CV (most negative first)</Radio>
                <Radio value="sv">SV (most negative first)</Radio>
              </HStack>
            </RadioGroup>
          </Flex>
        </HStack>

        <DataTable
          data={report.rows || []}
          columns={reportColumns}
          tableId="variance-analysis-report"
          count={report.rows?.length || 0}
          page={page}
          onPageChange={setPage}
          pageSize={pageSize}
          isLoading={false}
          onRowClick={(row) => {
            // Navigate to cost element detail
            const costElementId = row.cost_element_id
            const wbeId = row.wbe_id
            navigate({
              to: "/projects/$id/wbes/$wbeId/cost-elements/$costElementId",
              params: {
                id: projectId,
                wbeId: wbeId,
                costElementId: costElementId,
              },
              search: (prev) => ({
                ...prev,
                page: prev.page ?? 1,
                tab: (prev.tab ?? "metrics") as
                  | "summary"
                  | "info"
                  | "cost-summary"
                  | "metrics"
                  | "timeline",
                view: "metrics" as const,
              }),
            })
          }}
        />
      </Stack>
    </Box>
  )
}
