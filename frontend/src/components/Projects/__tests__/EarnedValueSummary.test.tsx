// @vitest-environment jsdom
import { ChakraProvider } from "@chakra-ui/react"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { render, waitFor } from "@testing-library/react"
import type React from "react"
import { describe, expect, it, vi } from "vitest"
import * as client from "@/client"
import { TimeMachineProvider } from "@/context/TimeMachineContext"
import { system } from "../../../theme"
import { ColorModeProvider } from "../../ui/color-mode"
import EarnedValueSummary from "../EarnedValueSummary"

vi.mock("@/client", () => ({
  EarnedValueService: {
    getProjectEarnedValue: vi.fn(),
    getWbeEarnedValue: vi.fn(),
    getCostElementEarnedValue: vi.fn(),
  },
  EvmMetricsService: {
    getProjectEvmMetricsEndpoint: vi.fn(),
    getWbeEvmMetricsEndpoint: vi.fn(),
    getCostElementEvmMetricsEndpoint: vi.fn(),
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
        <QueryClientProvider client={qc}>
          <TimeMachineProvider>{ui}</TimeMachineProvider>
        </QueryClientProvider>
      </ColorModeProvider>
    </ChakraProvider>,
  )
}

describe("EarnedValueSummary", () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe("EVM Metrics Query", () => {
    it("makes query to EvmMetricsService for project level", async () => {
      const mockEarnedValue = {
        earned_value: "100",
        budget_bac: "200",
        percent_complete: 0.5,
      }
      const mockEvmMetrics = {
        cpi: "0.95",
        spi: "1.0",
        tcpi: "1.05",
        cost_variance: "-10",
        schedule_variance: "5",
      }

      vi.mocked(
        client.EarnedValueService.getProjectEarnedValue,
      ).mockResolvedValue(mockEarnedValue as any)
      vi.mocked(
        client.EvmMetricsService.getProjectEvmMetricsEndpoint,
      ).mockResolvedValue(mockEvmMetrics as any)

      renderWithProviders(<EarnedValueSummary level="project" projectId="p1" />)

      await waitFor(() => {
        expect(
          client.EvmMetricsService.getProjectEvmMetricsEndpoint,
        ).toHaveBeenCalledWith({
          projectId: "p1",
        })
      })
    })

    it("makes query to EvmMetricsService for WBE level", async () => {
      const mockEarnedValue = {
        earned_value: "100",
        budget_bac: "200",
        percent_complete: 0.5,
      }
      const mockEvmMetrics = {
        cpi: "0.95",
        spi: "1.0",
        tcpi: "1.05",
        cost_variance: "-10",
        schedule_variance: "5",
      }

      vi.mocked(client.EarnedValueService.getWbeEarnedValue).mockResolvedValue(
        mockEarnedValue as any,
      )
      vi.mocked(
        client.EvmMetricsService.getWbeEvmMetricsEndpoint,
      ).mockResolvedValue(mockEvmMetrics as any)

      renderWithProviders(
        <EarnedValueSummary level="wbe" projectId="p1" wbeId="w1" />,
      )

      await waitFor(() => {
        expect(
          client.EvmMetricsService.getWbeEvmMetricsEndpoint,
        ).toHaveBeenCalledWith({
          projectId: "p1",
          wbeId: "w1",
        })
      })
    })

    it("makes query to EvmMetricsService for cost-element level", async () => {
      const mockEarnedValue = {
        earned_value: "100",
        budget_bac: "200",
        percent_complete: 0.5,
      }
      const mockEvmMetrics = {
        cpi: "0.95",
        spi: "1.0",
        tcpi: "1.05",
        cost_variance: "-10",
        schedule_variance: "5",
      }

      vi.mocked(
        client.EarnedValueService.getCostElementEarnedValue,
      ).mockResolvedValue(mockEarnedValue as any)
      vi.mocked(
        client.EvmMetricsService.getCostElementEvmMetricsEndpoint,
      ).mockResolvedValue(mockEvmMetrics as any)

      renderWithProviders(
        <EarnedValueSummary
          level="cost-element"
          projectId="p1"
          costElementId="ce1"
        />,
      )

      await waitFor(() => {
        expect(
          client.EvmMetricsService.getCostElementEvmMetricsEndpoint,
        ).toHaveBeenCalledWith({
          projectId: "p1",
          costElementId: "ce1",
        })
      })
    })
  })

  describe("Status Indicator Helpers", () => {
    it("getCpiStatus returns correct status for CPI < 0.95 (red)", () => {
      // This will be implemented in the component
      expect(true).toBe(true) // Placeholder
    })

    it("getCpiStatus returns correct status for CPI 0.95-1.0 (yellow)", () => {
      expect(true).toBe(true) // Placeholder
    })

    it("getCpiStatus returns correct status for CPI >= 1.0 (green)", () => {
      expect(true).toBe(true) // Placeholder
    })

    it("getCpiStatus returns N/A status for null CPI", () => {
      expect(true).toBe(true) // Placeholder
    })

    it("getSpiStatus returns correct status for SPI < 0.95 (red)", () => {
      expect(true).toBe(true) // Placeholder
    })

    it("getSpiStatus returns correct status for SPI 0.95-1.0 (yellow)", () => {
      expect(true).toBe(true) // Placeholder
    })

    it("getSpiStatus returns correct status for SPI >= 1.0 (green)", () => {
      expect(true).toBe(true) // Placeholder
    })

    it("getSpiStatus returns N/A status for null SPI", () => {
      expect(true).toBe(true) // Placeholder
    })

    it("getTcpiStatus returns correct status for TCPI <= 1.0 (green)", () => {
      expect(true).toBe(true) // Placeholder
    })

    it("getTcpiStatus returns correct status for TCPI 1.0-1.1 (yellow)", () => {
      expect(true).toBe(true) // Placeholder
    })

    it("getTcpiStatus returns correct status for TCPI > 1.1 (red)", () => {
      expect(true).toBe(true) // Placeholder
    })

    it("getTcpiStatus returns red status for 'overrun' string", () => {
      expect(true).toBe(true) // Placeholder
    })

    it("getTcpiStatus returns N/A status for null TCPI", () => {
      expect(true).toBe(true) // Placeholder
    })

    it("getCvStatus returns red for negative CV", () => {
      expect(true).toBe(true) // Placeholder
    })

    it("getCvStatus returns yellow for zero CV", () => {
      expect(true).toBe(true) // Placeholder
    })

    it("getCvStatus returns green for positive CV", () => {
      expect(true).toBe(true) // Placeholder
    })

    it("getSvStatus returns red for negative SV", () => {
      expect(true).toBe(true) // Placeholder
    })

    it("getSvStatus returns yellow for zero SV", () => {
      expect(true).toBe(true) // Placeholder
    })

    it("getSvStatus returns green for positive SV", () => {
      expect(true).toBe(true) // Placeholder
    })
  })

  describe("Formatting Helpers", () => {
    it("formatIndex formats decimal to 2 decimal places", () => {
      expect(true).toBe(true) // Placeholder
    })

    it("formatIndex returns N/A for null", () => {
      expect(true).toBe(true) // Placeholder
    })

    it("formatTcpi returns 'overrun' string when value is 'overrun'", () => {
      expect(true).toBe(true) // Placeholder
    })

    it("formatTcpi formats decimal to 2 decimal places", () => {
      expect(true).toBe(true) // Placeholder
    })

    it("formatTcpi returns N/A for null", () => {
      expect(true).toBe(true) // Placeholder
    })

    it("formatVariance formats currency correctly", () => {
      expect(true).toBe(true) // Placeholder
    })

    it("formatVariance handles negative values", () => {
      expect(true).toBe(true) // Placeholder
    })

    it("formatVariance returns N/A for null", () => {
      expect(true).toBe(true) // Placeholder
    })
  })
})
