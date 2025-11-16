import { vi } from "vitest"

vi.mock("@/components/ui/toaster", () => {
  return {
    toaster: {
      create: () => {},
    },
    Toaster: () => null,
  }
})

// Mock next-themes matchMedia usage
vi.mock("next-themes", () => {
  let currentTheme: "light" | "dark" = "light"
  return {
    ThemeProvider: ({ children, forcedTheme, defaultTheme }: any) => {
      if (forcedTheme) currentTheme = forcedTheme
      else if (defaultTheme) currentTheme = defaultTheme
      return children
    },
    useTheme: () => ({
      resolvedTheme: currentTheme,
      setTheme: (t: "light" | "dark") => {
        currentTheme = t
      },
    }),
  }
})

// Mock UsersService for TimeMachineProvider
vi.mock("@/client", async (importOriginal) => {
  const actual = await importOriginal<any>()
  const today = new Date().toISOString().slice(0, 10)
  return {
    ...actual,
    UsersService: {
      ...(actual.UsersService ?? {}),
      readTimeMachinePreference: vi
        .fn()
        .mockResolvedValue({ time_machine_date: today }),
      updateTimeMachinePreference: vi
        .fn()
        .mockResolvedValue({ time_machine_date: today }),
    },
  }
})
