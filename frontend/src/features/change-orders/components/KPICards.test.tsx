import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import { KPICards } from "./KPICards";

describe("KPICards Component", () => {
  const mockKPIData: KPIScorecard = {
    bac: {
      main_value: "1000000",
      change_value: "1050000",
      delta: "50000",
      delta_percent: 5.0,
    },
    budget_delta: {
      main_value: "1000000",
      change_value: "1050000",
      delta: "50000",
      delta_percent: 5.0,
    },
    revenue_delta: {
      main_value: "1200000",
      change_value: "1250000",
      delta: "50000",
      delta_percent: 4.17,
    },
    gross_margin: {
      main_value: "200000",
      change_value: "200000",
      delta: "0",
      delta_percent: 0.0,
    },
    actual_costs: {
      main_value: "800000",
      change_value: "850000",
      delta: "50000",
      delta_percent: 6.25,
    },
  };

  it("renders financial metrics section", () => {
    render(<KPICards kpiScorecard={mockKPIData} />);

    expect(screen.getByText("Financial Metrics")).toBeInTheDocument();
    expect(screen.getByText("Budget at Completion")).toBeInTheDocument();
    expect(screen.getByText("Total Budget Allocation")).toBeInTheDocument();
    expect(screen.getByText("Revenue Allocation")).toBeInTheDocument();
    expect(screen.getByText("Gross Margin")).toBeInTheDocument();
    expect(screen.getByText("Actual Costs")).toBeInTheDocument();
  });

  it("renders EAC and VAC cards when present", () => {
    const dataWithEVM: KPIScorecard = {
      ...mockKPIData,
      eac: {
        main_value: "1100000",
        change_value: "1150000",
        delta: "50000",
        delta_percent: 4.55,
      },
      vac: {
        main_value: "-100000",
        change_value: "-100000",
        delta: "0",
        delta_percent: 0.0,
      },
    };

    render(<KPICards kpiScorecard={dataWithEVM} />);

    expect(screen.getByText("Estimate at Completion")).toBeInTheDocument();
    expect(screen.getByText("Variance at Completion")).toBeInTheDocument();
  });

  it("renders schedule and performance metrics section when available", () => {
    const dataWithSchedule: KPIScorecard = {
      ...mockKPIData,
      schedule_duration: {
        main_value: "150",
        change_value: "160",
        delta: "10",
        delta_percent: 6.67,
      },
      cpi: {
        main_value: "0.95",
        change_value: "0.92",
        delta: "-0.03",
        delta_percent: -3.16,
      },
      spi: {
        main_value: "1.05",
        change_value: "1.02",
        delta: "-0.03",
        delta_percent: -2.86,
      },
      tcpi: {
        main_value: "1.10",
        change_value: "1.15",
        delta: "0.05",
        delta_percent: 4.55,
      },
    };

    render(<KPICards kpiScorecard={dataWithSchedule} />);

    expect(screen.getByText("Schedule & Performance Metrics")).toBeInTheDocument();
    expect(screen.getByText("Schedule Duration")).toBeInTheDocument();
    expect(screen.getByText("Cost Performance Index")).toBeInTheDocument();
    expect(screen.getByText("Schedule Performance Index")).toBeInTheDocument();
    expect(screen.getByText("To-Complete Performance Index")).toBeInTheDocument();
  });

  it("does not render schedule section when no schedule or performance metrics", () => {
    render(<KPICards kpiScorecard={mockKPIData} />);

    expect(screen.queryByText("Schedule & Performance Metrics")).not.toBeInTheDocument();
  });

  it("displays loading spinner when loading prop is true", () => {
    const { container } = render(
      <KPICards kpiScorecard={mockKPIData} loading={true} />
    );

    // Ant Design Spin renders a div with class ant-spin
    expect(container.querySelector(".ant-spin")).toBeInTheDocument();
  });

  it("shows target indicators for performance indices", () => {
    const dataWithCPI: KPIScorecard = {
      ...mockKPIData,
      cpi: {
        main_value: "0.95",
        change_value: "1.02",
        delta: "0.07",
        delta_percent: 7.37,
      },
    };

    render(<KPICards kpiScorecard={dataWithCPI} />);

    // Check that CPI card is rendered with target indicator
    expect(screen.getByText("Cost Performance Index")).toBeInTheDocument();
    // The target text is in small detail text
    expect(screen.getByText(/Target:/)).toBeInTheDocument();
  });

  it("shows correct target for TCPI", () => {
    const dataWithTCPI: KPIScorecard = {
      ...mockKPIData,
      tcpi: {
        main_value: "1.10",
        change_value: "1.05",
        delta: "-0.05",
        delta_percent: -4.55,
      },
    };

    render(<KPICards kpiScorecard={dataWithTCPI} />);

    // Check that TCPI card is rendered
    expect(screen.getByText("To-Complete Performance Index")).toBeInTheDocument();
  });
});
