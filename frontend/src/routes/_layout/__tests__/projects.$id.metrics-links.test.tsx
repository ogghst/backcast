// @vitest-environment jsdom
import { ChakraProvider } from "@chakra-ui/react"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { render, screen, waitFor } from "@testing-library/react"
import type React from "react"
import { afterEach, describe, expect, it, vi } from "vitest"
import * as client from "@/client"
import { ColorModeProvider } from "@/components/ui/color-mode"
import { TimeMachineProvider } from "@/context/TimeMachineContext"
import { system } from "../../../theme"
import { Route } from "../projects.$id"

vi.mock("@/client", () => ({
  ProjectsService: {
    readProject: vi.fn(),
  },
  WbesService: {
    readWbes: vi.fn(),
  },
  BudgetTimelineService: {
    getCostElementsWithSchedules: vi.fn(),
  },
  UsersService: {
    readTimeMachinePreference: vi.fn(),
    updateTimeMachinePreference: vi.fn(),
  },
}))

vi.mock("@/components/Pending/PendingItems", () => ({
  default: () => <div data-testid="pending-items" />,
}))

vi.mock("@/components/Projects/MetricsSummary", () => ({
  default: () => <div data-testid="metrics-summary" />,
}))

vi.mock("@/components/Projects/BudgetTimeline", () => ({
  default: () => <div data-testid="budget-timeline" />,
}))

vi.mock("@/components/Projects/BudgetTimelineFilter", () => ({
  default: () => <div data-testid="budget-timeline-filter" />,
}))

vi.mock("@tanstack/react-router", async () => {
  const actual = await vi.importActual<typeof import("@tanstack/react-router")>(
    "@tanstack/react-router",
  )
  return {
    ...actual,
    Link: ({ children }: { children: React.ReactNode }) => <>{children}</>,
    useNavigate: () => vi.fn(),
    useRouterState: () => "/projects/project-123",
  }
})

function renderWithProviders(ui: React.ReactElement) {
  const qc = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
    },
  })
  return render(
    <ChakraProvider value={system}>
      <ColorModeProvider defaultTheme="light">
        <QueryClientProvider client={qc}>
          <TimeMachineProvider>{ui}</TimeMachineProvider>
        </QueryClientProvider>
      </ColorModeProvider>
    </ChakraProvider>,
  )
}

describe("Project detail metrics actions", () => {
  afterEach(() => {
    vi.clearAllMocks()
  })

  it("shows link to project performance dashboard in metrics tab", async () => {
    vi.spyOn(Route, "useParams").mockReturnValue({ id: "project-123" } as any)
    vi.spyOn(Route, "useSearch").mockReturnValue({
      tab: "metrics",
      page: 1,
    } as any)

    vi.mocked(client.ProjectsService.readProject).mockResolvedValue({
      project_id: "project-123",
      project_name: "Test Project",
    } as any)
    vi.mocked(client.WbesService.readWbes).mockResolvedValue({
      data: [],
      count: 0,
    })
    vi.mocked(
      client.BudgetTimelineService.getCostElementsWithSchedules,
    ).mockResolvedValue([])
    vi.mocked(client.UsersService.readTimeMachinePreference).mockResolvedValue({
      time_machine_date: "2024-01-15",
    } as any)
    vi.mocked(
      client.UsersService.updateTimeMachinePreference,
    ).mockResolvedValue({
      time_machine_date: "2024-01-15",
    } as any)

    const Component = Route.options.component as React.ComponentType

    renderWithProviders(<Component />)

    await waitFor(() => {
      expect(
        screen.getByText(/View Project Performance Dashboard/i),
      ).toBeInTheDocument()
    })
  })
})
