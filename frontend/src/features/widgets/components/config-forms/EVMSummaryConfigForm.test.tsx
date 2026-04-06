import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { ConfigProvider } from "antd";
import { EVMSummaryConfigForm } from "./EVMSummaryConfigForm";

function renderWithTheme(ui: React.ReactElement) {
  return render(<ConfigProvider>{ui}</ConfigProvider>);
}

describe("EVMSummaryConfigForm", () => {
  it("renders Entity Type select with PROJECT/WBE/COST_ELEMENT options", () => {
    const onChange = vi.fn();
    renderWithTheme(
      <EVMSummaryConfigForm config={{ entityType: "PROJECT" }} onChange={onChange} />,
    );

    expect(screen.getByText("Entity Type")).toBeInTheDocument();
    // Project is the selected value shown in the Select
    expect(screen.getByText("Project")).toBeInTheDocument();
  });

  it("shows correct initial value from config prop", () => {
    const onChange = vi.fn();
    renderWithTheme(
      <EVMSummaryConfigForm config={{ entityType: "WBE" }} onChange={onChange} />,
    );

    // Ant Design Select renders the selected value as visible text
    expect(screen.getByText("WBE (Work Breakdown Element)")).toBeInTheDocument();
  });

  it("defaults to PROJECT when entityType is not provided", () => {
    const onChange = vi.fn();
    renderWithTheme(
      <EVMSummaryConfigForm config={{}} onChange={onChange} />,
    );

    expect(screen.getByText("Project")).toBeInTheDocument();
  });

  it("calls onChange with correct partial update when selection changes", () => {
    const onChange = vi.fn();
    renderWithTheme(
      <EVMSummaryConfigForm config={{ entityType: "PROJECT" }} onChange={onChange} />,
    );

    // Open the select dropdown by clicking on it
    const selectTrigger = screen.getByRole("combobox");
    fireEvent.mouseDown(selectTrigger);

    // Click the "Cost Element" option
    const costElementOption = screen.getByText("Cost Element");
    fireEvent.click(costElementOption);

    expect(onChange).toHaveBeenCalledWith({ entityType: "COST_ELEMENT" });
  });
});
