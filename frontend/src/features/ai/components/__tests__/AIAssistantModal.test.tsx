import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { AIAssistantModal } from "../AIAssistantModal";
import type { AIAssistantPublic } from "../../types";

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
      default_role: "ai-viewer",
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

  it("should render default_role select field", async () => {
    render(
      <AIAssistantModal
        open={true}
        onCancel={vi.fn()}
        onOk={vi.fn()}
        confirmLoading={false}
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
      model_id: "model-1",
      system_prompt: "You are helpful",
      temperature: 0.7,
      max_tokens: 2048,
      allowed_tools: ["list_projects"],
      default_role: "ai-manager",
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
  });

  it("should show role options in the dropdown", async () => {
    const user = userEvent.setup();

    render(
      <AIAssistantModal
        open={true}
        onCancel={vi.fn()}
        onOk={vi.fn()}
        confirmLoading={false}
        models={mockModels}
      />
    );

    const roleSelect = await screen.findByLabelText("Role");
    await user.click(roleSelect);

    expect(await screen.findByText("AI Viewer")).toBeInTheDocument();
    expect(await screen.findByText("AI Manager")).toBeInTheDocument();
    expect(await screen.findByText("AI Admin")).toBeInTheDocument();
  });

});
