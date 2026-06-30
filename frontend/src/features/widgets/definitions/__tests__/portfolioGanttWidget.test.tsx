/**
 * Phase 4 render tests for the Portfolio Timeline (portfolio-gantt) widget.
 *
 * Mirrors `portfolioWidgets.test.tsx` (mock `usePortfolioEVM` + the
 * DashboardContextBus harness). Because the Gantt bars render on an ECharts
 * canvas (not the DOM), the row-count / skip / filter assertions spy on the
 * engine entry — `buildGanttOptions` — and read the `rows` array it receives.
 * That captures the widget's row model without depending on canvas rendering.
 *
 * Design doc §7 Phase 4 verify: portfolio-gantt renders one bar per project
 * that has BOTH start+end dates, skips projects missing either, honours the
 * portfolio status/RAG filter, and registers with scope:'portfolio' +
 * requiredPermission:'portfolio-read'.
 */

import { describe, it, expect, beforeEach, vi } from "vitest";
import { render } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";
import { App as AntdApp } from "antd";
import type { ReactNode } from "react";

// ── Mocks ───────────────────────────────────────────────────────────────────
//
// `DashboardContextBus` consumes TimeMachineContext internally; mock it the same
// way portfolioWidgets.test.tsx does.
vi.mock("@/contexts/TimeMachineContext", () => ({
  useTimeMachine: () => ({
    asOf: undefined,
    branch: "main",
    mode: "merged",
    isHistorical: false,
    invalidateQueries: vi.fn(),
  }),
}));

const usePortfolioEVMMock = vi.fn();
vi.mock("@/features/portfolio/api/usePortfolioEVM", () => ({
  usePortfolioEVM: () => usePortfolioEVMMock(),
}));

// Spy on the Gantt engine entry. ScheduleTimeline imports buildGanttOptions by
// name from this path, so the mock intercepts it and captures the rows array.
// vi.hoisted is required because vi.mock factories are hoisted above top-level
// const declarations — the spy must exist at hoist time.
const { buildGanttOptionsMock } = vi.hoisted(() => ({
  buildGanttOptionsMock: vi.fn(() => ({ series: [], xAxis: [], yAxis: [] })),
}));
vi.mock("@/features/schedule-baselines/components/GanttChart/GanttChartOptions", () => ({
  buildGanttOptions: buildGanttOptionsMock,
  // defaultGanttTooltip is exported by the options module; not needed here but
  // kept to satisfy any transitive import shape.
  defaultGanttTooltip: vi.fn(),
}));

// useEChartsTheme returns token values used for bar colour + tooltip; return a
// minimal valid palette so the widget's barColorFor resolves real tokens.
vi.mock("@/features/evm/utils/echartsTheme", () => ({
  useEChartsTheme: () => ({
    colors: {
      primary: "#1677ff",
      success: "#52c41a",
      warning: "#faad14",
      error: "#ff4d4f",
      info: "#1677ff",
      pv: "#5b8ff9",
      ev: "#5ad8a6",
      ac: "#5d7092",
      forecast: "#faad14",
      actual: "#ff4d4f",
      gaugeGood: "#52c41a",
      gaugeWarning: "#faad14",
      gaugeBad: "#ff4d4f",
      text: "#000",
      textSecondary: "#8c8c8c",
      border: "#d9d9d9",
      bg: "#fff",
    },
    tooltipConfig: {
      backgroundColor: "#fff",
      borderColor: "#d9d9d9",
      borderWidth: 1,
      textStyle: { color: "#000", fontSize: 12 },
      padding: [8, 12],
      extraCssText: "",
    },
  }),
}));

// Import the definitions AFTER mocks are registered so the registry picks up
// the side-effecting registerWidget() calls via registerAll.
import "@/features/widgets/definitions/registerAll";
import { getWidgetDefinition, getAllWidgetDefinitions } from "../..";
import { widgetTypeId } from "../../types";
import { DashboardContextBus } from "../../context/DashboardContextBus";

// ── Helpers ─────────────────────────────────────────────────────────────────

/** Build a portfolio project with the given id, name, dates, and EVM. */
function project(opts: {
  id: string;
  name: string;
  start?: string | null;
  end?: string | null;
  status?: string;
  cpi?: number | null;
  spi?: number | null;
}) {
  return {
    project_id: opts.id,
    name: opts.name,
    status: opts.status ?? "active",
    cpi: opts.cpi ?? null,
    spi: opts.spi ?? null,
    vac: 0,
    contract_value: 1000,
    bac: 1000,
    currency: "EUR",
    at_risk: false,
    start_date: opts.start === undefined ? "2025-01-01" : opts.start,
    end_date: opts.end === undefined ? "2025-06-01" : opts.end,
  };
}

function setPortfolioEVM(projects: ReturnType<typeof project>[]) {
  usePortfolioEVMMock.mockReturnValue({
    data: {
      summary: { cpi: 1.0, spi: 1.0, vac: 0, tcpi: 1.0 },
      projects,
      at_risk_projects: [],
    },
    isLoading: false,
    error: null,
    refetch: vi.fn(),
  });
}

