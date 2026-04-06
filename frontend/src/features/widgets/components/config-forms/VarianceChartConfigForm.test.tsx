import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { ConfigProvider } from "antd";
import { VarianceChartConfigForm } from "./VarianceChartConfigForm";

function renderWithTheme(ui: React.ReactElement) {
  return render(<ConfigProvider>{ui}</ConfigProvider>);
}

describe("VarianceChartConfigForm", () => {
  it("renders Show Thresholds switch and Threshold Percentage input", () => {
    const onChange = vi.fn();
    renderWithTheme(
      <VarianceChartConfigForm
        config={{ showThresholds: false, thresholdPercent: 10 }}
        onChange={onChange}
      />,
    );

    expect(screen.getByText("Show Thresholds")).toBeInTheDocument();
    expect(screen.getByText("Threshold Percentage")).toBeInTheDocument();
  });

  it("shows correct initial values from config prop", () => {
    const onChange = vi.fn();
    renderWithTheme(
      <VarianceChartConfigForm
        config={{ showThresholds: true, thresholdPercent: 25 }}
        onChange={onChange}
      />,
    );

    const switchEl = screen.getByRole("switch");
    expect(switchEl).toBeChecked();

    const input = screen.getByRole("spinbutton");
    expect(input).toHaveValue("25");
  });

  it("defaults showThresholds to false and thresholdPercent to 10", () => {
    const onChange = vi.fn();
    renderWithTheme(
      <VarianceChartConfigForm config={{}} onChange={onChange} />,
    );

    const switchEl = screen.getByRole("switch");
    expect(switchEl).not.toBeChecked();

    const input = screen.getByRole("spinbutton");
    expect(input).toHaveValue("10");
  });

  it("calls onChange with showThresholds update when switch toggled", () => {
    const onChange = vi.fn();
    renderWithTheme(
      <VarianceChartConfigForm
        config={{ showThresholds: false, thresholdPercent: 10 }}
        onChange={onChange}
      />,
    );

    const switchEl = screen.getByRole("switch");
    fireEvent.click(switchEl);

    expect(onChange).toHaveBeenCalledWith({ showThresholds: true });
  });

  it("calls onChange with thresholdPercent update when input changes", () => {
    const onChange = vi.fn();
    renderWithTheme(
      <VarianceChartConfigForm
        config={{ showThresholds: true, thresholdPercent: 10 }}
        onChange={onChange}
      />,
    );

    const input = screen.getByRole("spinbutton");
    fireEvent.change(input, { target: { value: "30" } });

    expect(onChange).toHaveBeenCalledWith({ thresholdPercent: 30 });
  });

  it("thresholdPercent input is disabled when showThresholds is false", () => {
    const onChange = vi.fn();
    renderWithTheme(
      <VarianceChartConfigForm
        config={{ showThresholds: false, thresholdPercent: 10 }}
        onChange={onChange}
      />,
    );

    const input = screen.getByRole("spinbutton");
    expect(input).toBeDisabled();
  });

  it("thresholdPercent input is enabled when showThresholds is true", () => {
    const onChange = vi.fn();
    renderWithTheme(
      <VarianceChartConfigForm
        config={{ showThresholds: true, thresholdPercent: 10 }}
        onChange={onChange}
      />,
    );

    const input = screen.getByRole("spinbutton");
    expect(input).not.toBeDisabled();
  });

  it("enforces min=0 and max=50 via InputNumber props", () => {
    const onChange = vi.fn();
    renderWithTheme(
      <VarianceChartConfigForm
        config={{ showThresholds: true, thresholdPercent: 10 }}
        onChange={onChange}
      />,
    );

    const input = screen.getByRole("spinbutton");
    expect(input).toHaveAttribute("aria-valuemin", "0");
    expect(input).toHaveAttribute("aria-valuemax", "50");
  });
});
