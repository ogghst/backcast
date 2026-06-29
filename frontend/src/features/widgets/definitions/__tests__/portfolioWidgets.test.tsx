/**
 * Phase 4 render tests for the 4 portfolio-scope widgets.
 *
 * Each widget is rendered inside a portfolio-scope `DashboardContextBus` (so
 * `scope` + `portfolioFilter` flow through the real context, matching how the
 * Phase-8 `GlobalDashboardPage` will host them). The data hooks are mocked with
 * deterministic payloads — these tests are about rendering + pagination, not
 * data fetching.
 *
 * Design doc §7 Phase 4 verify: "25 widgets registered; each renders in a
 * portfolio-scope harness with mocked hooks; pagination lives in the distress
 * widget."
 */

import { describe, it, expect, beforeEach, vi } from "vitest";
import { render, screen, fireEvent, within } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";
import { App as AntdApp } from "antd";
import type { ReactNode } from "react";

// ── Mocks ───────────────────────────────────────────────────────────────────
//
// `DashboardContextBus` consumes TimeMachineContext internally; mock it the same
// way DashboardContextBus.test.tsx does (lighter than mounting TimeMachineProvider).
vi.mock("@/contexts/TimeMachineContext", () => ({
  useTimeMachine: () => ({
    asOf: undefined,
    branch: "main",
    mode: "merged",
    isHistorical: false,
    invalidateQueries: vi.fn(),
  }),
}));

// Deterministic portfolio data. Shared default; per-test overrides via
// `setPortfolioEVM` / `setPortfolioCO`.
const usePortfolioEVMMock = vi.fn();
vi.mock("@/features/portfolio/api/usePortfolioEVM", () => ({
  usePortfolioEVM: () => usePortfolioEVMMock(),
}));

const usePortfolioCOMock = vi.fn();
vi.mock("@/features/portfolio/api/usePortfolioCO", () => ({
  usePortfolioCO: () => usePortfolioCOMock(),
}));

// Import the definitions AFTER mocks are registered so the registry picks up
// the side-effecting registerWidget() calls via registerAll.
import "@/features/widgets/definitions/registerAll";
import { getAllWidgetDefinitions, getWidgetDefinition } from "../..";
import { widgetTypeId } from "../../types";
import { DashboardContextBus } from "../../context/DashboardContextBus";

// ── Helpers ─────────────────────────────────────────────────────────────────

/** Default portfolio EVM payload — 2 projects, summary quad, 1 at-risk. */
function defaultEVMPayload() {
  return {
    data: {
      summary: { cpi: 0.92, spi: 0.88, vac: -1000, tcpi: 1.05 },
      projects: [
        {
          project_id: "p1",
          name: "Alpha",
          status: "active",
          cpi: 0.8,
          spi: 1.0,
          vac: -100,
          contract_value: 1000,
          bac: 1000,
          currency: "EUR",
          at_risk: false,
        },
        {
          project_id: "p2",
          name: "Beta",
          status: "active",
          cpi: 1.0,
          spi: 0.85,
          vac: 50,
          contract_value: 2000,
          bac: 2000,
          currency: "EUR",
          at_risk: true,
        },
      ],
      at_risk_projects: [
        {
          project_id: "p2",
          name: "Beta",
          status: "active",
          cpi: 1.0,
          spi: 0.85,
          vac: 50,
          contract_value: 2000,
          bac: 2000,
          currency: "EUR",
          at_risk: true,
        },
      ],
    },
    isLoading: false,
    error: null,
    refetch: vi.fn(),
  };
}

function defaultCOPayload() {
  return {
    data: {
      total_count: 5,
      pending_value: 12000,
      approved_value: 8000,
      total_cost_exposure: 20000,
      aging_threshold_days: 7,
      by_status: [
        { status: "Pending", count: 3 },
        { status: "Approved", count: 2 },
      ],
      aging_items: [{ id: "x" }],
    },
    isLoading: false,
    error: null,
    refetch: vi.fn(),
  };
}