/** Portfolio-scope harness: real context provider with projectId="" + filter. */
function renderInPortfolio(
  ui: ReactNode,
  portfolioFilter: {
    controlDate: string | null;
    status: string[] | null;
    rag: string[] | null;
  } = { controlDate: null, status: null, rag: null },
) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });

  const Wrapper = ({ children }: { children: ReactNode }) => (
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>
        <AntdApp>
          <DashboardContextBus
            scope="portfolio"
            portfolioFilter={portfolioFilter}
          >
            {children}
          </DashboardContextBus>
        </AntdApp>
      </MemoryRouter>
    </QueryClientProvider>
  );

  return render(<div style={{ height: 400 }}>{ui}</div>, { wrapper: Wrapper });
}

/** Look up the widget's render component and invoke it directly. */
function renderWidget(typeIdStr: string, config: Record<string, unknown>) {
  const def = getWidgetDefinition(widgetTypeId(typeIdStr));
  if (!def) throw new Error(`widget ${typeIdStr} not registered`);
  const Component = def.component;
  return renderInPortfolio(
    <Component config={config} instanceId="inst-1" isEditing={false} onRemove={vi.fn()} />,
  );
}

/** Read the most recent rows array passed to the mocked buildGanttOptions. */
function lastRows(): unknown[] {
  const calls = buildGanttOptionsMock.mock.calls;
  if (calls.length === 0) return [];
  // calls is a variadic tuple; cast through unknown to read the first arg
  // (the rows array) without asserting a fixed-length tuple shape.
  return (calls[calls.length - 1] as unknown[])[0] as unknown[];
}

// ── Tests ───────────────────────────────────────────────────────────────────

describe("PortfolioGanttWidget — registry", () => {
  it("registers portfolio-gantt with scope:'portfolio' + requiredPermission:'portfolio-read'", () => {
    const def = getWidgetDefinition(widgetTypeId("portfolio-gantt"));
    expect(def, "portfolio-gantt must be registered").toBeDefined();
    expect(def?.scope).toBe("portfolio");
    expect(def?.requiredPermission).toBe("portfolio-read");
  });

  it("the registry now holds 26 definitions (21 project + 5 portfolio)", () => {
    expect(getAllWidgetDefinitions()).toHaveLength(26);
  });
});

describe("PortfolioGanttWidget — row model", () => {
  beforeEach(() => {
    usePortfolioEVMMock.mockReset();
    buildGanttOptionsMock.mockClear();
  });

  it("renders one bar per project that has BOTH start_date and end_date", () => {
    setPortfolioEVM([
      project({ id: "p1", name: "Alpha", start: "2025-01-01", end: "2025-03-01" }),
      project({ id: "p2", name: "Beta", start: "2025-02-01", end: "2025-04-01" }),
    ]);
    renderWidget("portfolio-gantt", {});

    expect(lastRows()).toHaveLength(2);
    expect(lastRows().map((r) => (r as { name: string }).name)).toEqual(
      expect.arrayContaining(["Alpha", "Beta"]),
    );
  });

  it("skips a project whose start_date OR end_date is null", () => {
    setPortfolioEVM([
      project({ id: "p1", name: "Dated", start: "2025-01-01", end: "2025-03-01" }),
      project({ id: "p2", name: "NoStart", start: null, end: "2025-03-01" }),
      project({ id: "p3", name: "NoEnd", start: "2025-01-01", end: null }),
      project({ id: "p4", name: "BothNull", start: null, end: null }),
    ]);
    renderWidget("portfolio-gantt", {});

    const names = lastRows().map((r) => (r as { name: string }).name);
    expect(names).toEqual(["Dated"]);
  });

  it("narrowing the portfolio status filter removes the project's bar", () => {
    setPortfolioEVM([
      project({ id: "p1", name: "Active", status: "active" }),
      project({ id: "p2", name: "Completed", status: "completed" }),
    ]);

    // Re-render with a status filter that excludes "active" → only Completed remains.
    const def = getWidgetDefinition(widgetTypeId("portfolio-gantt"))!;
    const Component = def.component;
    renderInPortfolio(
      <Component config={{}} instanceId="inst-1" isEditing={false} onRemove={vi.fn()} />,
      { controlDate: null, status: ["completed"], rag: null },
    );

    const names = lastRows().map((r) => (r as { name: string }).name);
    expect(names).toEqual(["Completed"]);
    expect(names).not.toContain("Active");
  });

  it("sorts the bars ascending by start date", () => {
    setPortfolioEVM([
      project({ id: "p1", name: "Late", start: "2025-06-01", end: "2025-09-01" }),
      project({ id: "p2", name: "Early", start: "2025-01-01", end: "2025-03-01" }),
      project({ id: "p3", name: "Mid", start: "2025-03-01", end: "2025-05-01" }),
    ]);
    renderWidget("portfolio-gantt", {});

    const names = lastRows().map((r) => (r as { name: string }).name);
    expect(names).toEqual(["Early", "Mid", "Late"]);
  });

  it("renders the empty-state placeholder when no projects have dates", () => {
    setPortfolioEVM([
      project({ id: "p1", name: "Undated", start: null, end: null }),
    ]);
    const { getByText } = renderWidget("portfolio-gantt", {});

    expect(getByText("No projects with start/end dates")).toBeInTheDocument();
    // Engine never invoked when there are no rows.
    expect(buildGanttOptionsMock).not.toHaveBeenCalled();
  });
});
