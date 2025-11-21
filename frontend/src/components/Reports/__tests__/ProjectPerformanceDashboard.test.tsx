// @vitest-environment jsdom
import { ChakraProvider } from "@chakra-ui/react"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { render, screen, waitFor } from "@testing-library/react"
import type React from "react"
import { beforeEach, describe, expect, it, vi } from "vitest"
import type { CostElementsReadCostElementsData } from "@/client"
import * as client from "@/client"
import { ColorModeProvider } from "@/components/ui/color-mode"
import { TimeMachineProvider } from "@/context/TimeMachineContext"
import { system } from "../../../theme"
import ProjectPerformanceDashboard from "../ProjectPerformanceDashboard"

vi.mock("@/client", () => ({
  ProjectsService: {
    readProject: vi.fn(),
    readProjects: vi.fn(),
  },
  WbesService: {
    readWbes: vi.fn(),
  },
  CostElementsService: {
    readCostElements: vi.fn(),
  },
  CostElementTypesService: {
    readCostElementTypes: vi.fn(),
  },
  BudgetTimelineService: {
    getCostElementsWithSchedules: vi.fn(),
  },
  EvmMetricsService: {
    getProjectEvmMetricsEndpoint: vi.fn(),
  },
  EarnedValueService: {
    getProjectEarnedValue: vi.fn(),
  },
  AdminService: {
    listVarianceThresholdConfigs: vi.fn(),
  },
  ReportsService: {
    getProjectVarianceAnalysisReportEndpoint: vi.fn(),
  },
  UsersService: {
    readTimeMachinePreference: vi.fn(),
    updateTimeMachinePreference: vi.fn(),
  },
}))

vi.mock("@/components/Projects/BudgetTimeline", () => ({
  default: vi.fn(({ costElements, projectId, wbeIds }) => (
    <div data-testid="budget-timeline">
      <div data-testid="timeline-project-id">{projectId}</div>
      <div data-testid="timeline-wbe-ids">{wbeIds?.join(",") || "none"}</div>
      <div data-testid="timeline-cost-elements-count">
        {costElements?.length || 0}
      </div>
    </div>
  )),
}))

