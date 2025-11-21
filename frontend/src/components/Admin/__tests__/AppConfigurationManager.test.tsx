// @vitest-environment jsdom
import { ChakraProvider } from "@chakra-ui/react"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { fireEvent, render, screen, waitFor } from "@testing-library/react"
import type React from "react"
import { beforeEach, describe, expect, it, vi } from "vitest"
import * as client from "@/client"
import { ColorModeProvider } from "@/components/ui/color-mode"
import { system } from "../../../theme"
import AppConfigurationManager from "../AppConfigurationManager"

vi.mock("@/client", () => ({
  AdminService: {
    listAppConfigurations: vi.fn(),
    updateAppConfiguration: vi.fn(),
  },
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
        <QueryClientProvider client={qc}>{ui}</QueryClientProvider>
      </ColorModeProvider>
    </ChakraProvider>,
  )
}

describe("AppConfigurationManager", () => {
  beforeEach(() => {
    vi.resetAllMocks()
    vi.mocked(client.AdminService.listAppConfigurations).mockResolvedValue({
      data: [
        {
          config_id: "config-1",
          config_key: "ai_default_openai_base_url",
          config_value: "https://api.openai.com/v1",
          description: "Default OpenAI API base URL",
          is_active: true,
          created_at: "2025-01-01T00:00:00Z",
          updated_at: "2025-01-01T00:00:00Z",
        },
        {
          config_id: "config-2",
          config_key: "ai_default_openai_api_key_encrypted",
          config_value: "encrypted_key_value",
          description: "Default OpenAI API key (encrypted)",
          is_active: true,
          created_at: "2025-01-01T00:00:00Z",
          updated_at: "2025-01-01T00:00:00Z",
        },
      ],
      count: 2,
    } as any)
  })

  it("displays list of default AI configurations", async () => {
    renderWithProviders(<AppConfigurationManager />)

    // Wait for loading to complete and data to render
    await waitFor(
      () => {
        expect(
          screen.queryByText(/Loading configurations/i),
        ).not.toBeInTheDocument()
        expect(screen.getByText(/AI Configuration/i)).toBeInTheDocument()
      },
      { timeout: 3000 },
    )

    // Verify table headers are present
    expect(screen.getAllByText(/Key/i).length).toBeGreaterThan(0)
    expect(screen.getAllByText(/Value/i).length).toBeGreaterThan(0)

    // Verify configurations are displayed - check for the label instead of key
    expect(screen.getByText(/OpenAI Base URL/i)).toBeInTheDocument()

    // Verify service was called
    expect(client.AdminService.listAppConfigurations).toHaveBeenCalled()
  })

  it("allows editing a configuration", async () => {
    vi.mocked(client.AdminService.updateAppConfiguration).mockResolvedValue({
      config_id: "config-1",
      config_key: "ai_default_openai_base_url",
      config_value: "https://api.openai.com/v2",
      description: "Updated description",
      is_active: true,
      created_at: "2025-01-01T00:00:00Z",
      updated_at: "2025-01-01T00:00:00Z",
    } as any)

    renderWithProviders(<AppConfigurationManager />)

    // Wait for loading to complete
    await waitFor(
      () => {
        expect(
          screen.queryByText(/Loading configurations/i),
        ).not.toBeInTheDocument()
      },
      { timeout: 3000 },
    )

    // Verify edit buttons are present
    const editButtons = screen.getAllByRole("button", { name: /Edit/i })
    expect(editButtons.length).toBeGreaterThan(0)

    // Click first edit button
    fireEvent.click(editButtons[0])

    // Wait for dialog to open
    await waitFor(() => {
      expect(screen.getByText(/Edit Configuration/i)).toBeInTheDocument()
    })
  })

  it("validates base URL format", async () => {
    renderWithProviders(<AppConfigurationManager />)

    // Wait for loading to complete
    await waitFor(
      () => {
        expect(
          screen.queryByText(/Loading configurations/i),
        ).not.toBeInTheDocument()
      },
      { timeout: 3000 },
    )

    // Find and click edit button for base URL config
    const editButtons = screen.getAllByRole("button", { name: /Edit/i })
    fireEvent.click(editButtons[0])

    // Wait for dialog to open
    await waitFor(() => {
      expect(screen.getByText(/Edit Configuration/i)).toBeInTheDocument()
    })

    // Find base URL input and enter invalid URL
    // The label is "OpenAI Base URL" based on getConfigLabel
    const urlInput = screen.getByLabelText(/OpenAI Base URL/i)
    fireEvent.change(urlInput, { target: { value: "invalid-url" } })
    fireEvent.blur(urlInput)

    // Verify validation error appears
    await waitFor(() => {
      expect(screen.getByText(/Invalid URL format/i)).toBeInTheDocument()
    })
  })

  it("allows updating configuration value", async () => {
    vi.mocked(client.AdminService.updateAppConfiguration).mockResolvedValue({
      config_id: "config-1",
      config_key: "ai_default_openai_base_url",
      config_value: "https://api.openai.com/v2",
      description: "Updated description",
      is_active: true,
      created_at: "2025-01-01T00:00:00Z",
      updated_at: "2025-01-01T00:00:00Z",
    } as any)

    renderWithProviders(<AppConfigurationManager />)

    // Wait for loading to complete
    await waitFor(
      () => {
        expect(
          screen.queryByText(/Loading configurations/i),
        ).not.toBeInTheDocument()
      },
      { timeout: 3000 },
    )

    // Click edit button
    const editButtons = screen.getAllByRole("button", { name: /Edit/i })
    fireEvent.click(editButtons[0])

    // Wait for dialog to open
    await waitFor(() => {
      expect(screen.getByText(/Edit Configuration/i)).toBeInTheDocument()
    })

    // Update value - find by label "OpenAI Base URL"
    const valueInput = screen.getByLabelText(/OpenAI Base URL/i)
    fireEvent.change(valueInput, {
      target: { value: "https://api.openai.com/v2" },
    })

    // Submit form
    const saveButton = screen.getByRole("button", { name: /Save/i })
    fireEvent.click(saveButton)

    // Verify update was called
    await waitFor(() => {
      expect(client.AdminService.updateAppConfiguration).toHaveBeenCalled()
    })
  })
})
