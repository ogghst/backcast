import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { ConfigProvider } from "antd";
import { BudgetStatusConfigForm } from "./BudgetStatusConfigForm";

function renderWithTheme(ui: React.ReactElement) {
  return render(<ConfigProvider>{ui}</ConfigProvider>);
}

describe("BudgetStatusConfigForm", () => {
  it("renders bar and pie radio options", () => {
    const onChange = vi.fn();
    renderWithTheme(
      <BudgetStatusConfigForm config={{ chartType: "bar" }} onChange={onChange} />,
    );

    expect(screen.getByText("Chart Type")).toBeInTheDocument();
    expect(screen.getByText("Bar Chart")).toBeInTheDocument();
    expect(screen.getByText("Pie Chart")).toBeInTheDocument();
  });

  it("shows correct initial value from config prop", () => {
    const onChange = vi.fn();
    renderWithTheme(
      <BudgetStatusConfigForm config={{ chartType: "pie" }} onChange={onChange} />,
    );

    const pieRadio = screen.getByRole("radio", { name: /pie chart/i });
    expect(pieRadio).toBeChecked();

    const barRadio = screen.getByRole("radio", { name: /bar chart/i });
    expect(barRadio).not.toBeChecked();
  });

  it("defaults to bar when chartType is not provided", () => {
    const onChange = vi.fn();
    renderWithTheme(
      <BudgetStatusConfigForm config={{}} onChange={onChange} />,
    );

    const barRadio = screen.getByRole("radio", { name: /bar chart/i });
    expect(barRadio).toBeChecked();
  });

  it("calls onChange with chartType update when selection changes", () => {
    const onChange = vi.fn();
    renderWithTheme(
      <BudgetStatusConfigForm config={{ chartType: "bar" }} onChange={onChange} />,
    );

    const pieRadio = screen.getByRole("radio", { name: /pie chart/i });
    fireEvent.click(pieRadio);

    expect(onChange).toHaveBeenCalledWith({ chartType: "pie" });
  });
});
