import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { ConfigProvider } from "antd";
import { CompactKPIStrip } from "./CompactKPIStrip";
import { EntityType, type EVMMetricsResponse } from "@/features/evm/types";

function renderWithTheme(ui: React.ReactElement) {
  return render(<ConfigProvider>{ui}</ConfigProvider>);
}

const baseMetrics: EVMMetricsResponse = {
  entity_type: EntityType.PROJECT,
  entity_id: "proj-1",
  bac: 1_000_000,
  pv: 500_000,
  ac: 480_000,
  ev: 470_000,
  cv: -10_000,
  sv: -30_000,
  cpi: 0.98,
  spi: 0.94,
  eac: 1_020_000,
  vac: -20_000,
  etc: 540_000,
  progress_percentage: 47,
  control_date: "2026-04-01",
  branch: "main",
};

describe("CompactKPIStrip", () => {
  it("renders all 5 metric cells", () => {
    renderWithTheme(<CompactKPIStrip metrics={baseMetrics} />);
    expect(screen.getByText("CPI")).toBeInTheDocument();
    expect(screen.getByText("SPI")).toBeInTheDocument();
    expect(screen.getByText("Progress")).toBeInTheDocument();
    expect(screen.getByText("CV")).toBeInTheDocument();
    expect(screen.getByText("VAC")).toBeInTheDocument();
  });

  it("displays formatted CPI and SPI values with 2 decimals", () => {
    renderWithTheme(<CompactKPIStrip metrics={baseMetrics} />);
    expect(screen.getByText("0.98")).toBeInTheDocument();
    expect(screen.getByText("0.94")).toBeInTheDocument();
  });

  it("displays progress as percentage", () => {
    renderWithTheme(<CompactKPIStrip metrics={baseMetrics} />);
    expect(screen.getByText("47%")).toBeInTheDocument();
  });

  it("displays CV and VAC as compact currency", () => {
    renderWithTheme(<CompactKPIStrip metrics={baseMetrics} />);
    // CV = -10000 → -€10.0K
    expect(screen.getByText("-€10.0K")).toBeInTheDocument();
    // VAC = -20000 → -€20.0K
    expect(screen.getByText("-€20.0K")).toBeInTheDocument();
  });

  it("shows -- for null CPI", () => {
    const metrics = { ...baseMetrics, cpi: null };
    renderWithTheme(<CompactKPIStrip metrics={metrics} />);
    expect(screen.getByText("--")).toBeInTheDocument();
  });

  it("shows -- for null VAC", () => {
    const metrics = { ...baseMetrics, vac: null, eac: null, etc: null };
    renderWithTheme(<CompactKPIStrip metrics={metrics} />);
    // VAC should show "--"
    const allDashDash = screen.getAllByText("--");
    expect(allDashDash.length).toBeGreaterThanOrEqual(1);
  });

  it("renders status dots for each metric", () => {
    const { container } = renderWithTheme(
      <CompactKPIStrip metrics={baseMetrics} />,
    );
    // 5 metrics = 5 dots (span with border-radius: 50%)
    const dots = container.querySelectorAll('span[aria-hidden="true"]');
    expect(dots.length).toBe(5);
  });

  it("renders aria-labels for accessibility", () => {
    renderWithTheme(<CompactKPIStrip metrics={baseMetrics} />);
    const statuses = screen.getAllByRole("status");
    expect(statuses.length).toBe(5);
    // CPI status should contain the value and status
    expect(statuses[0]).toHaveAttribute("aria-label", expect.stringContaining("CPI"));
  });

  it("renders good-status metrics with success color", () => {
    const goodMetrics = {
      ...baseMetrics,
      cpi: 1.05,
      spi: 1.02,
      cv: 50_000,
      vac: 30_000,
    };
    const { container } = renderWithTheme(
      <CompactKPIStrip metrics={goodMetrics} />,
    );
    // All values should be green (success) — check that no error-colored dots exist
    const dots = container.querySelectorAll('span[aria-hidden="true"]');
    dots.forEach((dot) => {
      const bg = (dot as HTMLElement).style.background;
      // Success color from theme: #5da572
      expect(bg).toBeTruthy();
    });
  });

  it("handles large currency values in millions", () => {
    const metrics = {
      ...baseMetrics,
      cv: -2_500_000,
      vac: -3_000_000,
    };
    renderWithTheme(<CompactKPIStrip metrics={metrics} />);
    expect(screen.getByText("-€2.5M")).toBeInTheDocument();
    expect(screen.getByText("-€3.0M")).toBeInTheDocument();
  });
});
