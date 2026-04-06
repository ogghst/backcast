import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { ConfigProvider } from "antd";
import { CostRegistrationsConfigForm } from "./CostRegistrationsConfigForm";

function renderWithTheme(ui: React.ReactElement) {
  return render(<ConfigProvider>{ui}</ConfigProvider>);
}

describe("CostRegistrationsConfigForm", () => {
  it("renders Page Size input with correct initial value", () => {
    const onChange = vi.fn();
    renderWithTheme(
      <CostRegistrationsConfigForm config={{ pageSize: 25 }} onChange={onChange} />,
    );

    expect(screen.getByText("Page Size")).toBeInTheDocument();
    const input = screen.getByRole("spinbutton");
    expect(input).toHaveValue("25");
  });

  it("defaults to 20 when pageSize is not provided", () => {
    const onChange = vi.fn();
    renderWithTheme(
      <CostRegistrationsConfigForm config={{}} onChange={onChange} />,
    );

    const input = screen.getByRole("spinbutton");
    expect(input).toHaveValue("20");
  });

  it("calls onChange with pageSize update when input changes", () => {
    const onChange = vi.fn();
    renderWithTheme(
      <CostRegistrationsConfigForm config={{ pageSize: 20 }} onChange={onChange} />,
    );

    const input = screen.getByRole("spinbutton");
    fireEvent.change(input, { target: { value: "50" } });

    expect(onChange).toHaveBeenCalledWith({ pageSize: 50 });
  });

  it("enforces min=5 and max=100 via InputNumber props", () => {
    const onChange = vi.fn();
    renderWithTheme(
      <CostRegistrationsConfigForm config={{ pageSize: 20 }} onChange={onChange} />,
    );

    const input = screen.getByRole("spinbutton");
    // Ant Design InputNumber sets min/max as HTML attributes
    expect(input).toHaveAttribute("aria-valuemin", "5");
    expect(input).toHaveAttribute("aria-valuemax", "100");
  });
});