function setPortfolioEVM(payload = defaultEVMPayload()) {
  usePortfolioEVMMock.mockReturnValue(payload);
}
function setPortfolioCO(payload = defaultCOPayload()) {
  usePortfolioCOMock.mockReturnValue(payload);
}

/** Portfolio-scope harness: real context provider with projectId="" + filter. */
function renderInPortfolio(ui: ReactNode) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });

  const Wrapper = ({ children }: { children: ReactNode }) => (
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>
        <AntdApp>
          <DashboardContextBus
            scope="portfolio"
            portfolioFilter={{ controlDate: null, status: null, rag: null }}
          >
            {children}
          </DashboardContextBus>
        </AntdApp>
      </MemoryRouter>
    </QueryClientProvider>
  );

  return render(<div style={{ height: 400 }}>{ui}</div>, { wrapper: Wrapper });
}

/** Look up a widget's render component and invoke it directly (registry-driven). */
function renderWidget(
  typeIdStr: string,
  config: Record<string, unknown>,
  instanceId = "inst-1",
) {
  const def = getWidgetDefinition(widgetTypeId(typeIdStr));
  if (!def) throw new Error(`widget ${typeIdStr} not registered`);
  const Component = def.component;
  return renderInPortfolio(
    <Component
      config={config}
      instanceId={instanceId}
      isEditing={false}
      onRemove={vi.fn()}
    />,
  );
}

// ── Tests ───────────────────────────────────────────────────────────────────

describe("portfolio widgets — registry", () => {
  beforeEach(() => {
    usePortfolioEVMMock.mockReset();
    usePortfolioCOMock.mockReset();
    setPortfolioEVM();
    setPortfolioCO();
  });

  it("registers exactly 25 widget definitions (21 project + 4 portfolio)", () => {
    expect(getAllWidgetDefinitions()).toHaveLength(25);
  });

  it("registers all 4 portfolio widgets with scope:'portfolio'", () => {
    const portfolioIds = [
      "portfolio-kpi",
      "portfolio-projects-table",
      "portfolio-co-pipeline",
      "portfolio-distress-list",
    ];
    for (const id of portfolioIds) {
      const def = getWidgetDefinition(widgetTypeId(id));
      expect(def, `${id} should be registered`).toBeDefined();
      expect(def?.scope).toBe("portfolio");
    }
  });

  it("all 4 portfolio widgets gate on portfolio-read (F-7/G14: portfolio-co-pipeline matches its data route)", () => {
    for (const id of [
      "portfolio-kpi",
      "portfolio-projects-table",
      "portfolio-co-pipeline",
      "portfolio-distress-list",
    ]) {
      expect(
        getWidgetDefinition(widgetTypeId(id))?.requiredPermission,
      ).toBe("portfolio-read");
    }
  });
});

