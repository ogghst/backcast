// @vitest-environment jsdom
import { ChakraProvider } from "@chakra-ui/react"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { render, screen } from "@testing-library/react"
import { describe, expect, it, vi } from "vitest"
import { ColorModeProvider } from "@/components/ui/color-mode"
import { TimeMachineProvider } from "@/context/TimeMachineContext"
import { system } from "@/theme"
import TimeMachinePicker from "../TimeMachinePicker"

vi.mock("@tanstack/react-router", () => {
  return {
    useRouterState: () => ({ location: { pathname: "/projects/1" } }),
  }
})

function renderWithProviders(
  ui: React.ReactNode,
  forcedTheme: "light" | "dark",
) {
  const qc = new QueryClient()
  return render(
    <ChakraProvider value={system}>
      <ColorModeProvider forcedTheme={forcedTheme}>
        <QueryClientProvider client={qc}>
          <TimeMachineProvider>{ui}</TimeMachineProvider>
        </QueryClientProvider>
      </ColorModeProvider>
    </ChakraProvider>,
  )
}

describe("TimeMachinePicker theming", () => {
  it.skip("renders with light theme styles", () => {
    const { container } = renderWithProviders(<TimeMachinePicker />, "light")
    // ensure control is present
    expect(screen.getByTestId("time-machine-input")).toBeInTheDocument()
    // snapshot ensures style/class output corresponds to light theme
    expect(container.firstChild).toMatchSnapshot()
  })

  it.skip("renders with dark theme styles", () => {
    const { container } = renderWithProviders(<TimeMachinePicker />, "dark")
    expect(screen.getByTestId("time-machine-input")).toBeInTheDocument()
    expect(container.firstChild).toMatchSnapshot()
  })
})
