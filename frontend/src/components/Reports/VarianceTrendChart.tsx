import { Box, Heading, Text, VStack } from "@chakra-ui/react"
import {
  CategoryScale,
  Chart as ChartJS,
  type ChartOptions,
  Legend,
  LinearScale,
  LineElement,
  PointElement,
  TimeScale,
  Tooltip,
} from "chart.js"
import { useColorModeValue } from "@/components/ui/color-mode"
import "chartjs-adapter-date-fns"
import { useQuery } from "@tanstack/react-query"
import { Line } from "react-chartjs-2"
import { ReportsService, type VarianceTrendPublic } from "@/client"
import { useTimeMachine } from "@/context/TimeMachineContext"

// Register Chart.js components
ChartJS.register(
  CategoryScale,
  LinearScale,
  TimeScale,
  PointElement,
  LineElement,
  Tooltip,
  Legend,
)

interface VarianceTrendChartProps {
  projectId: string
  wbeId?: string
  costElementId?: string
}

export default function VarianceTrendChart({
  projectId,
  wbeId,
  costElementId,
}: VarianceTrendChartProps) {
  const { controlDate } = useTimeMachine()
  const axisColor = useColorModeValue("#2D3748", "#E2E8F0")
  const gridColor = useColorModeValue(
    "rgba(0,0,0,0.1)",
    "rgba(255,255,255,0.12)",
  )

  const queryKey = [
    "variance-trend",
    projectId,
    controlDate,
    wbeId,
    costElementId,
  ]

  const {
    data: trend,
    isLoading,
    error,
  } = useQuery<VarianceTrendPublic>({
    queryKey,
    queryFn: () =>
      ReportsService.getVarianceTrendEndpoint({
        projectId: projectId,
        wbeId: wbeId,
        costElementId: costElementId,
      }),
    enabled: !!projectId,
  })

  if (isLoading) {
    return (
      <Box borderWidth="1px" borderRadius="lg" p={4} bg="bg.surface">
        <Text>Loading variance trend...</Text>
      </Box>
    )
  }

  if (error) {
    return (
      <Box borderWidth="1px" borderRadius="lg" p={4} bg="bg.surface">
        <Text color="fg.error">
          Error loading variance trend:{" "}
          {error instanceof Error ? error.message : "Unknown error"}
        </Text>
      </Box>
    )
  }

  if (!trend || !trend.trend_points || trend.trend_points.length === 0) {
    return (
      <Box borderWidth="1px" borderRadius="lg" p={4} bg="bg.surface">
        <Text color="fg.muted">No variance trend data available.</Text>
      </Box>
    )
  }

  // Prepare chart data
  const labels = trend.trend_points.map((point) => new Date(point.month))
  const cvData = trend.trend_points.map((point) => Number(point.cost_variance))
  const svData = trend.trend_points.map((point) =>
    Number(point.schedule_variance),
  )

  const chartData = {
    labels,
    datasets: [
      {
        label: "Cost Variance (CV)",
        data: cvData,
        borderColor: "#f56565", // red.500
        backgroundColor: "rgba(245, 101, 101, 0.1)",
        borderWidth: 2,
        fill: false,
        tension: 0.1,
      },
      {
        label: "Schedule Variance (SV)",
        data: svData,
        borderColor: "#ed8936", // orange.500
        backgroundColor: "rgba(237, 137, 54, 0.1)",
        borderWidth: 2,
        fill: false,
        tension: 0.1,
      },
    ],
  }

  const chartOptions: ChartOptions<"line"> = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        position: "top" as const,
        labels: {
          color: axisColor,
        },
      },
      tooltip: {
        callbacks: {
          label: (context) => {
            const label = context.dataset.label || ""
            const value = context.parsed.y || 0
            const point = trend.trend_points?.[context.dataIndex]
            let cvPercentage = "N/A"
            let svPercentage = "N/A"

            if (point) {
              if (label.includes("CV") && point.cv_percentage !== null) {
                cvPercentage = `${Number(point.cv_percentage).toFixed(2)}%`
              }
              if (label.includes("SV") && point.sv_percentage !== null) {
                svPercentage = `${Number(point.sv_percentage).toFixed(2)}%`
              }
            }

            return `${label}: €${value.toLocaleString("en-US", {
              minimumFractionDigits: 2,
              maximumFractionDigits: 2,
            })} ${
              label.includes("CV")
                ? `(${cvPercentage})`
                : label.includes("SV")
                  ? `(${svPercentage})`
                  : ""
            }`
          },
        },
      },
    },
    scales: {
      x: {
        type: "time" as const,
        time: {
          unit: "month" as const,
          displayFormats: {
            month: "MMM yyyy",
          },
        },
        grid: { color: gridColor },
        ticks: { color: axisColor },
      },
      y: {
        grid: { color: gridColor },
        ticks: {
          color: axisColor,
          callback: (value) => {
            return `€${Number(value).toLocaleString("en-US", {
              minimumFractionDigits: 0,
              maximumFractionDigits: 0,
            })}`
          },
        },
      },
    },
  }

  const levelLabel = costElementId ? "Cost Element" : wbeId ? "WBE" : "Project"

  return (
    <Box
      borderWidth="1px"
      borderRadius="lg"
      p={{ base: 3, md: 4 }}
      bg="bg.surface"
      mb={4}
    >
      <VStack gap={4} align="stretch">
        <Heading size={{ base: "sm", md: "md" }}>
          Variance Trend Analysis ({levelLabel} Level)
        </Heading>
        <Box height={{ base: "300px", md: "400px" }}>
          <Line data={chartData} options={chartOptions} />
        </Box>
        <Text fontSize={{ base: "xs", md: "sm" }} color="fg.muted">
          Monthly variance evolution from project start to control date. Red
          line shows Cost Variance (CV), orange line shows Schedule Variance
          (SV). Negative values indicate over-budget or behind-schedule
          performance.
        </Text>
      </VStack>
    </Box>
  )
}
