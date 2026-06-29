/**
 * Smoke test for GlobalDashboardPage (Phase 8).
 *
 * Full render is heavy (DashboardContextBus + react-grid-layout + FilterBar +
 * widget registry). The e2e covers the integrated path; here we just verify the
 * page mounts without throwing and wires the global path correctly
 * (useDashboardPersistence(undefined, undefined, role), portfolio scope + filter,
 * FilterBar rendered above the grid).
 */

import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { GlobalDashboardPage } from "../GlobalDashboardPage";

// --- Mocks ---------------------------------------------------------------

vi.mock("react-router-dom", () => ({
  useBlocker: () => ({ state: "unblocked" as const }),
}));

// Global-path persistence hook: capture args, return a stable save fn.
const persistenceArgs = vi.fn();
const saveMock = vi.fn();
vi.mock("../../api/useDashboardPersistence", () => ({
  useDashboardPersistence: (...args: unknown[]) => {
    persistenceArgs(args);
    return { save: saveMock, isSaving: false, isLoading: false };
  },
}));

// Stub the heavy children.
vi.mock("../../context/DashboardContextBus", () => ({
  DashboardContextBus: ({
    children,
    scope,
    portfolioFilter,
  }: {
    children: React.ReactNode;
    scope?: string;
    portfolioFilter?: { controlDate: string | null; status: string[] | null; rag: string[] | null };
  }) => (
    <div data-testid="bus" data-scope={scope} data-control-date={portfolioFilter?.controlDate ?? ""}>
      {children}
    </div>
  ),
}));

vi.mock("../../components/DashboardGrid", () => ({
  DashboardGrid: ({ onSave }: { onSave: () => void }) => (
    <button data-testid="grid" onClick={onSave}>
      grid
    </button>
  ),
}));

vi.mock("@/features/portfolio/components/FilterBar", () => ({
  FilterBar: () => <div data-testid="filterbar">filterbar</div>,
}));

// Auth store: expose a role.
vi.mock("@/stores/useAuthStore", () => ({
  useAuthStore: (selector: (s: { user: { role: string } | null }) => unknown) =>
    selector({ user: { role: "cost-controller" } }),
}));

// Portfolio filter store.
vi.mock("@/stores/usePortfolioFilterStore", () => ({
  usePortfolioFilterStore: (selector: (s: { controlDate: string | null; status: string[] | null; rag: string[] | null }) => unknown) =>
    selector({ controlDate: "2026-06-29", status: ["active"], rag: null }),
}));

vi.mock("@/stores/usePortfolioFilterUrlSync", () => ({
  usePortfolioFilterUrlSync: () => {},
}));

vi.mock("../../definitions/registerAll", () => ({
  registerAllWidgets: () => {},
}));

describe("GlobalDashboardPage (smoke)", () => {
  it("mounts and wires the global path (undefined pid + role + portfolio scope)", () => {
    render(<GlobalDashboardPage />);

    // FilterBar rendered above the grid.
    expect(screen.getByTestId("filterbar")).toBeInTheDocument();
    // Bus received portfolio scope + controlDate from the filter store.
    const bus = screen.getByTestId("bus");
    expect(bus).toHaveAttribute("data-scope", "portfolio");
    expect(bus).toHaveAttribute("data-control-date", "2026-06-29");
    // Grid mounted.
    expect(screen.getByTestId("grid")).toBeInTheDocument();

    // Persistence called with the global sentinel (undefined, never "").
    expect(persistenceArgs).toHaveBeenCalledTimes(1);
    const [pid, name, role] = persistenceArgs.mock.calls[0][0] as [unknown, unknown, unknown];
    expect(pid).toBeUndefined();
    expect(name).toBeUndefined();
    expect(role).toBe("cost-controller");
  });

  it("onSave from the grid routes to the persistence save fn", () => {
    render(<GlobalDashboardPage />);
    screen.getByTestId("grid").click();
    expect(saveMock).toHaveBeenCalledTimes(1);
  });
});
