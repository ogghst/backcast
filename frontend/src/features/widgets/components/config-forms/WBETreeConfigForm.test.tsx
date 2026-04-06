import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { ConfigProvider } from "antd";
import { WBETreeConfigForm } from "./WBETreeConfigForm";

function renderWithTheme(ui: React.ReactElement) {
  return render(<ConfigProvider>{ui}</ConfigProvider>);
}

describe("WBETreeConfigForm", () => {
  it("renders Show Budget and Show Dates switch controls", () => {
    const onChange = vi.fn();
    renderWithTheme(
      <WBETreeConfigForm config={{ showBudget: false, showDates: false }} onChange={onChange} />,
    );

    expect(screen.getByText("Show Budget")).toBeInTheDocument();
    expect(screen.getByText("Show Dates")).toBeInTheDocument();
  });

  it("shows correct initial values from config prop", () => {
    const onChange = vi.fn();
    renderWithTheme(
      <WBETreeConfigForm config={{ showBudget: true, showDates: true }} onChange={onChange} />,
    );

    const switches = screen.getAllByRole("switch");
    expect(switches).toHaveLength(2);
    expect(switches[0]).toBeChecked();
    expect(switches[1]).toBeChecked();
  });

  it("defaults switches to off when config values are not provided", () => {
    const onChange = vi.fn();
    renderWithTheme(
      <WBETreeConfigForm config={{}} onChange={onChange} />,
    );

    const switches = screen.getAllByRole("switch");
    expect(switches[0]).not.toBeChecked();
    expect(switches[1]).not.toBeChecked();
  });

  it("calls onChange with showBudget update when Show Budget toggled", () => {
    const onChange = vi.fn();
    renderWithTheme(
      <WBETreeConfigForm config={{ showBudget: false, showDates: false }} onChange={onChange} />,
    );

    const switches = screen.getAllByRole("switch");
    fireEvent.click(switches[0]);

    expect(onChange).toHaveBeenCalledWith({ showBudget: true });
  });

  it("calls onChange with showDates update when Show Dates toggled", () => {
    const onChange = vi.fn();
    renderWithTheme(
      <WBETreeConfigForm config={{ showBudget: false, showDates: false }} onChange={onChange} />,
    );

    const switches = screen.getAllByRole("switch");
    fireEvent.click(switches[1]);

    expect(onChange).toHaveBeenCalledWith({ showDates: true });
  });
});
