import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { AIAssistantModal } from "../AIAssistantModal";
import type { AIAssistantPublic } from "../../types";

const mockModels = [
  { id: "model-1", model_id: "gpt-4", display_name: "GPT-4", is_active: true, provider_name: "OpenAI" },
  { id: "model-2", model_id: "gpt-3.5-turbo", display_name: "GPT-3.5 Turbo", is_active: true, provider_name: "OpenAI" },
];

// A main-agent fixture. The Role (default_role) field only renders for main
// agents — specialists inherit the role — so tests asserting on Role must
// render a main agent rather than the create-mode specialist default.
const mainAssistantFixture: AIAssistantPublic = {
  id: "456",
  name: "Main Agent",
  description: "Main orchestrator",
  presentation_prompt: null,
  model_id: "model-1",
  system_prompt: "You are a planner",
  planner_prompt: null,
  supervisor_prompt: null,
  temperature: 0.7,
  max_tokens: 2048,
  recursion_limit: 25,
  max_supervisor_iterations: 5,
  default_role: "ai-manager",
  is_active: true,
  agent_type: "main",
  allowed_tools: ["list_projects"],
  delegation_config: null,
  structured_output_schema: null,
  created_at: "2026-03-07T00:00:00Z",
  updated_at: "2026-03-07T00:00:00Z",
};

