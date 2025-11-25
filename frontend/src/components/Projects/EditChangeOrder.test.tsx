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
import EditChangeOrder from "./EditChangeOrder"

vi.mock("@/client", () => ({
  ChangeOrdersService: {
    updateChangeOrder: vi.fn(),
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

const mockChangeOrder = {
  change_order_id: "co-1",
  change_order_number: "CO-001",
  title: "Test Change Order",
  description: "Test description",
  requesting_party: "Test Party",
  effective_date: "2025-01-01",
  workflow_status: "design",
  project_id: "test-project-id",
  created_by_id: "user-1",
  created_at: "2025-01-01T00:00:00Z",
  entity_id: "co-1",
  status: "active",
  version: 1,
  branch: "co-001",
} as any

describe("EditChangeOrder", () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(client.ChangeOrdersService.updateChangeOrder).mockResolvedValue(
      mockChangeOrder,
    )
  })

  it("renders form with pre-filled data", async () => {
    renderWithProviders(<EditChangeOrder changeOrder={mockChangeOrder} />)

    const trigger = screen.getByRole("button", { name: /edit change order/i })
    fireEvent.click(trigger)

    await waitFor(() => {
      const titleInput = screen.getByLabelText(/title/i) as HTMLInputElement
      expect(titleInput.value).toBe("Test Change Order")
    })
  })

  it("only allows editing in 'design' status", async () => {
    const nonDesignCO = { ...mockChangeOrder, workflow_status: "approve" }
    renderWithProviders(<EditChangeOrder changeOrder={nonDesignCO} />)

    const trigger = screen.getByRole("button", { name: /edit change order/i })
    expect(trigger).toBeDisabled()
  })

  it("validates fields", async () => {
    renderWithProviders(<EditChangeOrder changeOrder={mockChangeOrder} />)

    const trigger = screen.getByRole("button", { name: /edit change order/i })
    fireEvent.click(trigger)

    await waitFor(() => {
      const titleInput = screen.getByLabelText(/title/i)
      fireEvent.change(titleInput, { target: { value: "" } })
    })

    const submitButton = screen.getByRole("button", { name: /save/i })
    fireEvent.click(submitButton)

    await waitFor(() => {
      expect(screen.getByText(/title is required/i)).toBeInTheDocument()
    })
  })

  it("submits updates", async () => {
    renderWithProviders(<EditChangeOrder changeOrder={mockChangeOrder} />)

    const trigger = screen.getByRole("button", { name: /edit change order/i })
    fireEvent.click(trigger)

    await waitFor(() => {
      const titleInput = screen.getByLabelText(/title/i)
      fireEvent.change(titleInput, { target: { value: "Updated Title" } })
    })

    const submitButton = screen.getByRole("button", { name: /save/i })
    fireEvent.click(submitButton)

    await waitFor(() => {
      expect(client.ChangeOrdersService.updateChangeOrder).toHaveBeenCalled()
    })
  })
})
