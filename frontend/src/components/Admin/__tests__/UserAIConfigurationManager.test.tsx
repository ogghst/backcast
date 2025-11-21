// @vitest-environment jsdom
import { ChakraProvider } from "@chakra-ui/react"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { fireEvent, render, screen, waitFor } from "@testing-library/react"
import type React from "react"
import { beforeEach, describe, expect, it, vi } from "vitest"
import * as client from "@/client"
import { ColorModeProvider } from "@/components/ui/color-mode"
import { system } from "../../../theme"
import UserAIConfigurationManager from "../UserAIConfigurationManager"

vi.mock("@/client", () => ({
  UsersService: {
    readUsers: vi.fn(),
    updateUser: vi.fn(),
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

describe("UserAIConfigurationManager", () => {
  beforeEach(() => {
    vi.resetAllMocks()
    vi.mocked(client.UsersService.readUsers).mockResolvedValue({
      data: [
        {
          id: "user-1",
          email: "user1@example.com",
          full_name: "User One",
          role: "controller",
          is_active: true,
          openai_base_url: null,
          openai_api_key_encrypted: null,
        },
        {
          id: "user-2",
          email: "user2@example.com",
          full_name: "User Two",
          role: "admin",
          is_active: true,
          openai_base_url: "https://api.openai.com/v1",
          openai_api_key_encrypted: "encrypted_key",
        },
      ],
      count: 2,
    } as any)
  })

  it("displays table of users with AI config status", async () => {
    renderWithProviders(<UserAIConfigurationManager />)

    // Wait for loading to complete and data to render
    await waitFor(
      () => {
        expect(screen.queryByText(/Loading users/i)).not.toBeInTheDocument()
        expect(screen.getByText(/User AI Configuration/i)).toBeInTheDocument()
      },
      { timeout: 3000 },
    )

    // Verify table headers are present
    expect(screen.getAllByText(/User/i).length).toBeGreaterThan(0)
    expect(screen.getAllByText(/Email/i).length).toBeGreaterThan(0)
    expect(screen.getByText(/AI Config Status/i)).toBeInTheDocument()

    // Verify users are displayed
    expect(screen.getByText(/User One/i)).toBeInTheDocument()
    expect(screen.getByText(/User Two/i)).toBeInTheDocument()

    // Verify service was called
    expect(client.UsersService.readUsers).toHaveBeenCalled()
  })

  it("shows configured status for users with AI config", async () => {
    renderWithProviders(<UserAIConfigurationManager />)

    // Wait for loading to complete
    await waitFor(
      () => {
        expect(screen.queryByText(/Loading users/i)).not.toBeInTheDocument()
      },
      { timeout: 3000 },
    )

    // Verify configured badge is shown for user-2
    const configuredBadges = screen.getAllByText(/Configured/i)
    expect(configuredBadges.length).toBeGreaterThan(0)
  })

  it("allows editing a user's AI configuration", async () => {
    vi.mocked(client.UsersService.updateUser).mockResolvedValue({
      id: "user-1",
      email: "user1@example.com",
      full_name: "User One",
      role: "controller",
      is_active: true,
      openai_base_url: "https://api.openai.com/v1",
      openai_api_key_encrypted: "encrypted_key",
    } as any)

    renderWithProviders(<UserAIConfigurationManager />)

    // Wait for loading to complete
    await waitFor(
      () => {
        expect(screen.queryByText(/Loading users/i)).not.toBeInTheDocument()
      },
      { timeout: 3000 },
    )

    // Find and click edit button for first user
    const editButtons = screen.getAllByRole("button", { name: /Edit/i })
    expect(editButtons.length).toBeGreaterThan(0)

    // Click first edit button
    fireEvent.click(editButtons[0])

    // Wait for dialog to open
    await waitFor(() => {
      expect(screen.getByText(/Edit AI Configuration/i)).toBeInTheDocument()
    })
  })

  it("validates base URL format in edit dialog", async () => {
    renderWithProviders(<UserAIConfigurationManager />)

    // Wait for loading to complete
    await waitFor(
      () => {
        expect(screen.queryByText(/Loading users/i)).not.toBeInTheDocument()
      },
      { timeout: 3000 },
    )

    // Find and click edit button
    const editButtons = screen.getAllByRole("button", { name: /Edit/i })
    fireEvent.click(editButtons[0])

    // Wait for dialog to open
    await waitFor(() => {
      expect(screen.getByText(/Edit AI Configuration/i)).toBeInTheDocument()
    })

    // Find base URL input and enter invalid URL
    const urlInput = screen.getByLabelText(/OpenAI Base URL/i)
    fireEvent.change(urlInput, { target: { value: "invalid-url" } })
    fireEvent.blur(urlInput)

    // Verify validation error appears
    await waitFor(() => {
      expect(screen.getByText(/Invalid URL format/i)).toBeInTheDocument()
    })
  })

  it("allows updating user AI configuration", async () => {
    vi.mocked(client.UsersService.updateUser).mockResolvedValue({
      id: "user-1",
      email: "user1@example.com",
      full_name: "User One",
      role: "controller",
      is_active: true,
      openai_base_url: "https://api.openai.com/v2",
      openai_api_key_encrypted: "encrypted_key",
    } as any)

    renderWithProviders(<UserAIConfigurationManager />)

    // Wait for loading to complete
    await waitFor(
      () => {
        expect(screen.queryByText(/Loading users/i)).not.toBeInTheDocument()
      },
      { timeout: 3000 },
    )

    // Click edit button
    const editButtons = screen.getAllByRole("button", { name: /Edit/i })
    fireEvent.click(editButtons[0])

    // Wait for dialog to open
    await waitFor(() => {
      expect(screen.getByText(/Edit AI Configuration/i)).toBeInTheDocument()
    })

    // Update base URL
    const urlInput = screen.getByLabelText(/OpenAI Base URL/i)
    fireEvent.change(urlInput, {
      target: { value: "https://api.openai.com/v2" },
    })

    // Update API key
    const apiKeyInput = screen.getByLabelText(/OpenAI API Key/i)
    fireEvent.change(apiKeyInput, { target: { value: "sk-test1234567890" } })

    // Submit form
    const saveButton = screen.getByRole("button", { name: /Save/i })
    fireEvent.click(saveButton)

    // Verify update was called
    await waitFor(() => {
      expect(client.UsersService.updateUser).toHaveBeenCalled()
    })
  })
})