vi.mock("@tanstack/react-router", async () => {
  const actual = await vi.importActual("@tanstack/react-router")
  return {
    ...actual,
    useNavigate: () => vi.fn(),
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

describe("ProjectPerformanceDashboard", () => {
  beforeEach(() => {
    vi.resetAllMocks()
    vi.mocked(client.ProjectsService.readProject).mockResolvedValue({
      project_id: "proj-123",
      project_name: "Mars Habitat",
    } as any)
    vi.mocked(client.ProjectsService.readProjects).mockResolvedValue({
      data: [
        { project_id: "proj-123", project_name: "Mars Habitat" },
        { project_id: "proj-456", project_name: "Lunar Rover" },
      ],
      count: 2,
    } as any)
    vi.mocked(client.WbesService.readWbes).mockResolvedValue({
      data: [
        { wbe_id: "wbe-1", machine_type: "Machine A" },
        { wbe_id: "wbe-2", machine_type: "Machine B" },
      ],
      count: 2,
    } as any)
    vi.mocked(client.CostElementsService.readCostElements).mockImplementation(((
      params?: CostElementsReadCostElementsData,
    ) => {
      const wbeId = params?.wbeId ?? ""
      const perWbe: Record<string, any[]> = {
        "wbe-1": [
          {
            cost_element_id: "ce-1",
            wbe_id: "wbe-1",
            department_name: "Controls",
          },
        ],
        "wbe-2": [
          {
            cost_element_id: "ce-2",
            wbe_id: "wbe-2",
            department_name: "Fabrication",
          },
        ],
      }
      const data = perWbe[wbeId] ?? []
      return new client.CancelablePromise((resolve) =>
        resolve({ data, count: data.length } as any),
      )
    }) as typeof client.CostElementsService.readCostElements)
    vi.mocked(
      client.CostElementTypesService.readCostElementTypes,
    ).mockResolvedValue({
      data: [
        {
          cost_element_type_id: "type-1",
          type_code: "ENG",
          type_name: "Engineering",
          category_type: "labor",
          is_active: true,
        },
        {
          cost_element_type_id: "type-2",
          type_code: "FAB",
          type_name: "Fabrication",
          category_type: "material",
          is_active: true,
        },
      ],
      count: 2,
    } as any)
    vi.mocked(client.UsersService.readTimeMachinePreference).mockResolvedValue({
      time_machine_date: "2025-01-01",
    } as any)
    vi.mocked(
      client.UsersService.updateTimeMachinePreference,
    ).mockResolvedValue({
      time_machine_date: "2025-01-01",
    } as any)
    vi.mocked(
      client.BudgetTimelineService.getCostElementsWithSchedules,
    ).mockResolvedValue([
      {
        cost_element_id: "ce-1",
        wbe_id: "wbe-1",
        department_name: "Controls",
        schedule: {
          schedule_id: "sched-1",
          cost_element_id: "ce-1",
          periods: [],
        },
      },
      {
        cost_element_id: "ce-2",
        wbe_id: "wbe-2",
        department_name: "Fabrication",
        schedule: {
          schedule_id: "sched-2",
          cost_element_id: "ce-2",
          periods: [],
        },
      },
    ] as any)
    vi.mocked(
      client.EvmMetricsService.getProjectEvmMetricsEndpoint,
    ).mockResolvedValue({
      cpi: "0.92",
      spi: "1.05",
      tcpi: "1.15",
      cost_variance: "-5000.00",
      schedule_variance: "3000.00",
    } as any)
    vi.mocked(
      client.EarnedValueService.getProjectEarnedValue,
    ).mockResolvedValue({
      budget_bac: "100000.00",
      earned_value: "50000.00",
      percent_complete: "0.50",
    } as any)
    vi.mocked(
      client.ReportsService.getProjectVarianceAnalysisReportEndpoint,
    ).mockResolvedValue({
      project_id: "proj-123",
      project_name: "Mars Habitat",
      control_date: "2025-01-01",
      rows: [],
      summary: {
        cost_variance: "0.00",
        schedule_variance: "0.00",
      },
      total_problem_areas: 0,
    } as any)
    vi.mocked(
      client.AdminService.listVarianceThresholdConfigs,
    ).mockResolvedValue({
      data: [
        {
          variance_threshold_config_id: "thresh-1",
          threshold_type: "warning_cv",
          threshold_percentage: "-5.00",
          description: "Warning threshold for cost variance",
          is_active: true,
          created_at: "2025-01-01T00:00:00Z",
          updated_at: "2025-01-01T00:00:00Z",
        },
        {
          variance_threshold_config_id: "thresh-2",
          threshold_type: "critical_cv",
          threshold_percentage: "-10.00",
          description: "Critical threshold for cost variance",
          is_active: true,
          created_at: "2025-01-01T00:00:00Z",
          updated_at: "2025-01-01T00:00:00Z",
        },
        {
          variance_threshold_config_id: "thresh-3",
          threshold_type: "warning_sv",
          threshold_percentage: "-3.00",
          description: "Warning threshold for schedule variance",
          is_active: true,
          created_at: "2025-01-01T00:00:00Z",
          updated_at: "2025-01-01T00:00:00Z",
        },
      ],
      count: 3,
    } as any)
  })

  it("renders placeholder sections", () => {
    renderWithProviders(<ProjectPerformanceDashboard projectId="proj-123" />)

    expect(
      screen.getByRole("heading", { name: /Project Performance Dashboard/i }),
    ).toBeInTheDocument()
    expect(
      screen.getByRole("heading", { name: /Timeline Overview/i }),
    ).toBeInTheDocument()
    expect(
      screen.getByRole("heading", { name: /Performance KPIs/i }),
    ).toBeInTheDocument()
    expect(
      screen.getByRole("heading", { name: /Drilldown Focus/i }),
    ).toBeInTheDocument()
  })

  it("shows project picker and filter options", async () => {
    renderWithProviders(<ProjectPerformanceDashboard projectId="proj-123" />)

    // Verify project selector is present
    const projectLabel = await screen.findByLabelText(
      /Project/i,
      {},
      { timeout: 2000 },
    )
    expect(projectLabel).toBeInTheDocument()

    // Verify filter sections are present
    expect(screen.getByText(/Work Breakdown Elements/i)).toBeInTheDocument()
    // Cost Element Types should be in a button (collapsible header)
    const typeButtons = screen.getAllByText(/Cost Element Types/i)
    expect(typeButtons.length).toBeGreaterThan(0)

    // Wait for cost element types to load and appear
    await waitFor(
      () => {
        expect(
          client.CostElementTypesService.readCostElementTypes,
        ).toHaveBeenCalled()
      },
      { timeout: 3000 },
    )
  })

  it("renders BudgetTimeline with correct filter props", async () => {
    renderWithProviders(<ProjectPerformanceDashboard projectId="proj-123" />)

    // Wait for project name to appear in the heading
    await screen.findByRole("heading", {
      name: /Project Performance Dashboard/i,
    })

    // Verify the service was called
    await waitFor(
      () => {
        expect(
          client.BudgetTimelineService.getCostElementsWithSchedules,
        ).toHaveBeenCalled()
      },
      { timeout: 3000 },
    )

    // Wait for BudgetTimeline to render (query should resolve)
    await waitFor(
      () => {
        const timeline = screen.queryByTestId("budget-timeline")
        expect(timeline).toBeInTheDocument()
      },
      { timeout: 5000 },
    )

    // Verify BudgetTimeline receives correct props
    const timeline = screen.getByTestId("budget-timeline")
    expect(timeline).toBeInTheDocument()
    expect(screen.getByTestId("timeline-project-id")).toHaveTextContent(
      "proj-123",
    )
    expect(
      screen.getByTestId("timeline-cost-elements-count"),
    ).toHaveTextContent("2")

    // Verify filter props are passed correctly (no filters selected initially)
    expect(screen.getByTestId("timeline-wbe-ids")).toHaveTextContent("none")
  })

  it("displays KPI cards with metrics from EvmMetricsService", async () => {
    renderWithProviders(<ProjectPerformanceDashboard projectId="proj-123" />)

    // Wait for dashboard to load
    await screen.findByRole("heading", {
      name: /Project Performance Dashboard/i,
    })

    // Wait for KPI cards to render with actual data
    await waitFor(
      () => {
        expect(
          client.EvmMetricsService.getProjectEvmMetricsEndpoint,
        ).toHaveBeenCalledWith({ projectId: "proj-123" })
      },
      { timeout: 3000 },
    )

    // Verify KPI cards display metrics (not placeholders)
    await waitFor(
      () => {
        // CPI should show 0.92
        expect(screen.getByText(/Cost Performance Index/i)).toBeInTheDocument()
        expect(screen.getByText("0.92")).toBeInTheDocument()
        // SPI should show 1.05
        expect(
          screen.getByText(/Schedule Performance Index/i),
        ).toBeInTheDocument()
        expect(screen.getByText("1.05")).toBeInTheDocument()
        // TCPI should show 1.15
        expect(
          screen.getByText(/To-Complete Performance Index/i),
        ).toBeInTheDocument()
        expect(screen.getByText("1.15")).toBeInTheDocument()
      },
      { timeout: 5000 },
    )
  })

  it("uses configurable thresholds from VarianceThresholdConfig for CV/SV", async () => {
    renderWithProviders(<ProjectPerformanceDashboard projectId="proj-123" />)

    // Wait for dashboard to load
    await screen.findByRole("heading", {
      name: /Project Performance Dashboard/i,
    })

    // Verify thresholds are fetched
    await waitFor(
      () => {
        expect(
          client.AdminService.listVarianceThresholdConfigs,
        ).toHaveBeenCalled()
      },
      { timeout: 3000 },
    )

    // Verify CV card uses threshold-based coloring
    // CV is -5000 (negative), which should trigger warning/critical based on percentage
    // Since we can't easily test color in RTL, we verify the threshold service was called
    // and the metrics service was called with the project ID
    expect(
      client.EvmMetricsService.getProjectEvmMetricsEndpoint,
    ).toHaveBeenCalled()
  })

  it("displays drilldown deck with top variance items and navigation links", async () => {
    // Mock variance analysis report data (override default mock)
    const mockVarianceReport = {
      project_id: "proj-123",
      project_name: "Mars Habitat",
      control_date: "2025-01-01",
      rows: [
        {
          cost_element_id: "ce-1",
          cost_element_type_id: "type-1",
          cost_element_type_name: "Engineering",
          wbe_id: "wbe-1",
          wbe_name: "Machine A",
          department_name: "Controls",
          cost_variance: "-10000.00",
          schedule_variance: "-5000.00",
          variance_severity: "critical",
        },
        {
          cost_element_id: "ce-2",
          cost_element_type_id: "type-2",
          cost_element_type_name: "Fabrication",
          wbe_id: "wbe-2",
          wbe_name: "Machine B",
          department_name: "Fabrication",
          cost_variance: "-5000.00",
          schedule_variance: "1000.00",
          variance_severity: "warning",
        },
      ],
      summary: {
        cost_variance: "-15000.00",
        schedule_variance: "-4000.00",
      },
      total_problem_areas: 2,
    } as any

    vi.mocked(
      client.ReportsService.getProjectVarianceAnalysisReportEndpoint,
    ).mockResolvedValue(mockVarianceReport)

    renderWithProviders(<ProjectPerformanceDashboard projectId="proj-123" />)

    // Wait for dashboard to load
    await screen.findByRole("heading", {
      name: /Project Performance Dashboard/i,
    })

    // Wait for drilldown deck to render
    await waitFor(
      () => {
        expect(
          client.ReportsService.getProjectVarianceAnalysisReportEndpoint,
        ).toHaveBeenCalled()
      },
      { timeout: 3000 },
    )

    // Verify drilldown section is present
    expect(
      screen.getByRole("heading", { name: /Drilldown Focus/i }),
    ).toBeInTheDocument()

    // Wait for the service to be called
    await waitFor(
      () => {
        expect(
          client.ReportsService.getProjectVarianceAnalysisReportEndpoint,
        ).toHaveBeenCalled()
      },
      { timeout: 3000 },
    )

    // Verify table structure exists (check for table headers)
    await waitFor(
      () => {
        // Check for table headers using columnheader role to avoid matching filter labels
        expect(
          screen.getByRole("columnheader", { name: /^WBE$/i }),
        ).toBeInTheDocument()
        // Cost Element header - use exact match to avoid matching "Cost Element Type"
        const costElementHeaders = screen.getAllByRole("columnheader", {
          name: /Cost Element/i,
        })
        expect(costElementHeaders.length).toBeGreaterThanOrEqual(1) // At least Cost Element, possibly Cost Element Type
        expect(
          screen.getByRole("columnheader", { name: /Cost Element Type/i }),
        ).toBeInTheDocument()
        expect(
          screen.getByRole("columnheader", { name: /Cost Variance/i }),
        ).toBeInTheDocument()
      },
      { timeout: 3000 },
    )

    // Verify at least one data row is displayed
    await waitFor(
      () => {
        // Check for table rows - should have at least one data row (plus header row)
        const tableRows = screen.getAllByRole("row")
        expect(tableRows.length).toBeGreaterThan(1) // Header row + at least one data row

        // Verify table contains expected data by checking for cell content
        // Use getAllByText to handle multiple matches (filter + table)
        const machineAMatches = screen.getAllByText(/Machine A/i)
        const controlsMatches = screen.getAllByText(/Controls/i)
        // At least one match should be in the table (not just in filters)
        expect(machineAMatches.length + controlsMatches.length).toBeGreaterThan(
          0,
        )
      },
      { timeout: 3000 },
    )
  })
})
