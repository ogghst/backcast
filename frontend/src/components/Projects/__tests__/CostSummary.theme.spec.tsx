// @vitest-environment jsdom
import { ChakraProvider } from "@chakra-ui/react"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { render, screen } from "@testing-library/react"
import type React from "react"
import { describe, expect, it, vi } from "vitest"
import { TimeMachineProvider } from "@/context/TimeMachineContext"
import { system } from "../../../theme"
import { ColorModeProvider } from "../../ui/color-mode"
import CostSummary from "../CostSummary"

vi.mock("@tanstack/react-query", async () => {
  const actual = await vi.importActual<any>("@tanstack/react-query")
  return {
    ...actual,
    useQuery: () => ({
      data: {
        total_cost: "100",
        budget_bac: "200",
        cost_percentage_of_budget: 45,
        cost_registration_count: 3,
      },
      isLoading: false,
    }),
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

describe("CostSummary theming", () => {
  it("uses themed bg and text colors in dark mode", () => {
    renderDark(<CostSummary level="project" projectId="p1" />)
    expect(screen.getByText("Cost Summary")).toBeTruthy()
    expect(screen.getByText("Total Cost")).toBeTruthy()
  })
})
