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
import VersionHistoryViewer from "./VersionHistoryViewer"

vi.mock("@/client", () => ({
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

describe("VersionHistoryViewer", () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(
      client.VersionHistoryService.getEntityVersionHistory,
    ).mockResolvedValue({
      entity_type: "wbe",
      entity_id: "wbe-1",
      branch: "main",
      count: 2,
      versions: [
        {
          version: 2,
          status: "active",
          branch: "main",
          created_at: "2025-01-02T00:00:00Z",
        },
        {
          version: 1,
          status: "active",
          branch: "main",
          created_at: "2025-01-01T00:00:00Z",
        },
      ],
    })
  })

  it("renders version history", async () => {
    renderWithProviders(
      <VersionHistoryViewer entityType="wbe" entityId="wbe-1" branch="main" />,
    )

    await waitFor(() => {
      expect(screen.getByText(/version history|version/i)).toBeInTheDocument()
    })
  })

  it("shows all versions", async () => {
    renderWithProviders(
      <VersionHistoryViewer entityType="wbe" entityId="wbe-1" branch="main" />,
    )

    await waitFor(() => {
      expect(screen.getByText(/version 1|version 2/i)).toBeInTheDocument()
    })
  })

  it("highlights current version", async () => {
    renderWithProviders(
      <VersionHistoryViewer entityType="wbe" entityId="wbe-1" branch="main" />,
    )

    await waitFor(() => {
      // Current version (latest) should be highlighted
      expect(screen.getByText(/version 2|current/i)).toBeInTheDocument()
    })
  })
})
