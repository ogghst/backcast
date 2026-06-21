import { describe, it, expect, vi, beforeEach } from "vitest";
import type { ReactNode } from "react";
import { render, screen, within } from "@testing-library/react";
import { EntityHeaderCard } from "./EntityHeaderCard";

/**
 * Tests for EntityHeaderCard — shared TIME/BUDGET donut header.
 *
 * The component reads Ant Design theme tokens via useExtendedToken() and the
 * time-travel asOf via useTimeMachineParams(). Both are mocked at module level
 * so we never need an antd ConfigProvider or a TimeMachineProvider wrapper.
 *
 * jsdom has no layout engine, so we assert on text content, ARIA roles, and
 * child-element counts — never on pixel sizes or centering.
 */

// --- Mock: useExtendedToken -------------------------------------------------
// Provide every `token.*` field the component (and CardTitleRow) reads, so the
// component never crashes on undefined. Colors are arbitrary non-empty strings
// so any token-based styling (strokeColor, background) resolves truthily.
const mockToken = {
  colorPrimary: "#1677ff",
  colorError: "#ff4d4f",
  colorWarning: "#faad14",
  colorSuccess: "#52c41a",
  colorBorder: "#d9d9d9",
  colorBorderSecondary: "#f0f0f0",
  colorText: "#000000",
  colorTextSecondary: "#888888",
  marginLG: 24,
  marginMD: 16,
  marginXS: 8,
  paddingSM: 12,
  paddingMD: 16,
  paddingXL: 24,
  borderRadiusLG: 8,
  fontSize: 14,
  fontSizeXS: 11,
  fontSizeSM: 12,
  fontSizeLG: 16,
  fontSizeXL: 20,
  fontSizeXXL: 24,
  fontWeightNormal: 400,
  fontWeightMedium: 500,
  fontWeightSemiBold: 600,
  fontWeightBold: 700,
  lineHeight: 1.5715,
};

vi.mock("@/hooks/useToken", () => ({
  useExtendedToken: () => ({ token: mockToken }),
}));

// --- Mock: useTimeMachineParams --------------------------------------------
// Per-test override of asOf via `mockAsOf`. branch/mode are unused by the
// component but required by the hook's return type.
let mockAsOf: string | undefined = undefined;

vi.mock("@/contexts/TimeMachineContext", () => ({
  useTimeMachineParams: () => ({ asOf: mockAsOf, branch: "main", mode: "merged" }),
}));

beforeEach(() => {
  mockAsOf = undefined;
});

