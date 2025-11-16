import { Box, Heading, Text, VStack } from "@chakra-ui/react"
import {
  CategoryScale,
  type ChartDataset,
  Chart as ChartJS,
  type ChartOptions,
  Legend,
  LinearScale,
  LineElement,
  PointElement,
  TimeScale,
  Tooltip,
  type TooltipItem,
} from "chart.js"
import { useColorModeValue } from "@/components/ui/color-mode"
import "chartjs-adapter-date-fns"
import { useQuery } from "@tanstack/react-query"
import { Line } from "react-chartjs-2"
import {
  type CostElementWithSchedulePublic,
  CostTimelineService,
  EarnedValueEntriesService,
  type EarnedValueEntryPublic,
} from "@/client"
import { useTimeMachine } from "@/context/TimeMachineContext"
import { buildEarnedValueTimeline } from "@/utils/earnedValueAggregation"
import type { TimePeriod } from "@/utils/progressionCalculations"
import {
  calculateGaussianProgression,
  calculateLinearProgression,
  calculateLogarithmicProgression,
} from "@/utils/progressionCalculations"
import { aggregateTimelines } from "@/utils/timelineAggregation"
import { generateTimeSeries } from "@/utils/timeSeriesGenerator"

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

export interface BudgetTimelineProps {
  costElements: CostElementWithSchedulePublic[]
  viewMode?: "aggregated" | "multi-line" // Default: "aggregated"
  projectId?: string // Required for cost timeline fetching
  wbeIds?: string[] // Optional filter for cost timeline
  costElementIds?: string[] // Optional filter for cost timeline
}

interface PlannedValueSeries {
  label: string
  data: { x: Date; y: number }[]
  color?: string
}

export interface BudgetTimelineChartConfig {
  datasets: ChartDataset<"line", { x: Date; y: number }[]>[]
  options: ChartOptions<"line">
}

const PLANNED_VALUE_COLOR = "#3182ce"
const ACTUAL_COST_COLOR = "#f56565"
const EARNED_VALUE_COLOR = "#48bb78"

export function createBudgetTimelineConfig({
  viewMode,
  plannedValue,
  actualCost,
  earnedValue,
}: {
  viewMode: "aggregated" | "multi-line"
  plannedValue: PlannedValueSeries[]
  actualCost: { x: Date; y: number }[]
  earnedValue: { date: Date; earnedValue: number }[]
}): BudgetTimelineChartConfig {
  const plannedDatasets: ChartDataset<"line", { x: Date; y: number }[]>[] =
    plannedValue.length > 0
      ? plannedValue.map((series, index) => ({
          label: series.label,
          data: series.data,
          borderColor:
            series.color ??
            (viewMode === "aggregated"
              ? PLANNED_VALUE_COLOR
              : [
                  "#3182ce",
                  "#48bb78",
                  "#ed8936",
                  "#9f7aea",
                  "#38b2ac",
                  "#dd6b20",
                ][index % 6]),
          backgroundColor: "transparent",
          borderWidth: 2,
          fill: false,
        }))
      : [
          {
            label: "Planned Value (PV)",
            data: [],
            borderColor: PLANNED_VALUE_COLOR,
            backgroundColor: "transparent",
            borderWidth: 2,
            fill: false,
          },
        ]

  const actualCostDataset: ChartDataset<"line", { x: Date; y: number }[]> = {
    label: "Actual Cost (AC)",
    data: actualCost,
    borderColor: ACTUAL_COST_COLOR,
    backgroundColor: "transparent",
    borderWidth: 2,
    fill: false,
  }

  const earnedValueDataset: ChartDataset<"line", { x: Date; y: number }[]> = {
    label: "Earned Value (EV)",
    data: earnedValue.map((point) => ({
      x: point.date,
      y: point.earnedValue,
    })),
    borderColor: EARNED_VALUE_COLOR,
    backgroundColor: "transparent",
    borderWidth: 2,
    fill: false,
  }

  const formatCurrency = (value: number) =>
    `€${value.toLocaleString("en-US", {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    })}`

  const options: ChartOptions<"line"> = {
    responsive: true,
    maintainAspectRatio: false,
    interaction: {
      intersect: false,
      mode: "index",
    },
    plugins: {
      legend: {
        display: true,
        position: "top",
        labels: {
          color: "#2D3748", // will be overridden in component with theme value
        },
      },
      tooltip: {
        callbacks: {
          label: (context: TooltipItem<"line">) => {
            const datasetLabel = context.dataset.label ?? ""
            const value = context.parsed.y ?? 0
            return `${datasetLabel}: ${formatCurrency(value)}`
          },
        },
      },
    },
    scales: {
      x: {
        type: "time",
        time: {
          unit: "day",
          displayFormats: {
            day: "MMM d, yyyy",
          },
        },
        title: {
          display: true,
          text: "Date",
        },
        grid: {
          color: "rgba(0,0,0,0.1)", // will be overridden in component
        },
        ticks: {
          color: "#2D3748", // will be overridden in component
        },
      },
      y: {
        title: {
          display: true,
          text: "Amount (€)",
        },
        ticks: {
          color: "#2D3748", // will be overridden in component
          callback: (value: string | number) => {
            const numericValue =
              typeof value === "number" ? value : Number(value)

            if (Number.isNaN(numericValue)) {
              return value
            }

            return formatCurrency(numericValue)
          },
        },
        grid: {
          color: "rgba(0,0,0,0.1)", // will be overridden in component
        },
      },
    },
  }

  return {
    datasets: [...plannedDatasets, actualCostDataset, earnedValueDataset],
    options,
  }
}