describe("PortfolioKpiWidget", () => {
  beforeEach(() => {
    usePortfolioEVMMock.mockReset();
    usePortfolioCOMock.mockReset();
    setPortfolioEVM();
    setPortfolioCO();
  });

  it("renders the configured MetricCards (default quad) and no distress tile", () => {
    renderWidget("portfolio-kpi", {
      metrics: ["cpi", "spi", "vac", "tcpi"],
      showDistressCount: "none",
    });

    // MetricCard renders its name as the prefix of the Card aria-label
    // ("{name}: {value}"). Filter to that ": " separator to exclude the
    // WidgetShell trigger button (aria-label = widget title).
    const cardLabels = Array.from(document.querySelectorAll("[aria-label]"))
      .map((el) => el.getAttribute("aria-label") ?? "")
      .filter((label) => label.includes(": "))
      .map((label) => label.split(":")[0].trim());
    expect(cardLabels).toEqual(
      expect.arrayContaining([
        "Portfolio CPI",
        "Portfolio SPI",
        "Portfolio VAC",
        "Portfolio TCPI",
      ]),
    );
    expect(cardLabels).not.toContain("Cost Distress (CPI < 0.9)");
  });

  it("renders only the configured metric subset", () => {
    renderWidget("portfolio-kpi", {
      metrics: ["cpi"],
      showDistressCount: "none",
    });

    // MetricCard cards render aria-label as "{name}: {value}". Exclude the
    // WidgetShell trigger button (aria-label = widget title "Portfolio KPIs")
    // by requiring the ": " value separator that only MetricCard uses.
    const cardLabels = Array.from(document.querySelectorAll("[aria-label]"))
      .map((el) => el.getAttribute("aria-label") ?? "")
      .filter((label) => label.includes(": "))
      .map((label) => label.split(":")[0].trim());
    expect(cardLabels).toEqual(["Portfolio CPI"]);
  });

  it("renders the cost-distress count tile when showDistressCount === 'cost'", () => {
    renderWidget("portfolio-kpi", {
      metrics: ["cpi"],
      showDistressCount: "cost",
    });

    // Alpha has cpi 0.8 (< 0.9) → cost-distress count = 1.
    expect(
      screen.getAllByText("Cost Distress (CPI < 0.9)").length,
    ).toBeGreaterThan(0);
  });

  it("renders the schedule-distress count tile when showDistressCount === 'schedule'", () => {
    renderWidget("portfolio-kpi", {
      metrics: ["spi"],
      showDistressCount: "schedule",
    });

    expect(
      screen.getAllByText("At-Risk (SPI < 0.9)").length,
    ).toBeGreaterThan(0);
  });
});

