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
  ArcElement,
  BarElement,
  CategoryScale,
  Chart as ChartJS,
  Legend,
  LinearScale,
  Tooltip,
} from "chart.js"
import { Bar, Doughnut } from "react-chartjs-2"
import { type BudgetSummaryPublic, BudgetSummaryService } from "@/client"

// Register Chart.js components
ChartJS.register(
  ArcElement,
  BarElement,
  CategoryScale,
  LinearScale,
  Tooltip,
  Legend,
)

interface BudgetSummaryProps {
  level: "project" | "wbe"
  projectId?: string
  wbeId?: string
}

export default function BudgetSummary({
  level,
  projectId,
  wbeId,
}: BudgetSummaryProps) {
  const queryKey =
    level === "project"
      ? ["budget-summary", "project", projectId]
      : ["budget-summary", "wbe", wbeId]

  const { data: summary, isLoading } = useQuery<BudgetSummaryPublic>({
    queryKey,
    queryFn: () => {
      if (level === "project" && projectId) {
        return BudgetSummaryService.getProjectBudgetSummary({
          projectId: projectId,
        })
      }
      if (level === "wbe" && wbeId) {
        return BudgetSummaryService.getWbeBudgetSummary({ wbeId: wbeId })
      }
      throw new Error("Invalid props: missing projectId or wbeId")
    },
    enabled:
      (level === "project" && !!projectId) || (level === "wbe" && !!wbeId),
  })

  if (isLoading) {
    return (
      <Box mb={6}>
        <Heading size="md" mb={4}>
          Budget Summary
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

  const revenueLimit = Number(summary.revenue_limit)
  const totalRevenueAllocated = Number(summary.total_revenue_allocated)
  const totalBudgetBac = Number(summary.total_budget_bac)
  const totalRevenuePlan = Number(summary.total_revenue_plan)
  const remainingRevenue = Number(summary.remaining_revenue)
  const utilizationPercent = summary.revenue_utilization_percent

  // Determine color based on utilization (using hex colors for Chart.js)
  const getUtilizationColorHex = (percent: number) => {
    if (percent < 80) return "#48bb78" // green.500
    if (percent <= 95) return "#ed8936" // yellow.500
    return "#f56565" // red.500
  }

  // Get color name for text (using Chakra color tokens)
  const getUtilizationColor = (percent: number) => {
    if (percent < 80) return "green.500"
    if (percent <= 95) return "yellow.500"
    return "red.500"
  }

  // Doughnut chart data for revenue utilization
  const revenueChartData = {
    labels: ["Allocated", "Remaining"],
    datasets: [
      {
        data: [totalRevenueAllocated, remainingRevenue],
        backgroundColor: [
          getUtilizationColorHex(utilizationPercent),
          "#e2e8f0", // gray.200
        ],
        borderWidth: 0,
      },
    ],
  }

  const revenueChartOptions = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        position: "bottom" as const,
        labels: {
          padding: 10,
          font: {
            size: 12,
          },
        },
      },
      tooltip: {
        callbacks: {
          label: (context: any) => {
            const label = context.label || ""
            const value = context.parsed || 0
            return `${label}: €${value.toLocaleString("en-US", {
              minimumFractionDigits: 2,
              maximumFractionDigits: 2,
            })}`
          },
        },
      },
    },
  }

  // Bar chart data for budget vs revenue comparison
  const comparisonChartData = {
    labels: ["Budget BAC", "Revenue Plan"],
    datasets: [
      {
        label: "Amount (€)",
        data: [totalBudgetBac, totalRevenuePlan],
        backgroundColor: ["#63b3ed", "#68d391"], // blue.400 and green.400
        borderRadius: 4,
      },
    ],
  }

  const comparisonChartOptions = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        display: false,
      },
      tooltip: {
        callbacks: {
          label: (context: any) => {
            const value = context.parsed.y || 0
            return `€${value.toLocaleString("en-US", {
              minimumFractionDigits: 2,
              maximumFractionDigits: 2,
            })}`
          },
        },
      },
    },
    scales: {
      y: {
        beginAtZero: true,
        ticks: {
          callback: (value: any) => `€${value.toLocaleString()}`,
        },
      },
    },
  }

  return (
    <Box mb={6}>
      <Heading size="md" mb={4}>
        Budget Summary
      </Heading>

      {/* Summary Cards */}
      <Grid
        templateColumns={{
          base: "1fr",
          md: "repeat(2, 1fr)",
          lg: "repeat(4, 1fr)",
        }}
        gap={4}
        mb={6}
      >
        <Box
          p={4}
          borderWidth="1px"
          borderRadius="md"
          borderColor="gray.200"
          bg="white"
        >
          <VStack align="stretch" gap={1}>
            <Text fontSize="sm" color="gray.600" fontWeight="medium">
              Revenue Limit
            </Text>
            <Text fontSize="xl" fontWeight="bold">
              €
              {revenueLimit.toLocaleString("en-US", {
                minimumFractionDigits: 2,
                maximumFractionDigits: 2,
              })}
            </Text>
          </VStack>
        </Box>

        <Box
          p={4}
          borderWidth="1px"
          borderRadius="md"
          borderColor="gray.200"
          bg="white"
        >
          <VStack align="stretch" gap={1}>
            <Text fontSize="sm" color="gray.600" fontWeight="medium">
              Total Allocated
            </Text>
            <Text fontSize="xl" fontWeight="bold">
              €
              {totalRevenueAllocated.toLocaleString("en-US", {
                minimumFractionDigits: 2,
                maximumFractionDigits: 2,
              })}
            </Text>
            <Text
              fontSize="xs"
              color={getUtilizationColor(utilizationPercent)}
              mt={1}
            >
              {utilizationPercent.toFixed(1)}% utilized
            </Text>
          </VStack>
        </Box>

        <Box
          p={4}
          borderWidth="1px"
          borderRadius="md"
          borderColor="gray.200"
          bg="white"
        >
          <VStack align="stretch" gap={1}>
            <Text fontSize="sm" color="gray.600" fontWeight="medium">
              Total Budget (BAC)
            </Text>
            <Text fontSize="xl" fontWeight="bold">
              €
              {totalBudgetBac.toLocaleString("en-US", {
                minimumFractionDigits: 2,
                maximumFractionDigits: 2,
              })}
            </Text>
          </VStack>
        </Box>

        <Box
          p={4}
          borderWidth="1px"
          borderRadius="md"
          borderColor="gray.200"
          bg="white"
        >
          <VStack align="stretch" gap={1}>
            <Text fontSize="sm" color="gray.600" fontWeight="medium">
              Total Revenue Plan
            </Text>
            <Text fontSize="xl" fontWeight="bold">
              €
              {totalRevenuePlan.toLocaleString("en-US", {
                minimumFractionDigits: 2,
                maximumFractionDigits: 2,
              })}
            </Text>
          </VStack>
        </Box>
      </Grid>

      {/* Charts */}
      <Grid
        templateColumns={{
          base: "1fr",
          md: "repeat(2, 1fr)",
        }}
        gap={4}
      >
        <Box
          p={4}
          borderWidth="1px"
          borderRadius="md"
          borderColor="gray.200"
          bg="white"
        >
          <VStack align="stretch" gap={2}>
            <Heading size="sm">Revenue Utilization</Heading>
            <Box h="250px">
              <Doughnut data={revenueChartData} options={revenueChartOptions} />
            </Box>
            <Text fontSize="xs" color="gray.600" textAlign="center">
              Utilization: {utilizationPercent.toFixed(1)}% | Remaining: €
              {remainingRevenue.toLocaleString("en-US", {
                minimumFractionDigits: 2,
                maximumFractionDigits: 2,
              })}
            </Text>
          </VStack>
        </Box>

        <Box
          p={4}
          borderWidth="1px"
          borderRadius="md"
          borderColor="gray.200"
          bg="white"
        >
          <VStack align="stretch" gap={2}>
            <Heading size="sm">Budget vs Revenue</Heading>
            <Box h="250px">
              <Bar
                data={comparisonChartData}
                options={comparisonChartOptions}
              />
            </Box>
            <Text fontSize="xs" color="gray.600" textAlign="center">
              Comparison of total budget and revenue allocations
            </Text>
          </VStack>
        </Box>
      </Grid>
    </Box>
  )
}
