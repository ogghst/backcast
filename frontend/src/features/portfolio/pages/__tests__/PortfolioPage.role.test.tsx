/**
 * Role-curation tests for PortfolioPage (Phase 2).
 *
 * Asserts the page heading + lead KPI tiles change with the authenticated
 * user's role:
 *   - default         → "Portfolio Dashboard" + CPI/SPI/VAC/TCPI
 *   - cost-controller → "Cost Controlling" + Portfolio CPI + Cost Distress count
 *   - pmo-director    → "PMO / Schedule Governance" + Portfolio SPI + At-Risk count
 *
 * The data hooks are mocked so the test is purely about role-driven layout,
 * not the (unchanged) data-fetching behavior.
 */

import { describe, it, expect, beforeEach, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";
import { App as AntdApp } from "antd";
import type { ReactNode } from "react";

// ── Mocks ───────────────────────────────────────────────────────────────────
//
// `useAuthStore` is mocked per-role inside each test via mockReturnValue.
// The real store's selector-style call (`useAuthStore((s) => ...)`) is honored
// by passing the selector the curated state.

const useAuthStoreMock = vi.fn();
vi.mock("@/stores/useAuthStore", () => ({
  useAuthStore: (selector: (s: Record<string, unknown>) => unknown) =>
    useAuthStoreMock(selector),
}));

// Filter store + URL sync are no-ops here; the role test does not vary filters.
vi.mock("@/stores/usePortfolioFilterStore", () => ({
  usePortfolioFilterStore: vi.fn((selector: (s: Record<string, unknown>) => unknown) =>
    selector({ controlDate: null, status: null, rag: null }),
  ),
}));
vi.mock("@/stores/usePortfolioFilterUrlSync", () => ({
  usePortfolioFilterUrlSync: vi.fn(),
}));

// Deterministic portfolio data. Includes one CPI-distress and one SPI-distress
// project so both distress tiles render a count > 0.
vi.mock("@/features/portfolio/api/usePortfolioEVM", () => ({
  usePortfolioEVM: () => ({
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
  }),
}));

vi.mock("@/features/portfolio/api/usePortfolioCO", () => ({
  usePortfolioCO: () => ({ data: undefined, isLoading: false }),
}));

import { PortfolioPage } from "../PortfolioPage";

function setRole(role: string): void {
  useAuthStoreMock.mockImplementation(
    (selector: (s: Record<string, unknown>) => unknown) =>
      selector({ user: { id: "u1", email: "x@x", role } }),
  );
}

function renderPage(): void {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });

  const Wrapper = ({ children }: { children: ReactNode }) => (
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>
        <AntdApp>{children}</AntdApp>
      </MemoryRouter>
    </QueryClientProvider>
  );

  render(<PortfolioPage />, { wrapper: Wrapper });
}

/**
 * Grab the lead KPI tile labels in render order.
 *
 * `MetricCard` renders its name as the prefix of the Card's `aria-label`
 * ("{name}: {value}"), while the distress-count tile is a raw antd `Statistic`
 * whose title sits in `.ant-statistic-title`. Collect from both so the helper
 * works regardless of which tile type the row contains.
 *
 * Scoped to the first `.ant-row` (the KPI row) so the CO-pipeline / table
 * statistics rendered further down are excluded.
 */
function leadTileTitles(): string[] {
  const firstRow = document.querySelector(".ant-row");
  const scope = firstRow ?? document;

  const titles: string[] = [];

  // MetricCard tiles — name is the prefix of the Card's aria-label.
  scope.querySelectorAll<HTMLElement>("[aria-label]").forEach((el) => {
    const label = el.getAttribute("aria-label") ?? "";
    const name = label.split(":")[0].trim();
    if (name) titles.push(name);
  });

  // Distress-count tile — antd Statistic title.
  scope
    .querySelectorAll(".ant-statistic-title")
    .forEach((el) => titles.push((el.textContent ?? "").trim()));

  return titles;
}

describe("PortfolioPage role-curation", () => {
  beforeEach(() => {
    useAuthStoreMock.mockReset();
  });

  it("default role → 'Portfolio Dashboard' heading with CPI/SPI/VAC/TCPI lead tiles", () => {
    setRole("manager"); // manager → default layout
    renderPage();

    const heading = screen.getByRole("heading", {
      level: 1,
      name: "Portfolio Dashboard",
    });
    expect(heading).toBeInTheDocument();

    const titles = leadTileTitles();
    expect(titles).toEqual(
      expect.arrayContaining([
        "Portfolio CPI",
        "Portfolio SPI",
        "Portfolio VAC",
        "Portfolio TCPI",
      ]),
    );
    // default layout never shows a distress count tile
    expect(titles).not.toContain("Cost Distress (CPI < 0.9)");
    expect(titles).not.toContain("At-Risk (SPI < 0.9)");
  });

  it("cost-controller → 'Cost Controlling' heading with Portfolio CPI lead + Cost Distress count", () => {
    setRole("cost-controller");
    renderPage();

    expect(
      screen.getByRole("heading", { level: 1, name: "Cost Controlling" }),
    ).toBeInTheDocument();

    const titles = leadTileTitles();
    expect(titles).toContain("Portfolio CPI");
    expect(titles).toContain("Cost Distress (CPI < 0.9)");
    // cost-controller does NOT lead with the full quad
    expect(titles).not.toContain("Portfolio VAC");
    expect(titles).not.toContain("Portfolio TCPI");
  });

  it("pmo-director → 'PMO / Schedule Governance' heading with Portfolio SPI lead + At-Risk count", () => {
    setRole("pmo-director");
    renderPage();

    expect(
      screen.getByRole("heading", {
        level: 1,
        name: "PMO / Schedule Governance",
      }),
    ).toBeInTheDocument();

    const titles = leadTileTitles();
    expect(titles).toContain("Portfolio SPI");
    expect(titles).toContain("At-Risk (SPI < 0.9)");
    // pmo-director does NOT lead with CPI/VAC/TCPI
    expect(titles).not.toContain("Portfolio CPI");
    expect(titles).not.toContain("Portfolio VAC");
  });

  it("cost-controller and pmo-director produce DIFFERENT headings + lead tiles", () => {
    setRole("cost-controller");
    const { unmount: unmount1 } = render(
      <PortfolioPage />,
      {
        wrapper: ({ children }: { children: ReactNode }) => (
          <QueryClientProvider client={new QueryClient()}>
            <MemoryRouter>
              <AntdApp>{children}</AntdApp>
            </MemoryRouter>
          </QueryClientProvider>
        ),
      },
    );
    const ccHeading = screen.getByRole("heading", { level: 1 }).textContent;
    const ccTitles = leadTileTitles();
    unmount1();

    setRole("pmo-director");
    render(
      <PortfolioPage />,
      {
        wrapper: ({ children }: { children: ReactNode }) => (
          <QueryClientProvider client={new QueryClient()}>
            <MemoryRouter>
              <AntdApp>{children}</AntdApp>
            </MemoryRouter>
          </QueryClientProvider>
        ),
      },
    );
    const pmoHeading = screen.getByRole("heading", { level: 1 }).textContent;
    const pmoTitles = leadTileTitles();

    expect(ccHeading).not.toBe(pmoHeading);
    expect(ccTitles).not.toEqual(pmoTitles);
  });
});
