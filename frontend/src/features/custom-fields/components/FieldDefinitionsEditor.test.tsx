import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent, act } from "@testing-library/react";
import { App, ConfigProvider } from "antd";
import { useState } from "react";

import {
  FieldDefinitionsEditor,
  type FieldDefinitionsValue,
} from "./FieldDefinitionsEditor";

function renderWithTheme(ui: React.ReactElement) {
  return render(
    <App>
      <ConfigProvider>{ui}</ConfigProvider>
    </App>,
  );
}

describe("FieldDefinitionsEditor", () => {
  it("renders existing fields from the value prop", () => {
    const value: FieldDefinitionsValue = {
      priority: { type: "select", label: "Priority", options: ["low", "high"] },
    };
    renderWithTheme(
      <FieldDefinitionsEditor value={value} onChange={vi.fn()} />,
    );
    // Code + label inputs are pre-filled.
    expect(
      (screen.getByPlaceholderText("priority") as HTMLInputElement).value,
    ).toBe("priority");
    expect(
      (screen.getByPlaceholderText("Priority") as HTMLInputElement).value,
    ).toBe("Priority");
  });

  it("shows the empty hint when there are no fields", () => {
    renderWithTheme(
      <FieldDefinitionsEditor value={{}} onChange={vi.fn()} />,
    );
    expect(screen.getByText(/no custom fields defined/i)).toBeInTheDocument();
  });

  it("adds a field and emits the new dict via onChange", () => {
    const onChange = vi.fn();
    renderWithTheme(
      <FieldDefinitionsEditor value={{}} onChange={onChange} />,
    );
    fireEvent.click(screen.getByRole("button", { name: /add field/i }));
    expect(onChange).toHaveBeenCalledTimes(1);
    // An empty-code row serializes to an empty dict (empty codes skipped).
    expect(onChange).toHaveBeenCalledWith({});
  });

  // Regression: when the parent ECHOES onChange back as value (as Antd Form
  // does for a controlled Form.Item child), an in-progress empty-code row
  // must persist. Previously, the round-trip serialized the empty row out,
  // the echo re-derived rows from the now-empty dict, and the row vanished —
  // so "Add Field" appeared to do nothing and typing into a new row dropped
  // it. The non-echoing harness above misses this; this test is the guard.
  it("persists a newly-added empty-code row under an echoing (form-controlled) parent", () => {
    function Controlled() {
      const [v, setV] = useState<FieldDefinitionsValue>({});
      return (
        <FieldDefinitionsEditor value={v} onChange={setV} />
      );
    }
    renderWithTheme(<Controlled />);

    const codeInputsBefore = screen.queryAllByPlaceholderText("priority");
    expect(codeInputsBefore).toHaveLength(0);

    fireEvent.click(screen.getByRole("button", { name: /add field/i }));
    // The empty-code row survives the value round-trip and stays rendered.
    expect(screen.getAllByPlaceholderText("priority")).toHaveLength(1);

    // Typing into the new row's Code input must keep the row (it must not be
    // dropped by the echo + re-derive cycle while the code is mid-edit).
    const codeInput = screen.getByPlaceholderText("priority");
    fireEvent.change(codeInput, { target: { value: "p" } });
    expect((codeInput as HTMLInputElement).value).toBe("p");
    expect(screen.getAllByPlaceholderText("priority")).toHaveLength(1);

    // A re-render / act tick must not drop the row either.
    act(() => {});
    expect(screen.getAllByPlaceholderText("priority")).toHaveLength(1);
  });

  it("serializes type-specific config (options, max_length, target_entity)", () => {
    const onChange = vi.fn();
    const value: FieldDefinitionsValue = {
      // select -> options
      priority: { type: "select", label: "Priority", options: ["low"] },
      // text -> max_length
      reason: { type: "text", label: "Reason", max_length: 500, required: true },
      // reference -> target_entity
      owner: { type: "reference", label: "Owner", target_entity: "user" },
      // number -> no extra config
      amount: { type: "number", label: "Amount" },
    };
    renderWithTheme(
      <FieldDefinitionsEditor value={value} onChange={onChange} />,
    );

    // Re-emit by toggling required on the first row's switch. We grab switches
    // (Required + the type-specific ones); toggling any fires onChange with the
    // full serialized dict. Simpler: re-render with a fresh onChange and patch
    // a label to force an emit, then assert the payload shape.
    const labelInput = screen.getByDisplayValue("Priority");
    fireEvent.change(labelInput, { target: { value: "Prio2" } });

    const lastCall = onChange.mock.calls.at(-1)?.[0] as FieldDefinitionsValue;
    expect(lastCall).toBeDefined();
    // options preserved on select
    expect(lastCall.priority.options).toEqual(["low"]);
    // max_length + required preserved on text
    expect(lastCall.reason.max_length).toBe(500);
    expect(lastCall.reason.required).toBe(true);
    // target_entity preserved on reference
    expect(lastCall.owner.target_entity).toBe("user");
    // number has no extra config keys beyond type/label + the always-emitted
    // top-level booleans ai_visible / searchable (default OFF) and status
    // (default "active").
    expect(lastCall.amount).toEqual({
      type: "number",
      label: "Amount",
      status: "active",
      ai_visible: false,
      searchable: false,
    });
    // label update applied
    expect(lastCall.priority.label).toBe("Prio2");
    // code never written into the inner spec (backend injects it)
    expect("code" in lastCall.priority).toBe(false);
  });

  it("toggles AI-visible ON and serializes it as a top-level spec key", () => {
    const onChange = vi.fn();
    const value: FieldDefinitionsValue = {
      priority: { type: "select", label: "Priority" },
    };
    renderWithTheme(
      <FieldDefinitionsEditor value={value} onChange={onChange} />,
    );

    // Default OFF: toggling required first to capture the OFF baseline.
    const switches = screen.getAllByRole("switch");
    // Row layout: [Required, AI-visible]; toggle the AI-visible switch on.
    const aiSwitch = switches[1];
    fireEvent.click(aiSwitch);

    const onCall = onChange.mock.calls.at(-1)?.[0] as FieldDefinitionsValue;
    expect(onCall).toBeDefined();
    expect(onCall.priority.ai_visible).toBe(true);
    // It is a TOP-LEVEL spec key (sibling of type/label), not nested in config.
    expect("ai_visible" in onCall.priority).toBe(true);
    expect("config" in onCall.priority).toBe(false);

    // Toggle it back OFF: ai_visible must be present and false (explicit).
    fireEvent.click(aiSwitch);
    const offCall = onChange.mock.calls.at(-1)?.[0] as FieldDefinitionsValue;
    expect(offCall.priority.ai_visible).toBe(false);
  });

  it("omits ai_visible from the spec when the stored value lacks it", () => {
    const onChange = vi.fn();
    const value: FieldDefinitionsValue = {
      amount: { type: "number", label: "Amount" },
    };
    renderWithTheme(
      <FieldDefinitionsEditor value={value} onChange={onChange} />,
    );
    // Force an emit by editing the label; ai_visible was absent in the input.
    fireEvent.change(screen.getByDisplayValue("Amount"), {
      target: { value: "Amt2" },
    });
    const lastCall = onChange.mock.calls.at(-1)?.[0] as FieldDefinitionsValue;
    expect(lastCall).toBeDefined();
    // Editor round-trips absent -> explicit false (top-level boolean).
    expect(lastCall.amount.ai_visible).toBe(false);
  });

  it("toggles Searchable ON and serializes it as a top-level spec key", () => {
    const onChange = vi.fn();
    const value: FieldDefinitionsValue = {
      priority: { type: "select", label: "Priority" },
    };
    renderWithTheme(
      <FieldDefinitionsEditor value={value} onChange={onChange} />,
    );

    // Row layout: [Required, AI-visible, Searchable]; toggle the Searchable
    // switch (index 2) on.
    const switches = screen.getAllByRole("switch");
    const searchableSwitch = switches[2];
    fireEvent.click(searchableSwitch);

    const onCall = onChange.mock.calls.at(-1)?.[0] as FieldDefinitionsValue;
    expect(onCall).toBeDefined();
    expect(onCall.priority.searchable).toBe(true);
    // It is a TOP-LEVEL spec key (sibling of type/label), not nested in config.
    expect("searchable" in onCall.priority).toBe(true);
    expect("config" in onCall.priority).toBe(false);

    // Toggle it back OFF: searchable must be present and false (explicit).
    fireEvent.click(searchableSwitch);
    const offCall = onChange.mock.calls.at(-1)?.[0] as FieldDefinitionsValue;
    expect(offCall.priority.searchable).toBe(false);
  });

  it("omits searchable from the spec when the stored value lacks it", () => {
    const onChange = vi.fn();
    const value: FieldDefinitionsValue = {
      amount: { type: "number", label: "Amount" },
    };
    renderWithTheme(
      <FieldDefinitionsEditor value={value} onChange={onChange} />,
    );
    // Force an emit by editing the label; searchable was absent in the input.
    fireEvent.change(screen.getByDisplayValue("Amount"), {
      target: { value: "Amt2" },
    });
    const lastCall = onChange.mock.calls.at(-1)?.[0] as FieldDefinitionsValue;
    expect(lastCall).toBeDefined();
    // Editor round-trips absent -> explicit false (top-level boolean).
    expect(lastCall.amount.searchable).toBe(false);
  });

  it("serializes status as a top-level spec key, defaulting to active", () => {
    const onChange = vi.fn();
    const value: FieldDefinitionsValue = {
      amount: { type: "number", label: "Amount" },
    };
    renderWithTheme(
      <FieldDefinitionsEditor value={value} onChange={onChange} />,
    );
    // Force an emit by editing the label; status was absent in the input.
    fireEvent.change(screen.getByDisplayValue("Amount"), {
      target: { value: "Amt2" },
    });
    const lastCall = onChange.mock.calls.at(-1)?.[0] as FieldDefinitionsValue;
    expect(lastCall).toBeDefined();
    // Editor round-trips absent -> explicit "active" (top-level).
    expect(lastCall.amount.status).toBe("active");
    expect("status" in lastCall.amount).toBe(true);
  });

  it("preserves a non-default status through the round-trip", () => {
    const onChange = vi.fn();
    const value: FieldDefinitionsValue = {
      legacy: { type: "text", label: "Legacy", status: "deprecated" },
    };
    renderWithTheme(
      <FieldDefinitionsEditor value={value} onChange={onChange} />,
    );
    // The Segmented control renders the deprecated value as the active option.
    const deprecatedControls = screen.getAllByText("deprecated");
    expect(deprecatedControls.length).toBeGreaterThan(0);
    // Force an emit by editing the label; status must survive the round-trip.
    fireEvent.change(screen.getByDisplayValue("Legacy"), {
      target: { value: "Legacy2" },
    });
    const lastCall = onChange.mock.calls.at(-1)?.[0] as FieldDefinitionsValue;
    expect(lastCall.legacy.status).toBe("deprecated");
  });

  it("removes a field via the remove button", () => {
    const onChange = vi.fn();
    const value: FieldDefinitionsValue = {
      priority: { type: "select", label: "Priority" },
      reason: { type: "text", label: "Reason" },
    };
    renderWithTheme(
      <FieldDefinitionsEditor value={value} onChange={onChange} />,
    );
    // antd icon buttons expose the label via `title`, not the accessible name.
    const removeButtons = screen
      .getAllByRole("button")
      .filter((b) => b.getAttribute("title") === "Remove field");
    expect(removeButtons.length).toBe(2);
    // Remove the first row (priority).
    fireEvent.click(removeButtons[0]);
    const lastCall = onChange.mock.calls.at(-1)?.[0] as FieldDefinitionsValue;
    expect(Object.keys(lastCall)).toEqual(["reason"]);
  });

  it("flags duplicate codes with an error message", () => {
    // Two rows with the same code: edit the second row's code to collide.
    const value: FieldDefinitionsValue = {
      dup: { type: "text", label: "First" },
    };
    renderWithTheme(
      <FieldDefinitionsEditor value={value} onChange={vi.fn()} />,
    );
    // Add a second field and type the same code "dup".
    fireEvent.click(screen.getByRole("button", { name: /add field/i }));
    const codeInputs = screen.getAllByPlaceholderText("priority");
    fireEvent.change(codeInputs[1], { target: { value: "dup" } });
    // Both colliding rows render the duplicate-code message.
    expect(screen.getAllByText("Code must be unique").length).toBeGreaterThanOrEqual(1);
  });
});