async function fetchAllEarnedValueEntries(
  costElementId: string,
): Promise<EarnedValueEntryPublic[]> {
  const limit = 100
  let skip = 0
  const collected: EarnedValueEntryPublic[] = []

  while (true) {
    const response = await EarnedValueEntriesService.readEarnedValueEntries({
      costElementId,
      skip,
      limit,
    })

    const data = response?.data ?? []
    const count = response?.count ?? data.length

    collected.push(...data)

    if (collected.length >= count || data.length < limit) {
      break
    }

    skip += limit
  }

  return collected
}

export default function BudgetTimeline({
  costElements,
  viewMode = "aggregated",
  projectId,
  wbeIds,
  costElementIds,
}: BudgetTimelineProps) {
  const { controlDate } = useTimeMachine()
  // Theme-aware colors (declare before early returns)
  const axisColor = useColorModeValue("#2D3748", "#E2E8F0")
  const gridColor = useColorModeValue(
    "rgba(0,0,0,0.1)",
    "rgba(255,255,255,0.12)",
  )
  const normalizedWbeIds = wbeIds?.length ? [...wbeIds].sort() : undefined
  const normalizedCostElementIds = costElementIds?.length
    ? [...costElementIds].sort()
    : undefined

  const elementsWithSchedules = costElements.filter(
    (ce) => ce.schedule !== null && ce.schedule !== undefined,
  )

  const costElementIdsForEarnedValue = elementsWithSchedules
    .map((ce) => ce.cost_element_id)
    .filter(Boolean)
  const sortedCostElementIdsForEarnedValue =
    costElementIdsForEarnedValue.length > 0
      ? [...costElementIdsForEarnedValue].sort()
      : []

  const { data: costTimelineData } = useQuery({
    queryFn: () =>
      CostTimelineService.getProjectCostTimeline({
        projectId: projectId!,
        wbeIds: normalizedWbeIds,
        costElementIds: normalizedCostElementIds,
      }),
    queryKey: [
      "cost-timeline",
      projectId,
      normalizedWbeIds,
      normalizedCostElementIds,
      controlDate,
    ],
    enabled: !!projectId,
  })

  const { data: earnedValueEntriesData } = useQuery({
    queryFn: async () => {
      const allEntries = await Promise.all(
        sortedCostElementIdsForEarnedValue.map((id) =>
          fetchAllEarnedValueEntries(id),
        ),
      )
      return allEntries.flat()
    },
    queryKey: [
      "earned-value-timeline",
      projectId,
      normalizedWbeIds,
      normalizedCostElementIds,
      sortedCostElementIdsForEarnedValue,
      controlDate,
    ],
    enabled: sortedCostElementIdsForEarnedValue.length > 0,
  })

  const timelines: TimePeriod[][] = elementsWithSchedules
    .map((ce) => {
      const schedule = ce.schedule!
      const startDate = new Date(schedule.start_date)
      const endDate = new Date(schedule.end_date)
      const budgetBac = Number(ce.budget_bac || 0)

      if (
        Number.isNaN(startDate.getTime()) ||
        Number.isNaN(endDate.getTime())
      ) {
        console.warn(
          `Invalid dates for cost element ${ce.cost_element_id}: start=${schedule.start_date}, end=${schedule.end_date}`,
        )
        return null
      }

      if (endDate < startDate) {
        console.warn(
          `End date before start date for cost element ${ce.cost_element_id}`,
        )
        return null
      }

      if (budgetBac < 0) {
        console.warn(
          `Negative budget for cost element ${ce.cost_element_id}: ${budgetBac}`,
        )
        return null
      }

      const timePoints = generateTimeSeries(startDate, endDate, "daily")

      let progression: TimePeriod[]
      switch (schedule.progression_type) {
        case "linear":
          progression = calculateLinearProgression(
            startDate,
            endDate,
            budgetBac,
            timePoints,
          )
          break
        case "gaussian":
          progression = calculateGaussianProgression(
            startDate,
            endDate,
            budgetBac,
            timePoints,
          )
          break
        case "logarithmic":
          progression = calculateLogarithmicProgression(
            startDate,
            endDate,
            budgetBac,
            timePoints,
          )
          break
        default:
          progression = calculateLinearProgression(
            startDate,
            endDate,
            budgetBac,
            timePoints,
          )
      }

      return progression
    })
    .filter((timeline): timeline is TimePeriod[] => timeline !== null)

  const costTimelinePoints = costTimelineData?.data || []
  const costData = costTimelinePoints.map((point) => ({
    x: new Date(point.point_date),
    y: parseFloat(point.cumulative_cost),
  }))

  const earnedValueTimeline =
    earnedValueEntriesData && earnedValueEntriesData.length > 0
      ? buildEarnedValueTimeline({
          entries: earnedValueEntriesData,
        })
      : []

  const hasEarnedValueData = earnedValueTimeline.length > 0

  let plannedValueSeries: PlannedValueSeries[]

  if (viewMode === "aggregated") {
    plannedValueSeries = [
      {
        label: "Planned Value (PV)",
        data: aggregateTimelines(timelines).map((period) => ({
          x: period.date,
          y: period.cumulativeBudget,
        })),
        color: PLANNED_VALUE_COLOR,
      },
    ]
  } else {
    const colorPalette = [
      "#3182ce",
      "#48bb78",
      "#ed8936",
      "#9f7aea",
      "#38b2ac",
      "#dd6b20",
    ]
    const multiLineSeries: PlannedValueSeries[] = []

    elementsWithSchedules.forEach((ce, index) => {
      const timeline = timelines[index]
      if (!timeline) {
        return
      }

      multiLineSeries.push({
        label: `${ce.department_name} - PV (€${Number(ce.budget_bac).toLocaleString()})`,
        data: timeline.map((period) => ({
          x: period.date,
          y: period.cumulativeBudget,
        })),
        color: colorPalette[index % colorPalette.length],
      })
    })

    plannedValueSeries =
      multiLineSeries.length > 0
        ? multiLineSeries
        : [
            {
              label: "Planned Value (PV)",
              data: [],
              color: PLANNED_VALUE_COLOR,
            },
          ]
  }

  const chartConfig = createBudgetTimelineConfig({
    viewMode,
    plannedValue: plannedValueSeries,
    actualCost: costData,
    earnedValue: earnedValueTimeline,
  })

  const chartData = {
    datasets: chartConfig.datasets,
  }

  // Override colors with theme-aware values
  const themedOptions: ChartOptions<"line"> = {
    ...chartConfig.options,
    plugins: {
      ...chartConfig.options.plugins,
      legend: {
        ...chartConfig.options.plugins?.legend,
        labels: {
          ...(chartConfig.options.plugins?.legend as any)?.labels,
          color: axisColor,
        },
      },
    },
    scales: {
      ...chartConfig.options.scales,
      x: {
        ...(chartConfig.options.scales?.x as any),
        grid: { color: gridColor },
        ticks: { color: axisColor },
      },
      y: {
        ...(chartConfig.options.scales?.y as any),
        grid: { color: gridColor },
        ticks: {
          ...(chartConfig.options.scales?.y as any)?.ticks,
          color: axisColor,
        },
      },
    },
  }

  return (
    <Box borderWidth="1px" borderRadius="lg" p={4} bg="bg.surface" mb={4}>
      <VStack gap={4} align="stretch">
        <Heading size="md">Budget, Cost & Earned Value Timeline</Heading>
        <Box height="400px">
          <Line data={chartData} options={themedOptions} />
        </Box>
        <Text fontSize="sm" color="fg.muted">
          Showing {timelines.length} cost element(s) with schedules.{" "}
          {costData.length > 0
            ? `Actual cost includes ${costData.length} point(s). `
            : "No actual cost data available. "}
          {hasEarnedValueData
            ? `Earned value includes ${earnedValueTimeline.length} entry(ies).`
            : "No earned value entries available."}
        </Text>
      </VStack>
    </Box>
  )
}
