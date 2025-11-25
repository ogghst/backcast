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
import ChangeOrderDetailView from "./ChangeOrderDetailView"

vi.mock("@/client", () => ({
  ChangeOrdersService: {
    readChangeOrder: vi.fn(),
  },
  ChangeOrderLineItemsService: {
    listChangeOrderLineItems: vi.fn(),
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

const mockLineItems = [
  {
    operation_type: "create",
    target_type: "wbe",
    budget_change: "1000.00",
    revenue_change: "500.00",
    description: "Test line item",
  },
] as any

describe("ChangeOrderDetailView", () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(client.ChangeOrdersService.readChangeOrder).mockResolvedValue(
      mockChangeOrder,
    )
    vi.mocked(
      client.ChangeOrderLineItemsService.listChangeOrderLineItems,
    ).mockResolvedValue(mockLineItems)
  })

  it("displays all change order details", async () => {
    renderWithProviders(
      <ChangeOrderDetailView
        changeOrderId="co-1"
        projectId="test-project-id"
      />,
    )

    await waitFor(() => {
      expect(screen.getByText("Test Change Order")).toBeInTheDocument()
      expect(screen.getByText("CO-001")).toBeInTheDocument()
      expect(screen.getByText("Test description")).toBeInTheDocument()
      expect(screen.getByText("Test Party")).toBeInTheDocument()
    })
  })

  it("shows branch information", async () => {
    renderWithProviders(
      <ChangeOrderDetailView
        changeOrderId="co-1"
        projectId="test-project-id"
      />,
    )

    await waitFor(() => {
      expect(screen.getByText("co-001")).toBeInTheDocument()
    })
  })

  it("shows line items", async () => {
    renderWithProviders(
      <ChangeOrderDetailView
        changeOrderId="co-1"
        projectId="test-project-id"
      />,
    )

    await waitFor(() => {
      expect(screen.getByText("Line Items")).toBeInTheDocument()
      expect(screen.getByText("Test line item")).toBeInTheDocument()
    })
  })

  it("shows financial impact", async () => {
    renderWithProviders(
      <ChangeOrderDetailView
        changeOrderId="co-1"
        projectId="test-project-id"
      />,
    )

    await waitFor(() => {
      expect(screen.getByText("Financial Impact Summary")).toBeInTheDocument()
      expect(screen.getByText(/€1,000.00/)).toBeInTheDocument()
      expect(screen.getByText(/€500.00/)).toBeInTheDocument()
    })
  })

  it("shows workflow history", async () => {
    renderWithProviders(
      <ChangeOrderDetailView
        changeOrderId="co-1"
        projectId="test-project-id"
      />,
    )

    await waitFor(() => {
      expect(screen.getByText("design")).toBeInTheDocument()
    })
  })
})