describe("PortfolioProjectsTableWidget", () => {
  beforeEach(() => {
    usePortfolioEVMMock.mockReset();
    usePortfolioCOMock.mockReset();
    setPortfolioEVM();
    setPortfolioCO();
  });

  it("renders the StandardTable with project rows; a known project name appears", () => {
    renderWidget("portfolio-projects-table", {});

    // The known project name renders as a link.
    expect(screen.getByRole("link", { name: "Alpha" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Beta" })).toBeInTheDocument();
  });

  it("respects a status filter carried in portfolioFilter (filtered out)", () => {
    // Re-render with a status filter that excludes "active" → no Alpha/Beta links.
    const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });
    const def = getWidgetDefinition(widgetTypeId("portfolio-projects-table"))!;
    const Component = def.component;

    render(
      <QueryClientProvider client={queryClient}>
        <MemoryRouter>
          <AntdApp>
            <DashboardContextBus
              scope="portfolio"
              portfolioFilter={{
                controlDate: null,
                status: ["completed"],
                rag: null,
              }}
            >
              <div style={{ height: 400 }}>
                <Component
                  config={{}}
                  instanceId="inst-1"
                  isEditing={false}
                  onRemove={vi.fn()}
                />
              </div>
            </DashboardContextBus>
          </AntdApp>
        </MemoryRouter>
      </QueryClientProvider>,
    );

    expect(screen.queryByRole("link", { name: "Alpha" })).toBeNull();
  });
});

describe("PortfolioChangeOrderPipelineWidget", () => {
  beforeEach(() => {
    usePortfolioEVMMock.mockReset();
    usePortfolioCOMock.mockReset();
    setPortfolioEVM();
    setPortfolioCO();
  });

  it("renders the 5 Statistic titles (Open COs, Pending Value, Approved Value, Cost Exposure, Aging)", () => {
    renderWidget("portfolio-co-pipeline", { agingThresholdDays: 7 });

    for (const title of [
      "Open COs",
      "Pending Value",
      "Approved Value",
      "Cost Exposure",
      "Aging (> 7d)",
    ]) {
      expect(
        screen.getAllByText(title).length,
        `${title} should render`,
      ).toBeGreaterThan(0);
    }
  });
});

describe("PortfolioDistressListWidget", () => {
  /** Build N at-risk projects named "P01".."P{N}", each with spi: 0.8, cpi: 1.0. */
  function makeAtRiskProjects(n: number) {
    return Array.from({ length: n }, (_, i) => {
      const id = String(i + 1).padStart(2, "0");
      return {
        project_id: `p${id}`,
        name: `P${id}`,
        status: "active",
        cpi: 1.0,
        spi: 0.8,
        vac: 0,
        contract_value: 1000,
        bac: 1000,
        currency: "EUR",
        at_risk: true,
      };
    });
  }

  function setPayload(atRiskCount: number) {
    const atRisk = makeAtRiskProjects(atRiskCount);
    usePortfolioEVMMock.mockReturnValue({
      data: {
        summary: { cpi: 0.92, spi: 0.88, vac: -1000, tcpi: 1.05 },
        projects: atRisk,
        at_risk_projects: atRisk,
      },
      isLoading: false,
      error: null,
      refetch: vi.fn(),
    });
  }

  /** The distress widget renders exactly one <ul> inside WidgetShell. */
  function distressList(): HTMLElement {
    return document.querySelector("ul")!;
  }

  function linkNamesIn(list: HTMLElement): string[] {
    return within(list)
      .getAllByRole("link")
      .map((a) => (a.textContent ?? "").trim());
  }

  beforeEach(() => {
    usePortfolioEVMMock.mockReset();
    usePortfolioCOMock.mockReset();
  });

  it("schedule mode: page 1 renders exactly pageSize (10) rows; P15 absent until page 2", () => {
    setPayload(15);
    renderWidget("portfolio-distress-list", {
      mode: "schedule",
      pageSize: 10,
    });

    const names = linkNamesIn(distressList());
    expect(names).toHaveLength(10);
    expect(names).toContain("P01");
    expect(names).not.toContain("P15");

    // Pagination control renders (projects.length > pageSize).
    expect(document.querySelectorAll(".ant-pagination").length).toBe(1);

    // Go to page 2 → P15 now in view, P01 gone.
    const page2 = document.querySelector('.ant-pagination-item[title="2"]')!;
    fireEvent.click(page2);
    const page2Names = linkNamesIn(distressList());
    expect(page2Names).toContain("P15");
    expect(page2Names).not.toContain("P01");
  });

  it("schedule mode: hides pagination when count <= pageSize", () => {
    setPayload(2);
    renderWidget("portfolio-distress-list", {
      mode: "schedule",
      pageSize: 10,
    });

    expect(linkNamesIn(distressList())).toEqual(["P01", "P02"]);
    expect(document.querySelectorAll(".ant-pagination").length).toBe(0);
  });

  it("cost mode: derives the list from cpiCostDistress (CPI < 0.9)", () => {
    // Two projects: one cost-distressed (cpi 0.8), one healthy (cpi 1.0).
    usePortfolioEVMMock.mockReturnValue({
      data: {
        summary: { cpi: 0.92, spi: 0.88, vac: -1000, tcpi: 1.05 },
        projects: [
          {
            project_id: "c1",
            name: "CostBad",
            status: "active",
            cpi: 0.8,
            spi: 1.0,
            vac: 0,
            contract_value: 1000,
            bac: 1000,
            currency: "EUR",
            at_risk: false,
          },
          {
            project_id: "c2",
            name: "CostOk",
            status: "active",
            cpi: 1.0,
            spi: 1.0,
            vac: 0,
            contract_value: 1000,
            bac: 1000,
            currency: "EUR",
            at_risk: false,
          },
        ],
        at_risk_projects: [],
      },
      isLoading: false,
      error: null,
      refetch: vi.fn(),
    });

    renderWidget("portfolio-distress-list", {
      mode: "cost",
      pageSize: 10,
    });

    const names = linkNamesIn(distressList());
    expect(names).toEqual(["CostBad"]);
  });
});
