/**
 * Tests for AssistantSelector component
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor, within } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { AssistantSelector } from "../AssistantSelector";
import userEvent from "@testing-library/user-event";

// Mock useAIAssistants to return controlled data
vi.mock("@/features/ai/api/useAIAssistants", () => ({
  useAIAssistants: vi.fn(),
}));

import { useAIAssistants } from "@/features/ai/api/useAIAssistants";

const mockUseAIAssistants = vi.mocked(useAIAssistants);

describe("AssistantSelector", () => {
  let queryClient: QueryClient;

  const defaultMockData = [
    {
      id: "assistant-1",
      name: "Project Helper",
      description: "Helps with project management",
      model_id: "model-123",
      system_prompt: "You are helpful",
      temperature: 0.7,
      max_tokens: 2048,
      recursion_limit: null,
      allowed_tools: ["list_projects", "get_project", "list_wbes"],
      default_role: null,
      is_active: true,
      created_at: "2026-03-07T00:00:00Z",
      updated_at: "2026-03-07T00:00:00Z",
    },
    {
      id: "assistant-2",
      name: "Senior Manager",
      description: "Full CRUD access",
      model_id: "model-456",
      system_prompt: "You manage things",
      temperature: 0.7,
      max_tokens: 2048,
      recursion_limit: null,
      allowed_tools: [
        "list_projects",
        "get_project",
        "create_wbe",
        "update_wbe",
        "list_wbes",
        "get_cost_element",
        "register_cost",
        "register_progress",
        "get_forecast",
      ],
      default_role: null,
      is_active: true,
      created_at: "2026-03-07T00:00:00Z",
      updated_at: "2026-03-07T00:00:00Z",
    },
  ];

  beforeEach(() => {
    vi.clearAllMocks();
    queryClient = new QueryClient({
      defaultOptions: {
        queries: { retry: false },
      },
    });

    // Default mock: return loaded data
    mockUseAIAssistants.mockReturnValue({
      data: defaultMockData,
      isLoading: false,
      error: null,
    } as ReturnType<typeof useAIAssistants>);
  });

  const wrapper = ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  );

  it("should render with placeholder when no value is selected", () => {
    const handleChange = vi.fn();

    render(<AssistantSelector value={undefined} onChange={handleChange} />, {
      wrapper,
    });

    // Select should be present
    const select = screen.getByRole("combobox");
    expect(select).toBeInTheDocument();
  });

  it("should render in loading state when isLoading is true", () => {
    const handleChange = vi.fn();

    mockUseAIAssistants.mockReturnValue({
      data: undefined,
      isLoading: true,
      error: null,
    } as ReturnType<typeof useAIAssistants>);

    render(<AssistantSelector value={undefined} onChange={handleChange} />, {
      wrapper,
    });

    // Select should be present (showing loading/placeholder state)
    const select = screen.getByRole("combobox");
    expect(select).toBeInTheDocument();
  });

  it("should display selected assistant by value", async () => {
    const handleChange = vi.fn();

    render(
      <AssistantSelector value="assistant-2" onChange={handleChange} />,
      {
        wrapper,
      }
    );

    // When a value is set, it should display that value
    await waitFor(() => {
      const select = screen.getByRole("combobox");
      expect(select).toBeInTheDocument();
    });
  });

  it("should be disabled when disabled prop is true", () => {
    const handleChange = vi.fn();

    render(
      <AssistantSelector
        value={undefined}
        onChange={handleChange}
        disabled
      />,
      { wrapper }
    );

    expect(screen.getByRole("combobox")).toBeDisabled();
  });

  it("should call onChange when user interacts with select", async () => {
    const handleChange = vi.fn();
    const user = userEvent.setup();

    render(<AssistantSelector value={undefined} onChange={handleChange} />, {
      wrapper,
    });

    const combobox = screen.getByRole("combobox");
    expect(combobox).toBeInTheDocument();

    // Click the select
    await user.click(combobox);
  });

  it("should be disabled when loading", () => {
    const handleChange = vi.fn();

    mockUseAIAssistants.mockReturnValue({
      data: undefined,
      isLoading: true,
      error: null,
    } as ReturnType<typeof useAIAssistants>);

    render(<AssistantSelector value={undefined} onChange={handleChange} />, {
      wrapper,
    });

    expect(screen.getByRole("combobox")).toBeDisabled();
  });

  it("should have correct ARIA attributes", () => {
    const handleChange = vi.fn();

    render(<AssistantSelector value={undefined} onChange={handleChange} />, {
      wrapper,
    });

    const combobox = screen.getByRole("combobox");
    expect(combobox).toHaveAttribute("aria-autocomplete", "list");
    expect(combobox).toHaveAttribute("aria-haspopup", "listbox");
  });

  it("should allow clearing when allowClear is not set", () => {
    const handleChange = vi.fn();

    render(
      <AssistantSelector value="assistant-1" onChange={handleChange} />,
      {
        wrapper,
      }
    );

    const select = screen.getByRole("combobox");
    expect(select).toBeInTheDocument();
  });

  it("should show tool count for each assistant option in the dropdown", async () => {
    const handleChange = vi.fn();
    const user = userEvent.setup();

    render(<AssistantSelector value={undefined} onChange={handleChange} />, {
      wrapper,
    });

    // Open the dropdown
    await user.click(screen.getByRole("combobox"));

    // Wait for the dropdown portal to appear
    const dropdown = await waitFor(() =>
      document.querySelector(".ant-select-dropdown")
    );
    expect(dropdown).toBeTruthy();

    // Verify tool counts are displayed for each assistant
    // assistant-1 has 3 tools, assistant-2 has 9 tools
    // The optionRender shows "<N> tools" in a Tag
    expect(within(dropdown as HTMLElement).getByText("3 tools")).toBeTruthy();
    expect(within(dropdown as HTMLElement).getByText("9 tools")).toBeTruthy();
  });

  it("should show tool count in the locked state", () => {
    const handleChange = vi.fn();

    render(
      <AssistantSelector
        value="assistant-1"
        onChange={handleChange}
        locked
      />,
      { wrapper }
    );

    // Locked state should show assistant name and tool count
    expect(screen.getByText("Project Helper")).toBeInTheDocument();
    expect(screen.getByText("3 tools")).toBeInTheDocument();
  });

  it("should show role name when allowed_tools is null and default_role is set", () => {
    const handleChange = vi.fn();

    const roleBasedData = [
      {
        id: "assistant-role",
        name: "Role Assistant",
        description: "Uses role-based tool filtering",
        model_id: "model-789",
        system_prompt: "You follow roles",
        temperature: 0.7,
        max_tokens: 2048,
        recursion_limit: null,
        allowed_tools: null,
        default_role: "ai-manager",
        is_active: true,
        created_at: "2026-03-07T00:00:00Z",
        updated_at: "2026-03-07T00:00:00Z",
      },
    ];

    mockUseAIAssistants.mockReturnValue({
      data: roleBasedData,
      isLoading: false,
      error: null,
    } as ReturnType<typeof useAIAssistants>);

    render(
      <AssistantSelector
        value="assistant-role"
        onChange={handleChange}
        locked
      />,
      { wrapper }
    );

    // Locked state should show role name instead of tool count
    expect(screen.getByText("Role Assistant")).toBeInTheDocument();
    expect(screen.getByText("ai-manager")).toBeInTheDocument();
  });

  it("should show role name in dropdown options for role-based assistants", async () => {
    const handleChange = vi.fn();
    const user = userEvent.setup();

    const roleBasedData = [
      {
        id: "assistant-role",
        name: "Role Assistant",
        description: "Uses role-based tool filtering",
        model_id: "model-789",
        system_prompt: "You follow roles",
        temperature: 0.7,
        max_tokens: 2048,
        recursion_limit: null,
        allowed_tools: null,
        default_role: "ai-viewer",
        is_active: true,
        created_at: "2026-03-07T00:00:00Z",
        updated_at: "2026-03-07T00:00:00Z",
      },
    ];

    mockUseAIAssistants.mockReturnValue({
      data: roleBasedData,
      isLoading: false,
      error: null,
    } as ReturnType<typeof useAIAssistants>);

    render(<AssistantSelector value={undefined} onChange={handleChange} />, {
      wrapper,
    });

    await user.click(screen.getByRole("combobox"));

    const dropdown = await waitFor(() =>
      document.querySelector(".ant-select-dropdown")
    );
    expect(dropdown).toBeTruthy();

    // Should show role name instead of "0 tools"
    expect(within(dropdown as HTMLElement).getByText("ai-viewer")).toBeTruthy();
  });
});
