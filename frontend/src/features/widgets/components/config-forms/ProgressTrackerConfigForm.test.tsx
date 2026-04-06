import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { ConfigProvider } from "antd";
import { ProgressTrackerConfigForm } from "./ProgressTrackerConfigForm";

function renderWithTheme(ui: React.ReactElement) {
  return render(<ConfigProvider>{ui}</ConfigProvider>);
}

describe("ProgressTrackerConfigForm", () => {
  it("renders Show History switch and History Limit input", () => {
    const onChange = vi.fn();
    renderWithTheme(
      <ProgressTrackerConfigForm
        config={{ showHistory: false, historyLimit: 10 }}
        onChange={onChange}
      />,
    );

    expect(screen.getByText("Show History")).toBeInTheDocument();
    expect(screen.getByText("History Limit")).toBeInTheDocument();
  });

  it("shows correct initial values from config prop", () => {
    const onChange = vi.fn();
    renderWithTheme(
      <ProgressTrackerConfigForm
        config={{ showHistory: true, historyLimit: 25 }}
        onChange={onChange}
      />,
    );

    const switchEl = screen.getByRole("switch");
    expect(switchEl).toBeChecked();

    const input = screen.getByRole("spinbutton");
    expect(input).toHaveValue("25");
  });

  it("defaults showHistory to false and historyLimit to 10", () => {
    const onChange = vi.fn();
    renderWithTheme(
      <ProgressTrackerConfigForm config={{}} onChange={onChange} />,
    );

    const switchEl = screen.getByRole("switch");
    expect(switchEl).not.toBeChecked();

    const input = screen.getByRole("spinbutton");
    expect(input).toHaveValue("10");
  });

  it("calls onChange with showHistory update when switch toggled", () => {
    const onChange = vi.fn();
    renderWithTheme(
      <ProgressTrackerConfigForm
        config={{ showHistory: false, historyLimit: 10 }}
        onChange={onChange}
      />,
    );

    const switchEl = screen.getByRole("switch");
    fireEvent.click(switchEl);

    expect(onChange).toHaveBeenCalledWith({ showHistory: true });
  });

  it("calls onChange with historyLimit update when input changes", () => {
    const onChange = vi.fn();
    renderWithTheme(
      <ProgressTrackerConfigForm
        config={{ showHistory: true, historyLimit: 10 }}
        onChange={onChange}
      />,
    );

    const input = screen.getByRole("spinbutton");
    fireEvent.change(input, { target: { value: "50" } });

    expect(onChange).toHaveBeenCalledWith({ historyLimit: 50 });
  });

  it("historyLimit input is disabled when showHistory is false", () => {
    const onChange = vi.fn();
    renderWithTheme(
      <ProgressTrackerConfigForm
        config={{ showHistory: false, historyLimit: 10 }}
        onChange={onChange}
      />,
    );

    const input = screen.getByRole("spinbutton");
    expect(input).toBeDisabled();
  });

  it("historyLimit input is enabled when showHistory is true", () => {
    const onChange = vi.fn();
    renderWithTheme(
      <ProgressTrackerConfigForm
        config={{ showHistory: true, historyLimit: 10 }}
        onChange={onChange}
      />,
    );

    const input = screen.getByRole("spinbutton");
    expect(input).not.toBeDisabled();
  });
});
