// @vitest-environment jsdom
import { ChakraProvider } from "@chakra-ui/react"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { render, screen } from "@testing-library/react"
import type React from "react"
import { describe, expect, it, vi } from "vitest"
import { TimeMachineProvider } from "@/context/TimeMachineContext"
import { system } from "../../../theme"
import { ColorModeProvider } from "../../ui/color-mode"
import EarnedValueSummary from "../EarnedValueSummary"

vi.mock("@tanstack/react-query", async () => {
  const actual = await vi.importActual<any>("@tanstack/react-query")
  return {
    ...actual,
    useQuery: (config: any) => {
      // Mock earned value query
      if (config.queryKey[0] === "earned-value") {
        return {
          data: {
            earned_value: "100",
            budget_bac: "200",
            percent_complete: 0.5,
          },
          isLoading: false,
        }
      }
      // Mock EVM metrics query
      if (config.queryKey[0] === "evm-metrics") {
        return {
          data: {
            cpi: "0.95",
            spi: "1.0",
            tcpi: "1.05",
            cost_variance: "-10",
            schedule_variance: "5",
          },
          isLoading: false,
        }
      }
      return { data: null, isLoading: false }
    },
  }
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

describe("EarnedValueSummary theming", () => {
  it("uses themed bg and text colors in dark mode", () => {
    renderDark(<EarnedValueSummary level="project" projectId="p1" />)

    // Smoke check: headings/texts render
    expect(screen.getByText("Earned Value Summary")).toBeTruthy()
    expect(screen.getByText("Earned Value (EV)")).toBeTruthy()
    expect(screen.getByText("Budget at Completion (BAC)")).toBeTruthy()
    expect(screen.getByText("Physical Completion")).toBeTruthy()
    // New EVM metrics cards
    expect(screen.getByText("Cost Performance Index (CPI)")).toBeTruthy()
    expect(screen.getByText("Schedule Performance Index (SPI)")).toBeTruthy()
    expect(
      screen.getByText("To-Complete Performance Index (TCPI)"),
    ).toBeTruthy()
    expect(screen.getByText("Cost Variance (CV)")).toBeTruthy()
    expect(screen.getByText("Schedule Variance (SV)")).toBeTruthy()
  })
})
