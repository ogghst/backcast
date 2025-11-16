// @vitest-environment jsdom
import { ChakraProvider } from "@chakra-ui/react"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { render } from "@testing-library/react"
import React from "react"
import { beforeEach, describe, expect, it, vi } from "vitest"
import { TimeMachineProvider } from "@/context/TimeMachineContext"
import { system } from "../../../theme"
import { ColorModeProvider } from "../../ui/color-mode"
import BudgetTimeline from "../BudgetTimeline"

// Mock react-query calls inside BudgetTimeline
vi.mock("@tanstack/react-query", async () => {
  const actual = await vi.importActual<any>("@tanstack/react-query")
  return {
    ...actual,
    useQuery: (opts: any) => {
      if (String(opts.queryKey?.[0]).includes("cost-timeline")) {
        return { data: { data: [] } }
      }
      if (String(opts.queryKey?.[0]).includes("earned-value-timeline")) {
        return { data: [] }
      }
      return { data: [] }
    },
  }
})

// Capture props for Line chart
const lineProps: any[] = []
vi.mock("react-chartjs-2", () => {
  return {
    Line: (props: any) => {
      lineProps.push(props)
      return React.createElement("div", { "data-testid": "line" })
    },
  }
})

describe("BudgetTimeline theming", () => {
  beforeEach(() => {
    lineProps.length = 0
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

  it("applies dark-mode legend/tick/grid colors", () => {
    // Minimal props to render with no data branches blocked
    renderDark(
      <BudgetTimeline
        costElements={[
          {
            cost_element_id: "1",
            department_name: "Dept",
            budget_bac: "0",
            schedule: {
              start_date: "2024-01-01",
              end_date: "2024-01-02",
              progression_type: "linear",
            } as any,
          } as any,
        ]}
        projectId="p1"
      />,
    )

    expect(lineProps[0]).toBeTruthy()
    const options = lineProps[0]?.options
    expect(options?.plugins?.legend?.labels?.color).toBe("#E2E8F0")
    expect(options?.scales?.x?.ticks?.color).toBe("#E2E8F0")
    expect(options?.scales?.x?.grid?.color).toBe("rgba(255,255,255,0.12)")
    expect(options?.scales?.y?.ticks?.color).toBe("#E2E8F0")
    expect(options?.scales?.y?.grid?.color).toBe("rgba(255,255,255,0.12)")
  })
})
