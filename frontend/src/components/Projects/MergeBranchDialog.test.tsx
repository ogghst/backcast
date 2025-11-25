// @vitest-environment jsdom
import { ChakraProvider } from "@chakra-ui/react"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { fireEvent, render, screen, waitFor } from "@testing-library/react"
import type React from "react"
import { beforeEach, describe, expect, it, vi } from "vitest"
import * as client from "@/client"
import { ColorModeProvider } from "@/components/ui/color-mode"
import { BranchProvider } from "@/context/BranchContext"
import { system } from "@/theme"
import MergeBranchDialog from "./MergeBranchDialog"

vi.mock("@/client", () => ({
  BranchComparisonService: {
    compareBranches: vi.fn(),
  },
  ChangeOrdersService: {
    transitionChangeOrderStatus: vi.fn(),
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

describe("MergeBranchDialog", () => {
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
    vi.mocked(
      client.ChangeOrdersService.transitionChangeOrderStatus,
    ).mockResolvedValue({
      change_order_id: "co-1",
      change_order_number: "CO-001",
      title: "Test",
      workflow_status: "execute",
      project_id: "test-project-id",
      created_by_id: "user-1",
      created_at: "2025-01-01T00:00:00Z",
      entity_id: "co-1",
      status: "active",
      version: 1,
      branch: "co-001",
    })
  })

  it("shows merge confirmation", async () => {
    renderWithProviders(
      <MergeBranchDialog
        projectId="test-project-id"
        branch="co-001"
        changeOrderId="co-1"
        isOpen={true}
        onClose={() => {}}
      />,
    )

    await waitFor(() => {
      expect(screen.getByText(/merge branch/i)).toBeInTheDocument()
    })
  })

  it("displays merge summary", async () => {
    renderWithProviders(
      <MergeBranchDialog
        projectId="test-project-id"
        branch="co-001"
        changeOrderId="co-1"
        isOpen={true}
        onClose={() => {}}
      />,
    )

    await waitFor(() => {
      expect(screen.getByText(/summary|comparison/i)).toBeInTheDocument()
    })
  })

  it("executes merge on confirm", async () => {
    const onClose = vi.fn()
    renderWithProviders(
      <MergeBranchDialog
        projectId="test-project-id"
        branch="co-001"
        changeOrderId="co-1"
        isOpen={true}
        onClose={onClose}
      />,
    )

    await waitFor(() => {
      const confirmButton = screen.getByRole("button", {
        name: /confirm|merge/i,
      })
      expect(confirmButton).toBeInTheDocument()
    })

    const confirmButton = screen.getByRole("button", { name: /confirm|merge/i })
    fireEvent.click(confirmButton)

    await waitFor(() => {
      expect(
        client.ChangeOrdersService.transitionChangeOrderStatus,
      ).toHaveBeenCalled()
    })
  })
})
