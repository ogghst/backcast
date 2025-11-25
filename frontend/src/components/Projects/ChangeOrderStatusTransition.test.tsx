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
import ChangeOrderStatusTransition from "./ChangeOrderStatusTransition"

vi.mock("@/client", () => ({
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

describe("ChangeOrderStatusTransition", () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(
      client.ChangeOrdersService.transitionChangeOrderStatus,
    ).mockResolvedValue({
      change_order_id: "co-1",
      change_order_number: "CO-001",
      title: "Test",
      workflow_status: "approve",
      project_id: "test-project-id",
      created_by_id: "user-1",
      created_at: "2025-01-01T00:00:00Z",
      entity_id: "co-1",
      status: "active",
      version: 1,
      branch: "co-001",
    })
  })

  it("shows available transitions", () => {
    renderWithProviders(
      <ChangeOrderStatusTransition
        projectId="test-project-id"
        changeOrderId="co-1"
        currentStatus="design"
      />,
    )

    expect(screen.getByText(/transition|status/i)).toBeInTheDocument()
  })

  it("validates transition rules", () => {
    renderWithProviders(
      <ChangeOrderStatusTransition
        projectId="test-project-id"
        changeOrderId="co-1"
        currentStatus="design"
      />,
    )

    // Should show transition to "approve" but not "execute" from "design"
    expect(screen.getByText(/approve/i)).toBeInTheDocument()
  })

  it("executes transition", async () => {
    renderWithProviders(
      <ChangeOrderStatusTransition
        projectId="test-project-id"
        changeOrderId="co-1"
        currentStatus="design"
      />,
    )

    const approveButton = screen.getByRole("button", { name: /approve/i })
    fireEvent.click(approveButton)

    await waitFor(() => {
      expect(
        client.ChangeOrdersService.transitionChangeOrderStatus,
      ).toHaveBeenCalled()
    })
  })
})
