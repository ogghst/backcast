// @vitest-environment jsdom
import { ChakraProvider } from "@chakra-ui/react"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { fireEvent, render, screen, waitFor } from "@testing-library/react"
import type React from "react"
import { afterEach, describe, expect, it, vi } from "vitest"
import { ColorModeProvider } from "@/components/ui/color-mode"
import { TimeMachineProvider } from "@/context/TimeMachineContext"
import { system } from "../../../theme"
import ViewBaseline from "../ViewBaseline"

vi.mock("@/components/Projects/AIChat", () => ({
  default: ({
    contextType,
    contextId,
  }: {
    contextType: string
    contextId: string
  }) => (
    <div
      data-testid="ai-chat"
      data-context-type={contextType}
      data-context-id={contextId}
    >
      AI Chat Component
    </div>
  ),
}))

vi.mock("@/components/Projects/BaselineSummary", () => ({
  default: () => <div data-testid="baseline-summary" />,
}))

vi.mock("@/components/Projects/BaselineCostElementsByWBETable", () => ({
  default: () => <div data-testid="baseline-cost-elements-by-wbe" />,
}))

vi.mock("@/components/Projects/BaselineCostElementsTable", () => ({
  default: () => <div data-testid="baseline-cost-elements-table" />,
}))

vi.mock("@/components/Projects/BaselineEarnedValueEntriesTable", () => ({
  default: () => <div data-testid="baseline-earned-value-entries" />,
}))

function renderWithProviders(ui: React.ReactElement) {
  const qc = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
    },
  })
  return render(
    <ChakraProvider value={system}>
      <ColorModeProvider defaultTheme="light">
        <QueryClientProvider client={qc}>
          <TimeMachineProvider>{ui}</TimeMachineProvider>
        </QueryClientProvider>
      </ColorModeProvider>
    </ChakraProvider>,
  )
}

describe("ViewBaseline AI Assessment Tab", () => {
  afterEach(() => {
    vi.clearAllMocks()
  })

  const mockBaseline = {
    baseline_id: "baseline-123",
    baseline_type: "original",
    baseline_date: "2024-01-15",
    description: "Test Baseline",
    is_cancelled: false,
    created_at: "2024-01-15T10:00:00Z",
    milestone_type: "milestone",
    project_id: "project-123",
    created_by_id: "user-123",
  } as const

  it("renders AI Assessment tab in tabs list", async () => {
    renderWithProviders(
      <ViewBaseline
        baseline={mockBaseline}
        projectId="project-123"
        trigger={<button type="button">Open Baseline</button>}
      />,
    )

    // Open the modal
    const triggerButton = screen.getByText("Open Baseline")
    fireEvent.click(triggerButton)

    // Wait for modal to open and tabs to render
    await waitFor(() => {
      expect(screen.getByText(/AI Assessment/i)).toBeInTheDocument()
    })
  })

  it("renders AIChat component when AI Assessment tab is selected", async () => {
    renderWithProviders(
      <ViewBaseline
        baseline={mockBaseline}
        projectId="project-123"
        trigger={<button type="button">Open Baseline</button>}
      />,
    )

    // Open the modal
    const triggerButton = screen.getByText("Open Baseline")
    fireEvent.click(triggerButton)

    // Wait for modal to open
    await waitFor(() => {
      expect(screen.getByText(/View Baseline/i)).toBeInTheDocument()
    })

    // Click on AI Assessment tab
    const aiAssessmentTab = screen.getByText(/AI Assessment/i)
    fireEvent.click(aiAssessmentTab)

    // Wait for AIChat component to render
    await waitFor(() => {
      const aiChat = screen.getByTestId("ai-chat")
      expect(aiChat).toBeInTheDocument()
      expect(aiChat).toHaveAttribute("data-context-type", "baseline")
      expect(aiChat).toHaveAttribute("data-context-id", "baseline-123")
    })
  })

  it("resets to primary tab when modal closes", async () => {
    renderWithProviders(
      <ViewBaseline
        baseline={mockBaseline}
        projectId="project-123"
        trigger={<button type="button">Open Baseline</button>}
      />,
    )

    // Open the modal
    const triggerButton = screen.getByText("Open Baseline")
    fireEvent.click(triggerButton)

    // Wait for modal to open
    await waitFor(() => {
      expect(screen.getByText(/View Baseline/i)).toBeInTheDocument()
    })

    // Click on AI Assessment tab
    const aiAssessmentTab = screen.getByText(/AI Assessment/i)
    fireEvent.click(aiAssessmentTab)

    // Verify AIChat is shown
    await waitFor(() => {
      expect(screen.getByTestId("ai-chat")).toBeInTheDocument()
    })

    // Close the modal (click close button)
    const closeButtons = screen.getAllByRole("button")
    const closeButton = closeButtons.find(
      (btn) =>
        btn.getAttribute("aria-label")?.includes("close") ||
        btn.classList.toString().includes("close"),
    )
    if (closeButton) {
      fireEvent.click(closeButton)
    }

    // Wait for modal to close
    await waitFor(() => {
      expect(screen.queryByText(/View Baseline/i)).not.toBeInTheDocument()
    })

    // Re-open the modal
    fireEvent.click(triggerButton)

    // Verify it defaults back to "By WBE" tab (primary tab)
    await waitFor(() => {
      expect(screen.getByText(/View Baseline/i)).toBeInTheDocument()
      // The "By WBE" content should be visible by default
      expect(
        screen.getByTestId("baseline-cost-elements-by-wbe"),
      ).toBeInTheDocument()
    })
  })
})
