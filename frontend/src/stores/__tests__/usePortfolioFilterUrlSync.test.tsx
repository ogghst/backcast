/**
 * Round-trip tests for the portfolio filter URL↔store sync hook.
 *
 * Idiom mirrors src/hooks/useTableParams.test.tsx: renderHook inside a
 * <MemoryRouter>, with a co-rendered probe (useLocation) to read back the
 * serialized URL. The store is a module singleton, so we reset it between
 * tests.
 */
import { describe, it, expect, beforeEach } from "vitest";
import { renderHook, act, waitFor } from "@testing-library/react";
import { MemoryRouter, Routes, Route, useLocation } from "react-router-dom";
import type { ReactNode } from "react";
import { usePortfolioFilterUrlSync } from "../usePortfolioFilterUrlSync";
import { usePortfolioFilterStore } from "../usePortfolioFilterStore";

// Read the store *during render* (not via getState) so the value under
// assertion is captured AFTER the hydration effect commits and triggers a
// re-render. getState() called synchronously right after renderHook would run
// before the effect flushes.
interface HarnessResult {
  search: string;
  controlDate: string | null;
  status: string[] | null;
  rag: string[] | null;
}

function useHarness(): HarnessResult {
  usePortfolioFilterUrlSync();
  return {
    search: useLocation().search,
    controlDate: usePortfolioFilterStore((s) => s.controlDate),
    status: usePortfolioFilterStore((s) => s.status),
    rag: usePortfolioFilterStore((s) => s.rag),
  };
}

// Wrapper that mounts the hook under test at /portfolio and exposes the
// location search via a sibling renderHook call.
function createWrapper(initialEntry: string) {
  return function Wrapper({ children }: { children: ReactNode }) {
    return (
      <MemoryRouter initialEntries={[initialEntry]}>
        <Routes>
          <Route path="/portfolio" element={children} />
        </Routes>
      </MemoryRouter>
    );
  };
}

// Reset the singleton store between tests so prior state cannot leak in.
beforeEach(() => {
  usePortfolioFilterStore.setState({
    controlDate: null,
    status: null,
    rag: null,
  });
});

describe("usePortfolioFilterUrlSync", () => {
  describe("URL → store hydration", () => {
    it("hydrates control_date + status + rag from the URL", async () => {
      const wrapper = createWrapper(
        "/portfolio?control_date=2026-06-28&filters=status:active;rag:Red",
      );

      const { result } = renderHook(() => useHarness(), { wrapper });

      await waitFor(() => expect(result.current.controlDate).toBe("2026-06-28"));
      expect(result.current.status).toEqual(["active"]);
      expect(result.current.rag).toEqual(["Red"]);
    });

    it("parses multi-value filters (key:val1,val2)", async () => {
      const wrapper = createWrapper(
        "/portfolio?filters=status:active,draft;rag:Green,Amber,Red",
      );

      const { result } = renderHook(() => useHarness(), { wrapper });

      await waitFor(() =>
        expect(result.current.status).toEqual(["active", "draft"]),
      );
      expect(result.current.rag).toEqual(["Green", "Amber", "Red"]);
    });

    it("leaves the store at nulls when the URL is clean", () => {
      const wrapper = createWrapper("/portfolio");

      const { result } = renderHook(() => useHarness(), { wrapper });

      expect(result.current.controlDate).toBeNull();
      expect(result.current.status).toBeNull();
      expect(result.current.rag).toBeNull();
    });
  });

  describe("store → URL persistence", () => {
    it("writes control_date to the URL when set from the store", () => {
      const wrapper = createWrapper("/portfolio");

      const { result } = renderHook(() => useHarness(), { wrapper });

      act(() => {
        usePortfolioFilterStore.getState().setControlDate("2026-07-01");
      });

      expect(result.current.search).toContain("control_date=2026-07-01");
    });

    it("serializes rag into the filters blob (key:val format)", () => {
      const wrapper = createWrapper("/portfolio");

      const { result } = renderHook(() => useHarness(), { wrapper });

      act(() => {
        usePortfolioFilterStore.getState().setRag(["Green"]);
      });

      expect(result.current.search).toContain("filters=rag%3AGreen");
    });

    it("serializes status + rag together in one filters blob", () => {
      const wrapper = createWrapper("/portfolio");

      const { result } = renderHook(() => useHarness(), { wrapper });

      act(() => {
        usePortfolioFilterStore.getState().setStatus(["active", "draft"]);
        usePortfolioFilterStore.getState().setRag(["Red", "Green"]);
      });

      // status comes before rag in the serialized order (see buildFiltersBlob).
      expect(result.current.search).toContain(
        "filters=status%3Aactive%2Cdraft%3Brag%3ARed%2CGreen",
      );
    });
  });

  describe("clearing filters", () => {
    it("removes the filters param when status is cleared to null", async () => {
      const wrapper = createWrapper("/portfolio?filters=status:active");

      const { result } = renderHook(() => useHarness(), { wrapper });

      // After hydration the store holds status=["active"], URL still carries it.
      await waitFor(() => expect(result.current.status).toEqual(["active"]));

      act(() => {
        usePortfolioFilterStore.getState().setStatus(null);
      });

      // The filters segment must be gone entirely — no stale "status:" remnant.
      expect(result.current.search).not.toContain("filters=");
      expect(result.current.search).not.toContain("status");
    });

    it("clears control_date from the URL when set back to null", async () => {
      const wrapper = createWrapper("/portfolio?control_date=2026-06-28");

      const { result } = renderHook(() => useHarness(), { wrapper });

      await waitFor(() =>
        expect(result.current.controlDate).toBe("2026-06-28"),
      );

      act(() => {
        usePortfolioFilterStore.getState().setControlDate(null);
      });

      expect(result.current.search).not.toContain("control_date=");
    });
  });

  describe("loop protection", () => {
    it("setting the same value twice does not throw and keeps the URL stable", () => {
      const wrapper = createWrapper("/portfolio");

      const { result } = renderHook(() => useHarness(), { wrapper });

      act(() => {
        usePortfolioFilterStore.getState().setRag(["Amber"]);
      });
      const first = result.current.search;

      // A no-op re-set of the same value: must not throw and must not drift.
      act(() => {
        usePortfolioFilterStore.getState().setRag(["Amber"]);
      });

      expect(result.current.search).toBe(first);
      expect(result.current.search).toContain("filters=rag%3AAmber");
    });
  });
});
