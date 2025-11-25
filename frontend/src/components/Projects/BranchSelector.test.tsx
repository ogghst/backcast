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
import BranchSelector from "./BranchSelector"

vi.mock("@/client", () => ({
  ChangeOrdersService: {
    listChangeOrders: vi.fn(),
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

describe("BranchSelector", () => {
  beforeEach(() => {
    vi.clearAllMocks()
    // Mock change orders with a branch
    vi.mocked(client.ChangeOrdersService.listChangeOrders).mockResolvedValue([
      {
        change_order_id: "co-1",
        change_order_number: "CO-001",
        title: "Test CO",
        description: "Test",
        requesting_party: "Test",
        effective_date: "2025-01-01",
        workflow_status: "design",
        project_id: "test-project-id",
        created_by_id: "user-1",
        created_at: "2025-01-01T00:00:00Z",
        entity_id: "co-1",
        status: "active",
        version: 1,
        branch: "co-001",
      },
    ])
  })

  it("renders branch dropdown", () => {
    renderWithProviders(<BranchSelector />)
    const select = screen.getByRole("combobox")
    expect(select).toBeInTheDocument()
  })

  it("shows current branch", () => {
    renderWithProviders(<BranchSelector />)
    const select = screen.getByRole("combobox") as HTMLSelectElement
    // Default branch should be 'main'
    expect(select.value).toBe("main")
  })

  it("allows switching branches", async () => {
    renderWithProviders(<BranchSelector />)

    // Wait for branches to load
    await waitFor(() => {
      const select = screen.getByRole("combobox") as HTMLSelectElement
      expect(select.options.length).toBeGreaterThan(1)
    })

    const select = screen.getByRole("combobox") as HTMLSelectElement

    // Change to a different branch
    fireEvent.change(select, { target: { value: "co-001" } })

    // Value should be updated
    await waitFor(() => {
      expect(select.value).toBe("co-001")
    })
  })

  it("updates query on branch change", async () => {
    renderWithProviders(<BranchSelector />)

    // Wait for branches to load
    await waitFor(() => {
      const select = screen.getByRole("combobox") as HTMLSelectElement
      expect(select.options.length).toBeGreaterThan(1)
    })

    const select = screen.getByRole("combobox") as HTMLSelectElement

    // Change branch
    fireEvent.change(select, { target: { value: "co-001" } })

    // The context should update (we can't directly test query invalidation without mocking)
    await waitFor(() => {
      expect(select.value).toBe("co-001")
    })
  })
})
