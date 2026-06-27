import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { App, ConfigProvider } from "antd";
import React from "react";

import { TemplateSelector } from "./TemplateSelector";
import type { FieldDefinitions } from "../types/fieldSpec";

// Mock the templates list hook so the selector renders deterministically.
const mockTemplates = [
  {
    custom_entity_template_id: "tpl-1",
    name: "Project Default",
    target_entity_type: "PROJECT",
    field_definitions: {
      priority: { type: "select", label: "Priority", options: ["low"] },
    } as FieldDefinitions,
  },
  {
    custom_entity_template_id: "tpl-2",
    name: "Project Extended",
    target_entity_type: "PROJECT",
    field_definitions: {
      notes: { type: "text", label: "Notes" },
    } as FieldDefinitions,
  },
];

vi.mock("../api/useCustomEntityTemplates", () => ({
  useCustomEntityTemplates: vi.fn(() => ({
    data: mockTemplates,
    isLoading: false,
  })),
}));

import { useCustomEntityTemplates } from "../api/useCustomEntityTemplates";

function renderWithTheme(ui: React.ReactElement) {
  return render(
    <App>
      <ConfigProvider>{ui}</ConfigProvider>
    </App>,
  );
}

describe("TemplateSelector", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders the list of templates as options", async () => {
    renderWithTheme(
      <TemplateSelector
        targetType="PROJECT"
        onChange={vi.fn()}
      />,
    );

    // Open the dropdown.
    fireEvent.mouseDown(
      screen.getByRole("combobox") as HTMLElement,
    );
    await waitFor(() => {
      expect(screen.getByText("Project Default")).toBeInTheDocument();
      expect(screen.getByText("Project Extended")).toBeInTheDocument();
    });
  });

  it("fires onChange with root id + field_definitions on selection", async () => {
    const onChange = vi.fn();
    renderWithTheme(
      <TemplateSelector targetType="PROJECT" onChange={onChange} />,
    );

    fireEvent.mouseDown(screen.getByRole("combobox") as HTMLElement);
    await waitFor(() => screen.getByText("Project Default"));
    fireEvent.click(screen.getByText("Project Default"));

    expect(onChange).toHaveBeenCalledTimes(1);
    const [rootId, fieldDefs] = onChange.mock.calls[0];
    expect(rootId).toBe("tpl-1");
    expect(fieldDefs).toMatchObject({
      priority: { type: "select", label: "Priority" },
    });
  });

  it("fires onChange(null, null) when cleared", async () => {
    const onChange = vi.fn();
    const { container } = renderWithTheme(
      <TemplateSelector
        targetType="PROJECT"
        value="tpl-1"
        onChange={onChange}
      />,
    );

    // antd's clear is triggered by mousedown on .ant-select-clear (not click).
    const clear = container.querySelector(".ant-select-clear");
    expect(clear).not.toBeNull();
    fireEvent.mouseDown(clear as HTMLElement);

    await waitFor(() => {
      expect(onChange).toHaveBeenCalledWith(null, null);
    });
  });

  it("forwards the targetType filter to the query hook", () => {
    renderWithTheme(
      <TemplateSelector targetType="WORK_PACKAGE" onChange={vi.fn()} />,
    );
    const mockFn = useCustomEntityTemplates as unknown as ReturnType<
      typeof vi.fn
    >;
    expect(mockFn).toHaveBeenCalledWith(
      expect.objectContaining({ target_entity_type: "WORK_PACKAGE" }),
    );
  });
});
