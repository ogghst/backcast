import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { renderToStaticMarkup } from "react-dom/server"
import { describe, expect, it, vi } from "vitest"
import { TimeMachineProvider } from "@/context/TimeMachineContext"

import BudgetTimelineFilter from "../BudgetTimelineFilter"

vi.mock("@chakra-ui/react", () => {
  const React = require("react")
  const passThrough = ({ children, ...rest }: any) =>
    React.createElement("div", rest, children)
  const textLike = ({ children, ...rest }: any) =>
    React.createElement("span", rest, children)

  return {
    __esModule: true,
    Box: passThrough,
    Badge: passThrough,
    Button: passThrough,
    Collapsible: {
      Root: passThrough,
      Trigger: passThrough,
      Content: passThrough,
    },
    Flex: passThrough,
    HStack: passThrough,
    Text: textLike,
    VStack: passThrough,
  }
})

vi.mock("@/client", () => {
  return {
    WbesService: {
      readWbes: vi.fn().mockResolvedValue({ data: [], count: 0 }),
    },
    CostElementTypesService: {
      readCostElementTypes: vi.fn().mockResolvedValue({ data: [] }),
    },
    CostElementsService: {
      readCostElements: vi.fn().mockResolvedValue({ data: [], count: 0 }),
    },
  }
})

describe("BudgetTimelineFilter", () => {
  it("does not render display mode controls", () => {
    const queryClient = new QueryClient()
    const markup = renderToStaticMarkup(
      <QueryClientProvider client={queryClient}>
        <TimeMachineProvider>
          <BudgetTimelineFilter
            projectId="project-1"
            context="project"
            onFilterChange={() => {}}
          />
        </TimeMachineProvider>
      </QueryClientProvider>,
    )

    expect(markup).not.toContain("Display Mode")
    expect(markup).not.toContain("Budget</")
    expect(markup).not.toContain("Costs</")
    expect(markup).not.toContain("Both</")
  })
})
