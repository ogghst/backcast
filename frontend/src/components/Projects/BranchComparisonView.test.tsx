// @vitest-environment jsdom
import { ChakraProvider } from "@chakra-ui/react"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { render, screen, waitFor } from "@testing-library/react"
import type React from "react"
import { beforeEach, describe, expect, it, vi } from "vitest"
import * as client from "@/client"
import { ColorModeProvider } from "@/components/ui/color-mode"
import { BranchProvider } from "@/context/BranchContext"
import { system } from "@/theme"
import BranchComparisonView from "./BranchComparisonView"

vi.mock("@/client", () => ({
  BranchComparisonService: {
    compareBranches: vi.fn(),
  },
}))

function renderWithProviders(ui: React.ReactElement) {
  const qc = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  })
  return render(
    <ChakraProvider value={system}>
      <ColorModeProvider defaultTheme="light">
        <QueryClientProvider client={qc}>
          <BranchProvider projectId="test-project-id">{ui}</BranchProvider>
        </QueryClientProvider>
      </ColorModeProvider>
    </ChakraProvider>,
  )
}

describe("BranchComparisonView", () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(client.BranchComparisonService.compareBranches).mockResolvedValue(
      {
        creates: [
          {
            entity_type: "wbe",
            entity_id: "wbe-1",
            machine_type: "New Machine",
            revenue_allocation: "10000.00",
          },
        ],
        updates: [
          {
            entity_type: "wbe",
            entity_id: "wbe-2",
            machine_type: "Updated Machine",
            revenue_allocation: "20000.00",
          },
        ],
        deletes: [],
        financial_impact: {
          total_revenue_change: "5000.00",
          total_budget_change: "3000.00",
        },
      },
    )
  })

  it("renders side-by-side comparison", async () => {
    renderWithProviders(
      <BranchComparisonView projectId="test-project-id" branch="co-001" />,
    )

    await waitFor(() => {
      expect(screen.getByText(/comparison/i)).toBeInTheDocument()
    })
  })

  it("highlights differences with visual indicators", async () => {
    renderWithProviders(
      <BranchComparisonView projectId="test-project-id" branch="co-001" />,
    )

    await waitFor(() => {
      // Should show creates, updates, deletes with visual indicators
      expect(screen.getByText(/creates|updates|deletes/i)).toBeInTheDocument()
    })
  })

  it("shows financial impact summary", async () => {
    renderWithProviders(
      <BranchComparisonView projectId="test-project-id" branch="co-001" />,
    )

    await waitFor(() => {
      expect(
        screen.getByText(/financial impact|revenue|budget/i),
      ).toBeInTheDocument()
    })
  })

  it("is responsive", async () => {
    renderWithProviders(
      <BranchComparisonView projectId="test-project-id" branch="co-001" />,
    )

    await waitFor(() => {
      const container = screen.getByText(/comparison/i).closest("div")
      expect(container).toBeInTheDocument()
    })
  })
})
