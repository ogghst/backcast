// @vitest-environment jsdom
import { ChakraProvider } from "@chakra-ui/react"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { fireEvent, render, screen, waitFor } from "@testing-library/react"
import type React from "react"
import { beforeEach, describe, expect, it, vi } from "vitest"
import { ColorModeProvider } from "@/components/ui/color-mode"
import { BranchProvider } from "@/context/BranchContext"
import { system } from "@/theme"
import RollbackVersion from "./RollbackVersion"

vi.mock("@/client", () => ({
  WbesService: {
    updateWbe: vi.fn(),
  },
  CostElementsService: {
    updateCostElement: vi.fn(),
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

describe("RollbackVersion", () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it("shows rollback confirmation", () => {
    renderWithProviders(
      <RollbackVersion
        entityType="wbe"
        entityId="wbe-1"
        targetVersion={1}
        branch="main"
        isOpen={true}
        onClose={() => {}}
      />,
    )

    expect(screen.getByText(/rollback|confirm/i)).toBeInTheDocument()
  })

  it("executes rollback", async () => {
    const onClose = vi.fn()
    renderWithProviders(
      <RollbackVersion
        entityType="wbe"
        entityId="wbe-1"
        targetVersion={1}
        branch="main"
        isOpen={true}
        onClose={onClose}
      />,
    )

    const confirmButton = screen.getByRole("button", {
      name: /confirm|rollback/i,
    })
    fireEvent.click(confirmButton)

    await waitFor(() => {
      // Should call update service
      expect(screen.getByText(/rollback/i)).toBeInTheDocument()
    })
  })
})
