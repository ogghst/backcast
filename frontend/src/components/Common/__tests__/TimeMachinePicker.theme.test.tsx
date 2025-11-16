import { ChakraProvider } from "@chakra-ui/react"
import { render, screen } from "@testing-library/react"
import { describe, expect, it } from "vitest"
import { ColorModeProvider } from "@/components/ui/color-mode"
import { TimeMachineProvider } from "@/context/TimeMachineContext"
import { system } from "@/theme"
import TimeMachinePicker from "../TimeMachinePicker"

function renderWithProviders(
  ui: React.ReactNode,
  forcedTheme: "light" | "dark",
) {
  return render(
    <ChakraProvider value={system}>
      <ColorModeProvider forcedTheme={forcedTheme}>
        <TimeMachineProvider>{ui}</TimeMachineProvider>
      </ColorModeProvider>
    </ChakraProvider>,
  )
}

describe("TimeMachinePicker theming", () => {
  it("renders with light theme styles", () => {
    const { container } = renderWithProviders(<TimeMachinePicker />, "light")
    // ensure control is present
    expect(screen.getByTestId("time-machine-input")).toBeInTheDocument()
    // snapshot ensures style/class output corresponds to light theme
    expect(container.firstChild).toMatchSnapshot()
  })

  it("renders with dark theme styles", () => {
    const { container } = renderWithProviders(<TimeMachinePicker />, "dark")
    expect(screen.getByTestId("time-machine-input")).toBeInTheDocument()
    expect(container.firstChild).toMatchSnapshot()
  })
})
