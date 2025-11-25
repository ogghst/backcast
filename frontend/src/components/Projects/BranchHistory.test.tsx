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
import BranchHistory from "./BranchHistory"

vi.mock("@/client", () => ({
  ChangeOrdersService: {
    listChangeOrders: vi.fn(),
  },
  VersionHistoryService: {
    getEntityVersionHistory: vi.fn(),
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

describe("BranchHistory", () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(client.ChangeOrdersService.listChangeOrders).mockResolvedValue([
      {
        change_order_id: "co-1",
        change_order_number: "CO-001",
        title: "Test",
        branch: "co-001",
        workflow_status: "design",
        project_id: "test-project-id",
        created_by_id: "user-1",
        created_at: "2025-01-01T00:00:00Z",
        entity_id: "co-1",
        status: "active",
        version: 1,
      },
    ])
  })

  it("displays branch history", async () => {
    renderWithProviders(
      <BranchHistory projectId="test-project-id" branch="co-001" />,
    )

    await waitFor(() => {
      expect(screen.getByText(/history|audit|timeline/i)).toBeInTheDocument()
    })
  })

  it("shows audit trail", async () => {
    renderWithProviders(
      <BranchHistory projectId="test-project-id" branch="co-001" />,
    )

    await waitFor(() => {
      expect(screen.getByText(/history|audit/i)).toBeInTheDocument()
    })
  })
})