describe("EntityHeaderCard", () => {
  it("renders title, badge, and description", () => {
    render(
      <EntityHeaderCard
        title="My Project"
        badge={<span>Active</span>}
        description="A test project"
      />,
    );

    expect(screen.getByText("My Project")).toBeInTheDocument();
    expect(screen.getByText("Active")).toBeInTheDocument();
    expect(screen.getByText("A test project")).toBeInTheDocument();
  });

  it("renders a non-zero time percent and 'elapsed' label mid-window", () => {
    // Window: 2020-01-01 → 2020-12-31 (leap-year span). Reference at the
    // midpoint (2020-07-02) yields ~50%. We assert > 0% and not 100%.
    render(
      <EntityHeaderCard
        title="T"
        scheduleStart="2020-01-01T00:00:00Z"
        scheduleEnd="2020-12-31T00:00:00Z"
        controlDate="2020-07-02T00:00:00Z"
      />,
    );

    // The TIME donut is the first Progress circle; its format renders the
    // percent text plus the "elapsed" caption.
    expect(screen.getByText("elapsed")).toBeInTheDocument();

    // Find the time donut's percent text: it lives in the same container as
    // "elapsed", as a preceding sibling.
    const elapsedBlock = screen.getByText("elapsed").parentElement;
    expect(elapsedBlock).not.toBeNull();
    const pctText = within(elapsedBlock!).getByText(/\d+%/);
    const numericPct = parseInt(pctText.textContent ?? "0", 10);
    expect(numericPct).toBeGreaterThan(0);
    expect(numericPct).toBeLessThan(100);
  });

  it("renders 0% time progress and Timeline fallback when scheduleStart missing", () => {
    render(<EntityHeaderCard title="T" scheduleEnd="2020-12-31T00:00:00Z" />);

    expect(screen.getByText("elapsed")).toBeInTheDocument();
    // The time donut percent text — fallback to 0%.
    const elapsedBlock = screen.getByText("elapsed").parentElement!;
    expect(within(elapsedBlock).getByText("0%")).toBeInTheDocument();

    // Missing start/end render the formatDate fallback "—".
    expect(screen.getAllByText("—").length).toBeGreaterThan(0);
  });

  it("shows the control date when provided", () => {
    render(<EntityHeaderCard title="T" controlDate="2021-06-15T00:00:00Z" />);

    expect(screen.getByText(/Control:/)).toBeInTheDocument();
  });

  it("renders budget label with EUR currency and 0% of budget when actualCosts=0", () => {
    render(
      <EntityHeaderCard
        title="T"
        budget={95000}
        currency="EUR"
        actualCosts={0}
      />,
    );

    // Budget label is a strong <Text> holding "€95.0K" immediately followed by
    // the "budget" caption. Scope currency checks to that label node.
    const budgetCaption = screen.getByText("budget");
    const budgetLabelRow = budgetCaption.parentElement!;
    // Compact currency for 95000 EUR → "€95.0K".
    expect(budgetLabelRow.textContent).toContain("€");
    expect(budgetLabelRow.textContent).toContain("95");

    // Budget donut percent — "of budget" caption identifies the budget ring.
    const budgetBlock = screen.getByText("of budget").parentElement!;
    expect(within(budgetBlock).getByText("0%")).toBeInTheDocument();
  });

  it("renders an additional revenue Progress ring only when revenue > 0", () => {
    // The budget section is the column containing the "of budget" caption.
    // We count Progress instances scoped to THAT column, so the separate TIME
    // donut (its own column) never inflates the count.
    // Per-instance Progress wrapper is the root ".ant-progress" element (also
    // carrying "ant-progress-circle"); ".ant-progress-circle" alone matches
    // nested inner wrappers too.
    const countBudgetRings = () => {
      const budgetCol = screen.getByText("of budget").closest(
        "div[class*='ant-col'], section, li, td",
      ) as HTMLElement | null;
      const scope = budgetCol ?? document.body;
      return Array.from(scope.querySelectorAll(".ant-progress")).filter((el) =>
        el.classList.contains("ant-progress-circle"),
      ).length;
    };

    // Case A: revenue > 0 → TWO budget-section rings (revenue outer + budget inner).
    const { rerender } = render(
      <EntityHeaderCard
        title="T"
        budget={100}
        actualCosts={40}
        revenue={200}
      />,
    );
    // The revenue legend line proves the revenue branch rendered.
    expect(screen.getByText(/revenue/)).toBeInTheDocument();
    expect(countBudgetRings()).toBe(2);

    // Case B: revenue undefined → exactly ONE budget-section ring, no revenue legend.
    rerender(<EntityHeaderCard title="T" budget={100} actualCosts={40} />);
    expect(screen.queryByText(/revenue/)).not.toBeInTheDocument();
    expect(countBudgetRings()).toBe(1);
  });

  it("renders footer only when provided", () => {
    const footer: ReactNode = <div data-testid="footer">FOOTER</div>;

    const { rerender } = render(<EntityHeaderCard title="T" footer={footer} />);
    expect(screen.getByTestId("footer")).toBeInTheDocument();

    rerender(<EntityHeaderCard title="T" />);
    expect(screen.queryByTestId("footer")).not.toBeInTheDocument();
  });

  it("renders extraContent when provided", () => {
    render(<EntityHeaderCard title="T" extraContent={<div>CHART</div>} />);

    expect(screen.getByText("CHART")).toBeInTheDocument();
  });

  it("prefers TimeMachine asOf over controlDate for time percent", () => {
    mockAsOf = "2020-07-02T00:00:00Z"; // midpoint reference
    render(
      <EntityHeaderCard
        title="T"
        scheduleStart="2020-01-01T00:00:00Z"
        scheduleEnd="2020-12-31T00:00:00Z"
        controlDate="2010-01-01T00:00:00Z" // would yield 0% if used
      />,
    );

    const elapsedBlock = screen.getByText("elapsed").parentElement!;
    const pctText = within(elapsedBlock).getByText(/\d+%/);
    const numericPct = parseInt(pctText.textContent ?? "0", 10);
    // asOf wins → ~50%, not the ~0% controlDate would produce.
    expect(numericPct).toBeGreaterThan(0);
    expect(numericPct).toBeLessThan(100);
  });
});
