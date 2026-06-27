import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { App, ConfigProvider, Form } from "antd";
import React from "react";

import {
  CustomFieldsRenderer,
} from "./CustomFieldsRenderer";
import type { FieldDefinitions } from "../types/fieldSpec";

// Mock the user loader so the reference widget renders without a backend.
vi.mock("@/features/users/api/useUsers", () => ({
  useUsers: vi.fn(() => ({ data: [], isLoading: false })),
}));

function renderWithTheme(ui: React.ReactElement) {
  return render(
    <App>
      <ConfigProvider>{ui}</ConfigProvider>
    </App>,
  );
}

describe("CustomFieldsRenderer", () => {
  it("renders a widget per field definition inside a form", async () => {
    const defs: FieldDefinitions = {
      notes: { type: "text", label: "Notes", max_length: 200 },
      priority: {
        type: "select",
        label: "Priority",
        options: ["low", "high"],
      },
      due: { type: "date", label: "Due Date" },
      active: { type: "boolean", label: "Active" },
    };

    renderWithTheme(
      <Form layout="vertical">
        <CustomFieldsRenderer fieldDefinitions={defs} />
      </Form>,
    );

    // Labels render for every field.
    for (const label of ["Notes", "Priority", "Due Date", "Active"]) {
      expect(screen.getByText(label)).toBeInTheDocument();
    }
    // Select options only mount when the dropdown is open; open it.
    const selects = screen.getAllByRole("combobox");
    fireEvent.mouseDown(selects[0]); // first Select = priority
    await waitFor(() => {
      expect(screen.getByTitle("low")).toBeInTheDocument();
      expect(screen.getByTitle("high")).toBeInTheDocument();
    });
  });

  it("marks required fields with the antd required rule (asterisk)", () => {
    const defs: FieldDefinitions = {
      owner: { type: "text", label: "Owner", required: true },
      opt: { type: "text", label: "Optional" },
    };

    renderWithTheme(
      <Form layout="vertical">
        <CustomFieldsRenderer fieldDefinitions={defs} />
      </Form>,
    );

    // antd renders the required asterisk as a <span class="ant-form-item-required">.
    const requiredMarks = screen.getAllByText("Owner").flatMap((el) =>
      el.closest(".ant-form-item")?.querySelectorAll(
        ".ant-form-item-required",
      ) ?? [],
    );
    expect(requiredMarks.length).toBeGreaterThan(0);
    // Optional field has no required mark.
    const optItem = screen.getByText("Optional").closest(".ant-form-item");
    expect(optItem?.querySelector(".ant-form-item-required")).toBeNull();
  });

  it("renders read-only label/value rows (no inputs) when readOnly", () => {
    const defs: FieldDefinitions = {
      notes: { type: "text", label: "Notes" },
      active: { type: "boolean", label: "Active" },
    };
    const values = { notes: "hello", active: true };

    renderWithTheme(
      <CustomFieldsRenderer
        fieldDefinitions={defs}
        readOnly
        values={values}
      />,
    );

    // Read-only value formatting: boolean true → "Yes".
    expect(screen.getByText("Yes")).toBeInTheDocument();
    expect(screen.getByText("hello")).toBeInTheDocument();
    // No text inputs rendered.
    expect(document.querySelector("input[type='text']")).toBeNull();
  });

  it("renders a disabled placeholder input for formula fields", () => {
    const defs: FieldDefinitions = {
      score: { type: "formula", label: "Score" },
    };

    const { container } = renderWithTheme(
      <Form layout="vertical">
        <CustomFieldsRenderer fieldDefinitions={defs} />
      </Form>,
    );

    const formulaInput = container.querySelector(
      "input[placeholder='computed']",
    );
    expect(formulaInput).not.toBeNull();
    expect(formulaInput?.hasAttribute("disabled")).toBe(true);
  });

  it("renders nothing when fieldDefinitions is empty", () => {
    const { container } = renderWithTheme(
      <Form layout="vertical">
        <CustomFieldsRenderer fieldDefinitions={{}} />
      </Form>,
    );
    // No form items, no inputs.
    expect(container.querySelector(".ant-form-item")).toBeNull();
  });

  it("respects a custom prefix for the Form.Item name path", async () => {
    const defs: FieldDefinitions = {
      notes: { type: "text", label: "Notes" },
    };
    let captured: unknown;
    const TestForm = () => {
      const [form] = Form.useForm();
      React.useEffect(() => {
        // Seed a value at the custom prefix path, then read it back.
        form.setFieldsValue({ cf: { notes: "x" } });
        captured = form.getFieldsValue(true);
      }, [form]);
      return (
        <Form form={form} layout="vertical">
          <CustomFieldsRenderer fieldDefinitions={defs} prefix="cf" />
        </Form>
      );
    };

    renderWithTheme(<TestForm />);
    // The renderer registered a Form.Item at [cf, notes]; getFieldsValue(true)
    // reflects the seeded value nested under the custom prefix.
    await Promise.resolve();
    expect(captured).toMatchObject({ cf: { notes: "x" } });
  });
});
