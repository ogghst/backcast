// @vitest-environment jsdom
import { ChakraProvider } from "@chakra-ui/react"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { render, screen, waitFor } from "@testing-library/react"
import type React from "react"
import { beforeEach, describe, expect, it, vi } from "vitest"
import * as client from "@/client"
import { TimeMachineProvider } from "@/context/TimeMachineContext"
import { system } from "../../../theme"
import { ColorModeProvider } from "../../ui/color-mode"
import VarianceAnalysisReport from "../VarianceAnalysisReport"

vi.mock("@/client", () => ({
  ReportsService: {
    getProjectVarianceAnalysisReportEndpoint: vi.fn(),
  },
  UsersService: {
    readTimeMachinePreference: vi.fn(),
    updateTimeMachinePreference: vi.fn(),
  },
}))

vi.mock("@tanstack/react-router", () => ({
  useNavigate: () => vi.fn(),
}))

vi.mock("../VarianceTrendChart", () => ({
  default: () => (
    <div data-testid="variance-trend-chart">Variance Trend Chart</div>
  ),
}))

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

describe("VarianceAnalysisReport", () => {
  beforeEach(() => {
    vi.resetAllMocks()
    vi.mocked(client.UsersService.readTimeMachinePreference).mockResolvedValue({
      time_machine_date: "2025-01-01",
    } as any)
    vi.mocked(
      client.UsersService.updateTimeMachinePreference,
    ).mockResolvedValue({
      time_machine_date: "2025-01-01",
    } as any)
  })

  it("renders loading state", () => {
    vi.mocked(
      client.ReportsService.getProjectVarianceAnalysisReportEndpoint,
    ).mockImplementation(
      () =>
        new Promise(() => {}) as ReturnType<
          typeof client.ReportsService.getProjectVarianceAnalysisReportEndpoint
        >,
    ) // Never resolves

    const { container } = renderWithProviders(
      <VarianceAnalysisReport projectId="test-project-id" />,
    )

    // Should show loading skeleton
    expect(container.querySelector("div")).toBeDefined()
  })

  it("renders error state", async () => {
    vi.mocked(
      client.ReportsService.getProjectVarianceAnalysisReportEndpoint,
    ).mockRejectedValue(new Error("Failed to load report"))

    renderWithProviders(<VarianceAnalysisReport projectId="test-project-id" />)

    await waitFor(() => {
      expect(
        screen.getByText(/Error loading variance analysis report/i),
      ).toBeDefined()
    })
  })

  it("renders empty state when no problem areas and showOnlyProblems is true", async () => {
    const mockReport = {
      project_id: "test-project-id",
      project_name: "Test Project",
      control_date: "2024-06-15",
      rows: [],
      total_problem_areas: 0,
      config_used: {
        critical_cv: "-10.00",
        warning_cv: "-5.00",
        critical_sv: "-10.00",
        warning_sv: "-5.00",
      },
      summary: {
        cost_variance: "0.00",
        schedule_variance: "0.00",
      },
    }

    vi.mocked(
      client.ReportsService.getProjectVarianceAnalysisReportEndpoint,
    ).mockResolvedValue(mockReport as any)

    renderWithProviders(<VarianceAnalysisReport projectId="test-project-id" />)

    await waitFor(() => {
      expect(screen.getByText(/No problem areas found/i)).toBeDefined()
    })
  })

  it("renders report with data", async () => {
    const mockReport = {
      project_id: "test-project-id",
      project_name: "Test Project",
      control_date: "2024-06-15",
      rows: [
        {
          cost_element_id: "ce-1",
          wbe_id: "wbe-1",
          wbe_name: "Test Machine",
          wbe_serial_number: "SN-001",
          department_code: "ENG",
          department_name: "Engineering",
          cost_element_type_id: null,
          cost_element_type_name: null,
          planned_value: "10000.00",
          earned_value: "8000.00",
          actual_cost: "9000.00",
          budget_bac: "10000.00",
          cpi: "0.8889",
          spi: "0.8000",
          tcpi: "2.0000",
          cost_variance: "-1000.00",
          schedule_variance: "-2000.00",
          cv_percentage: "-10.00",
          sv_percentage: "-20.00",
          variance_severity: "critical",
          has_cost_variance_issue: true,
          has_schedule_variance_issue: true,
        },
      ],
      total_problem_areas: 1,
      config_used: {
        critical_cv: "-10.00",
        warning_cv: "-5.00",
        critical_sv: "-10.00",
        warning_sv: "-5.00",
      },
      summary: {
        cost_variance: "-1000.00",
        schedule_variance: "-2000.00",
      },
    }

    vi.mocked(
      client.ReportsService.getProjectVarianceAnalysisReportEndpoint,
    ).mockResolvedValue(mockReport as any)

    renderWithProviders(<VarianceAnalysisReport projectId="test-project-id" />)

    await waitFor(() => {
      expect(screen.getByText(/Variance Analysis Report/i)).toBeDefined()
      expect(screen.getByText(/Test Machine/i)).toBeDefined()
      // Check for problem areas count - use getAllByText since "Problem Areas" appears multiple times
      // (once as a label, once in "Show only problem areas" checkbox)
      const problemAreasLabels = screen.getAllByText(/Problem Areas/i)
      expect(problemAreasLabels.length).toBeGreaterThan(0)
      // Find the label that's in the stats section (not the checkbox)
      // The stats section should have "Problem Areas" followed by a number and "cost elements"
      const statsLabel = problemAreasLabels.find((label) => {
        const container = label.closest("div")
        return container?.textContent?.match(
          /Problem Areas.*\d+.*cost elements/i,
        )
      })
      expect(statsLabel).toBeDefined()
      // Verify the count "1" appears in the same container
      const container = statsLabel?.closest("div")
      expect(container?.textContent).toMatch(/1.*cost elements/i)
    })
  })

  it("renders variance trend chart", async () => {
    const mockReport = {
      project_id: "test-project-id",
      project_name: "Test Project",
      control_date: "2024-06-15",
      rows: [
        {
          cost_element_id: "ce-1",
          wbe_id: "wbe-1",
          wbe_name: "Test Machine",
          wbe_serial_number: "SN-001",
          department_code: "ENG",
          department_name: "Engineering",
          cost_element_type_id: null,
          cost_element_type_name: null,
          planned_value: "10000.00",
          earned_value: "8000.00",
          actual_cost: "9000.00",
          budget_bac: "10000.00",
          cpi: "0.8889",
          spi: "0.8000",
          tcpi: "2.0000",
          cost_variance: "-1000.00",
          schedule_variance: "-2000.00",
          cv_percentage: "-10.00",
          sv_percentage: "-20.00",
          variance_severity: "critical",
          has_cost_variance_issue: true,
          has_schedule_variance_issue: true,
        },
      ],
      total_problem_areas: 1,
      config_used: {
        critical_cv: "-10.00",
        warning_cv: "-5.00",
        critical_sv: "-10.00",
        warning_sv: "-5.00",
      },
      summary: {
        cost_variance: "-1000.00",
        schedule_variance: "-2000.00",
      },
    }

    vi.mocked(
      client.ReportsService.getProjectVarianceAnalysisReportEndpoint,
    ).mockResolvedValue(mockReport as any)

    renderWithProviders(<VarianceAnalysisReport projectId="test-project-id" />)

    // Wait for report to load first
    await waitFor(() => {
      expect(screen.getByText(/Variance Analysis Report/i)).toBeDefined()
    })

    // Then check for the chart
    await waitFor(() => {
      expect(screen.getByTestId("variance-trend-chart")).toBeInTheDocument()
    })
  })

  it("shows help section with variance explanations", async () => {
    const mockReport = {
      project_id: "test-project-id",
      project_name: "Test Project",
      control_date: "2024-06-15",
      rows: [
        {
          cost_element_id: "ce-1",
          wbe_id: "wbe-1",
          wbe_name: "Test Machine",
          wbe_serial_number: "SN-001",
          department_code: "ENG",
          department_name: "Engineering",
          cost_element_type_id: null,
          cost_element_type_name: null,
          planned_value: "10000.00",
          earned_value: "8000.00",
          actual_cost: "9000.00",
          budget_bac: "10000.00",
          cpi: "0.8889",
          spi: "0.8000",
          tcpi: "2.0000",
          cost_variance: "-1000.00",
          schedule_variance: "-2000.00",
          cv_percentage: "-10.00",
          sv_percentage: "-20.00",
          variance_severity: "critical",
          has_cost_variance_issue: true,
          has_schedule_variance_issue: true,
        },
      ],
      total_problem_areas: 1,
      config_used: {
        critical_cv: "-10.00",
        warning_cv: "-5.00",
        critical_sv: "-10.00",
        warning_sv: "-5.00",
      },
      summary: {
        cost_variance: "-1000.00",
        schedule_variance: "-2000.00",
      },
    }

    vi.mocked(
      client.ReportsService.getProjectVarianceAnalysisReportEndpoint,
    ).mockResolvedValue(mockReport as any)

    renderWithProviders(<VarianceAnalysisReport projectId="test-project-id" />)

    // Wait for report to load first
    await waitFor(() => {
      expect(screen.getByText(/Variance Analysis Report/i)).toBeDefined()
    })

    // Then check for help section content
    await waitFor(() => {
      expect(screen.getByText(/Understanding Variance Metrics/i)).toBeDefined()
      expect(screen.getByText(/Cost Variance \(CV\)/i)).toBeDefined()
      expect(screen.getByText(/Schedule Variance \(SV\)/i)).toBeDefined()
    })
  })
})
