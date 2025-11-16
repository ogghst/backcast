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
    useQuery: () => ({
      data: {
        earned_value: "100",
        budget_bac: "200",
        percent_complete: 0.5,
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

describe("EarnedValueSummary theming", () => {
  it("uses themed bg and text colors in dark mode", () => {
    renderDark(<EarnedValueSummary level="project" projectId="p1" />)

    // Smoke check: headings/texts render
    expect(screen.getByText("Earned Value Summary")).toBeTruthy()
    expect(screen.getByText("Earned Value (EV)")).toBeTruthy()
    expect(screen.getByText("Budget at Completion (BAC)")).toBeTruthy()
    expect(screen.getByText("Physical Completion")).toBeTruthy()
  })
})
