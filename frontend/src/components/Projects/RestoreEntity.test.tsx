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
import RestoreEntity from "./RestoreEntity"

vi.mock("@/client", () => ({
  RestoreService: {
    restoreWbe: vi.fn(),
    restoreCostElement: vi.fn(),
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

describe("RestoreEntity", () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(client.RestoreService.restoreWbe).mockResolvedValue({
      wbe_id: "wbe-1",
      entity_id: "wbe-1",
      machine_type: "Test Machine",
      status: "active",
      version: 2,
      branch: "main",
    })
  })

  it("shows restore button for deleted entities", () => {
    renderWithProviders(
      <RestoreEntity entityType="wbe" entityId="wbe-1" branch="main" />,
    )

    expect(screen.getByRole("button", { name: /restore/i })).toBeInTheDocument()
  })

  it("executes restore", async () => {
    renderWithProviders(
      <RestoreEntity entityType="wbe" entityId="wbe-1" branch="main" />,
    )

    const restoreButton = screen.getByRole("button", { name: /restore/i })
    fireEvent.click(restoreButton)

    await waitFor(() => {
      expect(client.RestoreService.restoreWbe).toHaveBeenCalled()
    })
  })
})
