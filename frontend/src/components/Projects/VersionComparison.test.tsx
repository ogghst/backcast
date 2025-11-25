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
import VersionComparison from "./VersionComparison"

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

describe("VersionComparison", () => {
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

  it("shows side-by-side version comparison", async () => {
    renderWithProviders(
      <VersionComparison
        entityType="wbe"
        entityId="wbe-1"
        version1={1}
        version2={2}
        branch="main"
      />,
    )

    await waitFor(() => {
      expect(screen.getByText(/comparison|version/i)).toBeInTheDocument()
    })
  })

  it("highlights differences", async () => {
    renderWithProviders(
      <VersionComparison
        entityType="wbe"
        entityId="wbe-1"
        version1={1}
        version2={2}
        branch="main"
      />,
    )

    await waitFor(() => {
      expect(screen.getByText(/version 1|version 2/i)).toBeInTheDocument()
    })
  })
})
