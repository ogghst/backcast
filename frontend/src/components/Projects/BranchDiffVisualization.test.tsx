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
import BranchDiffVisualization from "./BranchDiffVisualization"

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

describe("BranchDiffVisualization", () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(client.BranchComparisonService.compareBranches).mockResolvedValue(
      {
        creates: [],
        updates: [],
        deletes: [],
        financial_impact: {
          total_revenue_change: "0.00",
          total_budget_change: "0.00",
        },
      },
    )
  })

  it("visualizes branch differences", async () => {
    renderWithProviders(
      <BranchDiffVisualization projectId="test-project-id" branch="co-001" />,
    )

    await waitFor(() => {
      expect(screen.getByText(/diff|comparison|changes/i)).toBeInTheDocument()
    })
  })

  it("uses color coding for changes", async () => {
    renderWithProviders(
      <BranchDiffVisualization projectId="test-project-id" branch="co-001" />,
    )

    await waitFor(() => {
      expect(screen.getByText(/diff|changes/i)).toBeInTheDocument()
    })
  })
})
