// @vitest-environment jsdom
import { ChakraProvider } from "@chakra-ui/react"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { render } from "@testing-library/react"
import React from "react"
import { beforeEach, describe, expect, it, vi } from "vitest"
import { TimeMachineProvider } from "@/context/TimeMachineContext"
import { system } from "../../../theme"
import { ColorModeProvider } from "../../ui/color-mode"
import BudgetSummary from "../BudgetSummary"

// Mock react-query data fetching used inside BudgetSummary
vi.mock("@tanstack/react-query", async () => {
  const actual = await vi.importActual<any>("@tanstack/react-query")
  return {
    ...actual,
    useQuery: () => ({
      data: {
        revenue_limit: "1000",
        total_revenue_allocated: "600",
        total_budget_bac: "800",
        total_revenue_plan: "900",
        remaining_revenue: "400",
        revenue_utilization_percent: 60,
      },
      isLoading: false,
    }),
  }
})

// Capture props passed to chart components
const doughnutProps: any[] = []
const barProps: any[] = []

vi.mock("react-chartjs-2", () => {
  return {
    Doughnut: (props: any) => {
      doughnutProps.push(props)
      return React.createElement("div", { "data-testid": "doughnut" })
    },
    Bar: (props: any) => {
      barProps.push(props)
      return React.createElement("div", { "data-testid": "bar" })
    },
  }
})

describe("BudgetSummary theming", () => {
  beforeEach(() => {
    doughnutProps.length = 0
    barProps.length = 0
  })

  function renderDark(ui: React.ReactElement) {
    const qc = new QueryClient()
    return render(
      <ChakraProvider value={system}>
        <ColorModeProvider defaultTheme="dark">
          <QueryClientProvider client={qc}>
            <TimeMachineProvider>{ui}</TimeMachineProvider>
          </QueryClientProvider>
        </ColorModeProvider>
      </ChakraProvider>,
    )
  }

  it("applies dark-mode legend/tick colors to charts", () => {
    renderDark(<BudgetSummary level="project" projectId="p1" />)

    // Doughnut options legend label color should be light in dark mode
    expect(doughnutProps[0]).toBeTruthy()
    const doughnutLegendColor =
      doughnutProps[0]?.options?.plugins?.legend?.labels?.color
    expect(doughnutLegendColor).toBe("#E2E8F0")

    // Bar chart options should set axis and grid colors
    expect(barProps[0]).toBeTruthy()
    const barOptions = barProps[0]?.options
    expect(barOptions?.plugins?.legend?.labels?.color ?? "#E2E8F0").toBe(
      "#E2E8F0",
    )
    expect(barOptions?.scales?.x?.ticks?.color).toBe("#E2E8F0")
    expect(barOptions?.scales?.x?.grid?.color).toBe("rgba(255,255,255,0.12)")
    expect(barOptions?.scales?.y?.ticks?.color).toBe("#E2E8F0")
    expect(barOptions?.scales?.y?.grid?.color).toBe("rgba(255,255,255,0.12)")
  })
})