describe("AIAssistantModal", () => {
  let queryClient: QueryClient;

  beforeEach(() => {
    vi.clearAllMocks();
    queryClient = new QueryClient({
      defaultOptions: {
        queries: { retry: false },
        mutations: { retry: false },
      },
    });
  });

  // ToolSelectorPanel (rendered by Tools/Delegation sections) calls useAITools,
  // which requires a QueryClientProvider. Collapsed sections now stay mounted
  // (keepMounted), so the provider must be present even before they are expanded.
  const renderWithProvider = (ui: React.ReactElement) =>
    render(ui, {
      wrapper: ({ children }) => (
        <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
      ),
    });

  it("should render modal with create mode title", async () => {
    renderWithProvider(
      <AIAssistantModal
        open={true}
        onCancel={vi.fn()}
        onOk={vi.fn()}
        confirmLoading={false}
        models={mockModels}
      />
    );

    expect(await screen.findByText("Create AI Assistant")).toBeInTheDocument();
  });

  it("should render modal with edit mode title when initialValues provided", async () => {
    const assistant: AIAssistantPublic = {
      id: "123",
      name: "Test Assistant",
      description: "Test description",
      presentation_prompt: null,
      model_id: "model-1",
      system_prompt: "You are helpful",
      planner_prompt: null,
      supervisor_prompt: null,
      temperature: 0.7,
      max_tokens: 2048,
      recursion_limit: 25,
      max_supervisor_iterations: 5,
      default_role: "ai-viewer",
      is_active: true,
      agent_type: "main",
      allowed_tools: ["list_projects"],
      delegation_config: null,
      structured_output_schema: null,
      created_at: "2026-03-07T00:00:00Z",
      updated_at: "2026-03-07T00:00:00Z",
    };

    renderWithProvider(
      <AIAssistantModal
        open={true}
        onCancel={vi.fn()}
        onOk={vi.fn()}
        confirmLoading={false}
        initialValues={assistant}
        models={mockModels}
      />
    );

    expect(await screen.findByText("Edit AI Assistant")).toBeInTheDocument();
  });

  it("should render all form fields", async () => {
    renderWithProvider(
      <AIAssistantModal
        open={true}
        onCancel={vi.fn()}
        onOk={vi.fn()}
        confirmLoading={false}
        models={mockModels}
      />
    );

    // Core fields always visible (create mode defaults to "specialist" agent type)
    expect(await screen.findByLabelText(/name/i)).toBeInTheDocument();
    expect(await screen.findByLabelText(/description/i)).toBeInTheDocument();
    expect(await screen.findByLabelText(/system prompt/i)).toBeInTheDocument();
    // Model field is only visible when agent_type === "main"
    // In create mode, agent_type defaults to "specialist", so Model is not rendered
  });

  it("should render default_role select field", async () => {
    renderWithProvider(
      <AIAssistantModal
        open={true}
        onCancel={vi.fn()}
        onOk={vi.fn()}
        confirmLoading={false}
        initialValues={mainAssistantFixture}
        models={mockModels}
      />
    );

    expect(await screen.findByLabelText("Role")).toBeInTheDocument();
  });

  it("should populate form with initialValues in edit mode", async () => {
    const assistant: AIAssistantPublic = {
      id: "123",
      name: "Test Assistant",
      description: "Test description",
      presentation_prompt: null,
      model_id: "model-1",
      system_prompt: "You are helpful",
      planner_prompt: null,
      supervisor_prompt: null,
      temperature: 0.7,
      max_tokens: 2048,
      recursion_limit: 25,
      max_supervisor_iterations: 5,
      default_role: "ai-manager",
      is_active: true,
      agent_type: "main",
      allowed_tools: ["list_projects"],
      delegation_config: null,
      structured_output_schema: null,
      created_at: "2026-03-07T00:00:00Z",
      updated_at: "2026-03-07T00:00:00Z",
    };

    renderWithProvider(
      <AIAssistantModal
        open={true}
        onCancel={vi.fn()}
        onOk={vi.fn()}
        confirmLoading={false}
        initialValues={assistant}
        models={mockModels}
      />
    );

    expect(await screen.findByLabelText(/name/i)).toHaveValue("Test Assistant");
    expect(await screen.findByLabelText(/description/i)).toHaveValue("Test description");
    expect(await screen.findByLabelText(/system prompt/i)).toHaveValue("You are helpful");
  });

  it("should show role options in the dropdown", async () => {
    const user = userEvent.setup();

    renderWithProvider(
      <AIAssistantModal
        open={true}
        onCancel={vi.fn()}
        onOk={vi.fn()}
        confirmLoading={false}
        initialValues={mainAssistantFixture}
        models={mockModels}
      />
    );

    const roleSelect = await screen.findByLabelText("Role");
    await user.click(roleSelect);

    // The selected role (AI Manager, from the fixture) also appears in the
    // selector's value display, so use findAllByText which tolerates that
    // duplicate; each role option must appear at least once in the dropdown.
    expect((await screen.findAllByText("AI Viewer")).length).toBeGreaterThanOrEqual(1);
    expect((await screen.findAllByText("AI Manager")).length).toBeGreaterThanOrEqual(1);
    expect((await screen.findAllByText("AI Admin")).length).toBeGreaterThanOrEqual(1);
  });

  it("should show presentation prompt field for specialist agents", async () => {
    renderWithProvider(
      <AIAssistantModal
        open={true}
        onCancel={vi.fn()}
        onOk={vi.fn()}
        confirmLoading={false}
        models={mockModels}
      />
    );

    // Create mode defaults to "specialist", so presentation prompt should be visible
    expect(await screen.findByLabelText(/presentation prompt/i)).toBeInTheDocument();
  });

  it("should not show presentation prompt field for main agents", async () => {
    const mainAssistant: AIAssistantPublic = {
      id: "456",
      name: "Main Agent",
      description: "Main orchestrator",
      presentation_prompt: null,
      model_id: "model-1",
      system_prompt: "You are a planner",
      planner_prompt: null,
      supervisor_prompt: null,
      temperature: 0.7,
      max_tokens: 2048,
      recursion_limit: 25,
      max_supervisor_iterations: 5,
      default_role: "ai-manager",
      is_active: true,
      agent_type: "main",
      allowed_tools: ["list_projects"],
      delegation_config: null,
      structured_output_schema: null,
      created_at: "2026-03-07T00:00:00Z",
      updated_at: "2026-03-07T00:00:00Z",
    };

    renderWithProvider(
      <AIAssistantModal
        open={true}
        onCancel={vi.fn()}
        onOk={vi.fn()}
        confirmLoading={false}
        initialValues={mainAssistant}
        models={mockModels}
      />
    );

    await waitFor(() => {
      expect(screen.queryByLabelText(/presentation prompt/i)).not.toBeInTheDocument();
    });
  });

});
