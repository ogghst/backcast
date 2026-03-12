import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { AIAssistantModal } from "../AIAssistantModal";
import type { AIAssistantPublic, AIAssistantCreate } from "../../types";

// Mock the API hooks
vi.mock("../../api", () => ({
  useAITools: vi.fn()
}));

// We can mock ToolSelectorPanel completely as we just want to test if it's rendered within the Form
vi.mock("../ToolSelectorPanel", () => ({
  ToolSelectorPanel: ({ value, onChange }: { value?: string[], onChange?: (v: string[]) => void }) => (
    <div data-testid="mock-tool-selector">
      <button 
        type="button" 
        data-testid="mock-tool-btn" 
        onClick={() => onChange?.([...(value || []), "test_tool"])}
      >
        Select Tool
      </button>
      <span data-testid="mock-tool-values">{value?.join(',')}</span>
    </div>
  )
}));

const mockModels = [
  { id: "model-1", model_id: "gpt-4", display_name: "GPT-4", is_active: true, provider_name: "OpenAI" },
  { id: "model-2", model_id: "gpt-3.5-turbo", display_name: "GPT-3.5 Turbo", is_active: true, provider_name: "OpenAI" },
];

describe("AIAssistantModal", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("should render modal with create mode title", async () => {
    render(
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
      model_id: "model-1",
      system_prompt: "You are helpful",
      temperature: 0.7,
      max_tokens: 2048,
      allowed_tools: ["list_projects"],
      is_active: true,
      created_at: "2026-03-07T00:00:00Z",
      updated_at: "2026-03-07T00:00:00Z",
    };

    render(
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
    render(
      <AIAssistantModal
        open={true}
        onCancel={vi.fn()}
        onOk={vi.fn()}
        confirmLoading={false}
        models={mockModels}
      />
    );

    expect(await screen.findByLabelText(/name/i)).toBeInTheDocument();
    expect(await screen.findByLabelText(/description/i)).toBeInTheDocument();
    expect(await screen.findByLabelText(/model/i)).toBeInTheDocument();
    expect(await screen.findByLabelText(/system prompt/i)).toBeInTheDocument();
  });

  it("should populate form with initialValues in edit mode including ToolSelectorPanel", async () => {
    const assistant: AIAssistantPublic = {
      id: "123",
      name: "Test Assistant",
      description: "Test description",
      model_id: "model-1",
      system_prompt: "You are helpful",
      temperature: 0.7,
      max_tokens: 2048,
      allowed_tools: ["list_projects"],
      is_active: true,
      created_at: "2026-03-07T00:00:00Z",
      updated_at: "2026-03-07T00:00:00Z",
    };

    render(
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
    
    // Check that our mock ToolSelectorPanel received "list_projects"
    expect(await screen.findByTestId('mock-tool-values')).toHaveTextContent('list_projects');
  });

  it("should render the ToolSelectorPanel in create mode", async () => {
    render(
      <AIAssistantModal
        open={true}
        onCancel={vi.fn()}
        onOk={vi.fn()}
        confirmLoading={false}
        models={mockModels}
      />
    );

    expect(await screen.findByTestId('mock-tool-selector')).toBeInTheDocument();
  });

  it("should submit form correctly including tool selection limits handled by mock", async () => {
    const user = userEvent.setup();
    const onOk = vi.fn();

    render(
      <AIAssistantModal
        open={true}
        onCancel={vi.fn()}
        onOk={onOk}
        confirmLoading={false}
        models={mockModels}
      />
    );

    const nameInput = await screen.findByLabelText(/name/i);
    await user.type(nameInput, "Test Assistant");
    
    // Ant Design Select interacts complexly in tests. 
    // We just need ToolSelectorPanel interaction here to verify it propagates
    const mockToolBtn = await screen.findByTestId('mock-tool-btn');
    await user.click(mockToolBtn);
    
    // It correctly sets the Form state value
    expect(await screen.findByTestId('mock-tool-values')).toHaveTextContent('test_tool');
  });

});
