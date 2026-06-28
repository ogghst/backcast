/**
 * Client-side pagination tests for DistressList on PortfolioPage.
 *
 * Asserts the At-Risk (SPI<0.9) ranked list paginates instead of rendering
 * every row at once (production data has ~96 at-risk projects):
 *   - First page renders exactly `pageSize` (10) rows; an out-of-page name
 *     ("P15") is absent until page 2 is selected.
 *   - A `.ant-pagination` control renders only when `projects.length > pageSize`.
 *
 * The data hooks are mocked verbatim from PortfolioPage.role.test.tsx so the
 * test is purely about the pagination behavior, not data fetching.
 */

import { describe, it, expect, beforeEach, vi } from "vitest";
import { render, screen, fireEvent, within } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";
import { App as AntdApp } from "antd";
import type { ReactNode } from "react";

// ── Mocks ───────────────────────────────────────────────────────────────────

const useAuthStoreMock = vi.fn();
vi.mock("@/stores/useAuthStore", () => ({
  useAuthStore: (selector: (s: Record<string, unknown>) => unknown) =>
    useAuthStoreMock(selector),
}));

vi.mock("@/stores/usePortfolioFilterStore", () => ({
  usePortfolioFilterStore: vi.fn((selector: (s: Record<string, unknown>) => unknown) =>
    selector({ controlDate: null, status: null, rag: null }),
  ),
}));
vi.mock("@/stores/usePortfolioFilterUrlSync", () => ({
  usePortfolioFilterUrlSync: vi.fn(),
}));

// Default-role payload is configured per test via mockImplementation.
const usePortfolioEVMMock = vi.fn();
vi.mock("@/features/portfolio/api/usePortfolioEVM", () => ({
  usePortfolioEVM: () => usePortfolioEVMMock(),
}));

vi.mock("@/features/portfolio/api/usePortfolioCO", () => ({
  usePortfolioCO: () => ({ data: undefined, isLoading: false }),
}));

import { PortfolioPage } from "../PortfolioPage";

// ── Helpers ─────────────────────────────────────────────────────────────────

function setRole(role: string): void {
  useAuthStoreMock.mockImplementation(
    (selector: (s: Record<string, unknown>) => unknown) =>
      selector({ user: { id: "u1", email: "x@x", role } }),
  );
}

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

/**
 * Scope queries to the At-Risk section's ranked list.
 *
 * `projects` mirrors `at_risk_projects` in the mock payload, so the per-project
 * StandardTable also renders links named "P01".."PNN". Querying the whole
 * document would match both. The ranked list is the only `<ul>` inside the
 * at-risk section, so scoping to it isolates the distress-list rows.
 */
function atRiskList(): HTMLElement {
  const heading = screen.getByText(/At-Risk Projects/);
  const section = heading.closest("div")!;
  return section.querySelector("ul")!;
}

/**
 * The at-risk section's own container (the styled panel wrapping title + list
 * + optional pagination). Scoped pagination checks here avoid counting the
 * per-project StandardTable's own `.ant-pagination`.
 */
function atRiskSection(): HTMLElement {
  return screen.getByText(/At-Risk Projects/).closest("div")!;
}

function linkNamesIn(list: HTMLElement): string[] {
  return within(list)
    .getAllByRole("link")
    .map((a) => (a.textContent ?? "").trim());
}

function setPayload(atRiskCount: number): void {
  const atRisk = makeAtRiskProjects(atRiskCount);
  usePortfolioEVMMock.mockReturnValue({
    data: {
      summary: { cpi: 0.92, spi: 0.88, vac: -1000, tcpi: 1.05 },
      // Mirror at-risk into projects so the page's non-empty branch renders.
      projects: atRisk,
      at_risk_projects: atRisk,
    },
    isLoading: false,
  });
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

describe("PortfolioPage DistressList pagination", () => {
  beforeEach(() => {
    useAuthStoreMock.mockReset();
    usePortfolioEVMMock.mockReset();
    // manager → default layout, which includes the atRisk section.
    setRole("manager");
  });

  it("renders exactly pageSize (10) at-risk rows on page 1; P15 absent until page 2", () => {
    setPayload(15);
    renderPage();

    const names = linkNamesIn(atRiskList());
    // Exactly 10 rows render on page 1.
    expect(names).toHaveLength(10);
    // First-page name present; out-of-page name absent.
    expect(names).toContain("P01");
    expect(names).not.toContain("P15");

    // Pagination control exists in the at-risk section.
    expect(atRiskSection().querySelectorAll(".ant-pagination").length).toBe(1);

    // Go to page 2 → P15 now in view, P01 gone.
    const page2Btn = atRiskSection().querySelector('.ant-pagination-item[title="2"]')!;
    fireEvent.click(page2Btn);
    const page2Names = linkNamesIn(atRiskList());
    expect(page2Names).toContain("P15");
    expect(page2Names).not.toContain("P01");
  });

  it("hides pagination when at-risk count <= pageSize (2 projects)", () => {
    setPayload(2);
    renderPage();

    const names = linkNamesIn(atRiskList());
    expect(names).toEqual(["P01", "P02"]);
    // No pagination inside the at-risk section when count <= pageSize.
    expect(atRiskSection().querySelectorAll(".ant-pagination").length).toBe(0);
  });
});
