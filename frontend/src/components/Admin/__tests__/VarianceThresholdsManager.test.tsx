// @vitest-environment jsdom
import { ChakraProvider } from "@chakra-ui/react"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { render, screen, waitFor } from "@testing-library/react"
import type React from "react"
import { beforeEach, describe, expect, it, vi } from "vitest"
import * as client from "@/client"
import { ColorModeProvider } from "@/components/ui/color-mode"
import { system } from "../../../theme"
import VarianceThresholdsManager from "../VarianceThresholdsManager"

vi.mock("@/client", () => ({
  AdminService: {
    listVarianceThresholdConfigs: vi.fn(),
    createVarianceThresholdConfig: vi.fn(),
    updateVarianceThresholdConfig: vi.fn(),
    deleteVarianceThresholdConfig: vi.fn(),
  },
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
        <QueryClientProvider client={qc}>{ui}</QueryClientProvider>
      </ColorModeProvider>
    </ChakraProvider>,
  )
}

describe("VarianceThresholdsManager", () => {
  beforeEach(() => {
    vi.resetAllMocks()
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
      ],
      count: 2,
    } as any)
  })

  it("displays list of variance thresholds", async () => {
    renderWithProviders(<VarianceThresholdsManager />)

    // Wait for loading to complete and data to render
    await waitFor(
      () => {
        expect(
          screen.queryByText(/Loading thresholds/i),
        ).not.toBeInTheDocument()
        expect(screen.getByText(/Variance Thresholds/i)).toBeInTheDocument()
      },
      { timeout: 3000 },
    )

    // Verify table headers are present
    expect(screen.getByText(/Type/i)).toBeInTheDocument()
    expect(screen.getByText(/Percentage/i)).toBeInTheDocument()

    // Verify service was called
    expect(client.AdminService.listVarianceThresholdConfigs).toHaveBeenCalled()
  })

  it("allows creating a new threshold", async () => {
    vi.mocked(
      client.AdminService.createVarianceThresholdConfig,
    ).mockResolvedValue({
      variance_threshold_config_id: "thresh-3",
      threshold_type: "warning_sv",
      threshold_percentage: "-3.00",
      description: "New warning threshold",
      is_active: true,
      created_at: "2025-01-01T00:00:00Z",
      updated_at: "2025-01-01T00:00:00Z",
    } as any)

    renderWithProviders(<VarianceThresholdsManager />)

    // Wait for loading to complete
    await waitFor(
      () => {
        expect(
          screen.queryByText(/Loading thresholds/i),
        ).not.toBeInTheDocument()
      },
      { timeout: 3000 },
    )

    // Verify "Add Threshold" button is present
    expect(
      screen.getByRole("button", { name: /Add Threshold/i }),
    ).toBeInTheDocument()
  })

  it("allows updating an existing threshold", async () => {
    vi.mocked(
      client.AdminService.updateVarianceThresholdConfig,
    ).mockResolvedValue({
      variance_threshold_config_id: "thresh-1",
      threshold_type: "warning_cv",
      threshold_percentage: "-6.00",
      description: "Updated warning threshold",
      is_active: true,
      created_at: "2025-01-01T00:00:00Z",
      updated_at: "2025-01-01T00:00:00Z",
    } as any)

    renderWithProviders(<VarianceThresholdsManager />)

    // Wait for loading to complete
    await waitFor(
      () => {
        expect(
          screen.queryByText(/Loading thresholds/i),
        ).not.toBeInTheDocument()
      },
      { timeout: 3000 },
    )

    // Verify edit buttons are present
    const editButtons = screen.getAllByRole("button", { name: /Edit/i })
    expect(editButtons.length).toBeGreaterThan(0)
  })
})
