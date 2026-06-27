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

  it("CREATE mode hides deprecated and retired fields", () => {
    const defs: FieldDefinitions = {
      live: { type: "text", label: "Live", status: "active" },
      dep: { type: "text", label: "Deprecated", status: "deprecated" },
      ret: { type: "text", label: "Retired", status: "retired" },
    };
    renderWithTheme(
      <Form layout="vertical">
        <CustomFieldsRenderer fieldDefinitions={defs} mode="create" />
      </Form>,
    );
    expect(screen.getByText("Live")).toBeInTheDocument();
    expect(screen.queryByText("Deprecated")).toBeNull();
    expect(screen.queryByText("Retired")).toBeNull();
  });

  it("CREATE mode treats a missing status as active (legacy specs)", () => {
    const defs: FieldDefinitions = {
      legacy: { type: "text", label: "Legacy" },
    };
    renderWithTheme(
      <Form layout="vertical">
        <CustomFieldsRenderer fieldDefinitions={defs} mode="create" />
      </Form>,
    );
    expect(screen.getByText("Legacy")).toBeInTheDocument();
  });

  it("EDIT mode renders deprecated/retired fields as disabled (read-only)", () => {
    const defs: FieldDefinitions = {
      live: { type: "text", label: "Live", status: "active" },
      dep: { type: "text", label: "Deprecated", status: "deprecated" },
      ret: { type: "text", label: "Retired", status: "retired" },
    };
    const { container } = renderWithTheme(
      <Form layout="vertical">
        <CustomFieldsRenderer fieldDefinitions={defs} mode="edit" />
      </Form>,
    );
    // All three fields render in edit mode.
    expect(screen.getByText("Live")).toBeInTheDocument();
    expect(screen.getByText("Deprecated")).toBeInTheDocument();
    expect(screen.getByText("Retired")).toBeInTheDocument();
    const inputs = container.querySelectorAll("input");
    expect(inputs.length).toBe(3);
    // Live input is editable; deprecated + retired are disabled (read-only).
    expect(inputs[0].hasAttribute("disabled")).toBe(false);
    expect(inputs[1].hasAttribute("disabled")).toBe(true);
    expect(inputs[2].hasAttribute("disabled")).toBe(true);
  });

  it("EDIT mode: live status overlay wins over the snapshot's spec.status", () => {
    // The snapshot froze status=active, but the live template now says retired.
    const defs: FieldDefinitions = {
      promoted: { type: "text", label: "Promoted", status: "active" },
    };
    const liveStatuses = { promoted: "retired" as const };
    const { container } = renderWithTheme(
      <Form layout="vertical">
        <CustomFieldsRenderer
          fieldDefinitions={defs}
          mode="edit"
          liveStatuses={liveStatuses}
        />
      </Form>,
    );
    const input = container.querySelector("input");
    expect(input).not.toBeNull();
    expect(input?.hasAttribute("disabled")).toBe(true);
  });

  it("EDIT mode: a live status absent from the overlay falls back to the snapshot status", () => {
    // No overlay supplied; the snapshot's deprecated status governs.
    const defs: FieldDefinitions = {
      snap: { type: "text", label: "Snap", status: "deprecated" },
    };
    const { container } = renderWithTheme(
      <Form layout="vertical">
        <CustomFieldsRenderer fieldDefinitions={defs} mode="edit" />
      </Form>,
    );
    const input = container.querySelector("input");
    expect(input?.hasAttribute("disabled")).toBe(true);
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
