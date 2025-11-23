import { Badge, Flex, Text, Tooltip } from "@chakra-ui/react"
import type { ForecastPublic } from "@/client"
import type { ColumnDefExtended } from "@/components/DataTable/types"
import DeleteForecast from "@/components/Projects/DeleteForecast"
import EditForecast from "@/components/Projects/EditForecast"
import { formatCurrency, formatDate } from "./earnedValueColumns"

export function buildForecastColumns(
  costElementId: string,
  budgetBac?: string | number | null,
  actualCost?: string | number | null,
  userMap?: Map<string, string>,
): ColumnDefExtended<ForecastPublic>[] {
  void costElementId

  // Calculate ETC = EAC - AC
  const calculateETC = (eac: string | number | null | undefined) => {
    if (eac === null || eac === undefined) {
      return null
    }
    const eacNum = typeof eac === "string" ? parseFloat(eac) : Number(eac)
    const acNum =
      actualCost !== null && actualCost !== undefined
        ? typeof actualCost === "string"
          ? parseFloat(actualCost)
          : Number(actualCost)
        : 0

    if (Number.isNaN(eacNum) || Number.isNaN(acNum)) {
      return null
    }
    return eacNum - acNum
  }

  // Get EAC color based on comparison with BAC
  const getEACColor = (eac: string | number | null | undefined) => {
    if (
      eac === null ||
      eac === undefined ||
      budgetBac === null ||
      budgetBac === undefined
    ) {
      return undefined
    }
    const eacNum = typeof eac === "string" ? parseFloat(eac) : Number(eac)
    const bacNum =
      typeof budgetBac === "string" ? parseFloat(budgetBac) : Number(budgetBac)

    if (Number.isNaN(eacNum) || Number.isNaN(bacNum)) {
      return undefined
    }

    const diff = Math.abs(eacNum - bacNum) / bacNum
    if (eacNum < bacNum) {
      return "green.500"
    }
    if (diff <= 0.05) {
      // Within 5%
      return "yellow.500"
    }
    return "red.500"
  }

  // Format forecast type as badge
  const formatForecastType = (type: string) => {
    const typeMap: Record<string, { label: string; color: string }> = {
      bottom_up: { label: "Bottom-up", color: "blue" },
      performance_based: { label: "Performance-based", color: "purple" },
      management_judgment: { label: "Management Judgment", color: "orange" },
    }
    const config = typeMap[type] || { label: type, color: "gray" }
    return (
      <Badge colorPalette={config.color} variant="subtle">
        {config.label}
      </Badge>
    )
  }

  return [
    {
      accessorKey: "forecast_date",
      header: "Forecast Date",
      enableSorting: true,
      enableResizing: true,
      size: 140,
      defaultVisible: true,
      cell: ({ getValue }) => formatDate(getValue() as string),
    },
    {
      accessorKey: "estimate_at_completion",
      header: "EAC",
      enableSorting: true,
      enableResizing: true,
      size: 140,
      defaultVisible: true,
      cell: ({ getValue }) => {
        const eac = getValue() as string | number | null
        const color = getEACColor(eac)
        return (
          <Text color={color} fontWeight={color ? "semibold" : "normal"}>
            {formatCurrency(eac)}
          </Text>
        )
      },
    },
    {
      id: "etc",
      header: "ETC",
      enableSorting: false,
      enableResizing: true,
      size: 140,
      defaultVisible: true,
      cell: ({ row }) => {
        const eac = row.original.estimate_at_completion
        const etc = calculateETC(eac)
        if (etc === null) {
          return "N/A"
        }
        return formatCurrency(etc)
      },
    },
    {
      accessorKey: "forecast_type",
      header: "Forecast Type",
      enableSorting: true,
      enableResizing: true,
      enableColumnFilter: true,
      filterType: "select",
      filterConfig: {
        type: "select",
        options: ["bottom_up", "performance_based", "management_judgment"],
      },
      size: 180,
      defaultVisible: true,
      cell: ({ getValue }) => formatForecastType(getValue() as string),
    },
    {
      id: "current",
      header: "Current",
      enableSorting: true,
      enableResizing: true,
      size: 100,
      defaultVisible: true,
      cell: ({ row }) => {
        if (row.original.is_current) {
          return (
            <Badge colorPalette="green" variant="solid">
              Current
            </Badge>
          )
        }
        return "—"
      },
    },
    {
      accessorKey: "estimator_id",
      header: "Estimator",
      enableSorting: true,
      enableResizing: true,
      size: 150,
      defaultVisible: false,
      cell: ({ getValue }) => {
        const estimatorId = getValue() as string
        const userName = userMap?.get(estimatorId)
        return userName || estimatorId
      },
    },
    {
      accessorKey: "assumptions",
      header: "Assumptions",
      enableSorting: false,
      enableResizing: true,
      size: 300,
      defaultVisible: true,
      cell: ({ getValue }) => {
        const assumptions = (getValue() as string) || ""
        const truncated =
          assumptions.length > 100
            ? `${assumptions.slice(0, 100)}...`
            : assumptions
        if (assumptions.length > 100) {
          return (
            <Tooltip.Root openDelay={200}>
              <Tooltip.Trigger asChild>
                <Text>{truncated}</Text>
              </Tooltip.Trigger>
              <Tooltip.Positioner>
                <Tooltip.Content maxW="400px">
                  {assumptions}
                  <Tooltip.Arrow>
                    <Tooltip.ArrowTip />
                  </Tooltip.Arrow>
                </Tooltip.Content>
              </Tooltip.Positioner>
            </Tooltip.Root>
          )
        }
        return <Text>{assumptions || "—"}</Text>
      },
    },
    {
      id: "actions",
      header: "Actions",
      enableSorting: false,
      enableResizing: false,
      enableColumnFilter: false,
      size: 160,
      defaultVisible: true,
      cell: ({ row }) => (
        <Flex gap={2}>
          {row.original.is_current && (
            <EditForecast
              forecast={row.original}
              budgetBac={budgetBac}
              actualCost={actualCost}
            />
          )}
          <DeleteForecast
            forecastId={row.original.forecast_id}
            isCurrent={row.original.is_current ?? false}
            forecastDate={row.original.forecast_date ?? ""}
            eac={row.original.estimate_at_completion ?? ""}
          />
        </Flex>
      ),
    },
  ]
}
