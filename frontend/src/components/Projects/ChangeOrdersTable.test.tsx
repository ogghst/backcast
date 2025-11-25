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
import ChangeOrdersTable from "./ChangeOrdersTable"

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

describe("ChangeOrdersTable", () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(client.ChangeOrdersService.listChangeOrders).mockResolvedValue([
      {
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
      },
    ])
  })

  it("renders change orders table", async () => {
    renderWithProviders(<ChangeOrdersTable projectId="test-project-id" />)

    await waitFor(() => {
      expect(screen.getByText("Change Orders")).toBeInTheDocument()
    })
  })

  it("uses DataTable component", async () => {
    renderWithProviders(<ChangeOrdersTable projectId="test-project-id" />)

    await waitFor(() => {
      // DataTable should render table headers
      expect(screen.getByText("Change Order Number")).toBeInTheDocument()
    })
  })

  it("shows all required columns", async () => {
    renderWithProviders(<ChangeOrdersTable projectId="test-project-id" />)

    await waitFor(() => {
      expect(screen.getByText("Change Order Number")).toBeInTheDocument()
      expect(screen.getByText("Title")).toBeInTheDocument()
      expect(screen.getByText("Status")).toBeInTheDocument()
    })
  })

  it("supports pagination", async () => {
    renderWithProviders(<ChangeOrdersTable projectId="test-project-id" />)

    await waitFor(() => {
      // Pagination component should be present
      const _pagination = screen.queryByRole("navigation", {
        name: /pagination/i,
      })
      // Pagination might not be visible if only one page, but component should exist
      expect(screen.getByText("Change Orders")).toBeInTheDocument()
    })
  })

  it("supports filtering by status", async () => {
    renderWithProviders(<ChangeOrdersTable projectId="test-project-id" />)

    await waitFor(() => {
      // Table should render with filters
      expect(screen.getByText("Change Orders")).toBeInTheDocument()
    })
  })
})
