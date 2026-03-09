import { describe, it, expect, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { AIAssistantModal } from "../AIAssistantModal";
import type { AIAssistantPublic, AIAssistantCreate } from "../../types";

const mockModels = [
  { id: "model-1", model_id: "gpt-4", display_name: "GPT-4", is_active: true },
  { id: "model-2", model_id: "gpt-3.5-turbo", display_name: "GPT-3.5 Turbo", is_active: true },
];

describe("AIAssistantModal", () => {
  it("should render modal with create mode title", () => {
    render(
      <AIAssistantModal
        open={true}
        onCancel={vi.fn()}
        onOk={vi.fn()}
        confirmLoading={false}
        models={mockModels}
      />
    );

    expect(screen.getByText("Create AI Assistant")).toBeInTheDocument();
  });

  it("should render modal with edit mode title when initialValues provided", () => {
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

    expect(screen.getByText("Edit AI Assistant")).toBeInTheDocument();
  });

  it("should render all form fields", () => {
    render(
      <AIAssistantModal
        open={true}
        onCancel={vi.fn()}
        onOk={vi.fn()}
        confirmLoading={false}
        models={mockModels}
      />
    );

    expect(screen.getByLabelText(/name/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/description/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/model/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/system prompt/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/temperature/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/max tokens/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/active/i)).toBeInTheDocument();
  });

  it("should populate form with initialValues in edit mode", () => {
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

    expect(screen.getByLabelText(/name/i)).toHaveValue("Test Assistant");
    expect(screen.getByLabelText(/description/i)).toHaveValue("Test description");
    expect(screen.getByLabelText(/system prompt/i)).toHaveValue("You are helpful");
  });

  it("should show all tools in tool checkboxes", () => {
    render(
      <AIAssistantModal
        open={true}
        onCancel={vi.fn()}
        onOk={vi.fn()}
        confirmLoading={false}
        models={mockModels}
      />
    );

    // Check that some expected tools are shown
    expect(screen.getByText(/list projects/i)).toBeInTheDocument();
    expect(screen.getByText(/get project/i)).toBeInTheDocument();
    expect(screen.getByText(/create wbe/i)).toBeInTheDocument();
  });

  it("should call onOk with form values when submitted", async () => {
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

    await user.type(screen.getByLabelText(/name/i), "Test Assistant");
    await user.click(screen.getByRole("button", { name: /create/i }));

    await waitFor(() => {
      expect(onOk).toHaveBeenCalled();
      const submittedData = onOk.mock.calls[0][0] as AIAssistantCreate;
      expect(submittedData.name).toBe("Test Assistant");
    });
  });

  it("should validate required fields", async () => {
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

    await user.click(screen.getByRole("button", { name: /create/i }));

    // Should show validation error for required name field
    await waitFor(() => {
      expect(screen.getByText(/please enter name/i)).toBeInTheDocument();
    });
    expect(onOk).not.toHaveBeenCalled();
  });

  it("should validate temperature range (0-2)", async () => {
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

    const temperatureInput = screen.getByLabelText(/temperature/i);
    await user.clear(temperatureInput);
    await user.type(temperatureInput, "2.5");

    await user.click(screen.getByRole("button", { name: /create/i }));

    await waitFor(() => {
      expect(screen.getByText(/temperature must be between 0 and 2/i)).toBeInTheDocument();
    });
  });

  it("should validate max_tokens positive integer", async () => {
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

    const maxTokensInput = screen.getByLabelText(/max tokens/i);
    await user.clear(maxTokensInput);
    await user.type(maxTokensInput, "-1");

    await user.click(screen.getByRole("button", { name: /create/i }));

    await waitFor(() => {
      expect(screen.getByText(/max tokens must be positive/i)).toBeInTheDocument();
    });
  });

  it("should show disabled state for unimplemented tools", () => {
    render(
      <AIAssistantModal
        open={true}
        onCancel={vi.fn()}
        onOk={vi.fn()}
        confirmLoading={false}
        models={mockModels}
      />
    );

    // The "update_wbe" tool is marked as not implemented in TOOL_REGISTRY
    const updateWBECheckbox = screen.getByLabelText(/update wbe/i);
    expect(updateWBECheckbox).toBeDisabled();
  });
});
