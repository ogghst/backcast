import { describe, it, expect, beforeEach } from "vitest";
import { usePortfolioFilterStore } from "../usePortfolioFilterStore";

// The store is a module-level singleton — reset between tests so order does
// not matter and a prior test's mutations can't leak in.
beforeEach(() => {
  usePortfolioFilterStore.setState({
    controlDate: null,
    status: null,
    rag: null,
  });
});

describe("usePortfolioFilterStore", () => {
  describe("initial state", () => {
    it("starts with every filter cleared (null)", () => {
      const state = usePortfolioFilterStore.getState();
      expect(state.controlDate).toBeNull();
      expect(state.status).toBeNull();
      expect(state.rag).toBeNull();
    });
  });

  describe("setControlDate", () => {
    it("sets and then clears the control date", () => {
      usePortfolioFilterStore.getState().setControlDate("2026-06-28");
      expect(usePortfolioFilterStore.getState().controlDate).toBe("2026-06-28");

      usePortfolioFilterStore.getState().setControlDate(null);
      expect(usePortfolioFilterStore.getState().controlDate).toBeNull();
    });
  });

  describe("setStatus", () => {
    it("sets a multi-select status list", () => {
      usePortfolioFilterStore.getState().setStatus(["active", "draft"]);
      expect(usePortfolioFilterStore.getState().status).toEqual([
        "active",
        "draft",
      ]);
    });

    it("clears back to null when passed null", () => {
      usePortfolioFilterStore.getState().setStatus(["active"]);
      usePortfolioFilterStore.getState().setStatus(null);
      expect(usePortfolioFilterStore.getState().status).toBeNull();
    });

    it("treats an empty array the same as null (no filter)", () => {
      usePortfolioFilterStore.getState().setStatus([]);
      expect(usePortfolioFilterStore.getState().status).toBeNull();
    });
  });

  describe("setRag", () => {
    it("sets a multi-select RAG list", () => {
      usePortfolioFilterStore.getState().setRag(["Green", "Red"]);
      expect(usePortfolioFilterStore.getState().rag).toEqual(["Green", "Red"]);
    });

    it("clears back to null when passed null", () => {
      usePortfolioFilterStore.getState().setRag(["Amber"]);
      usePortfolioFilterStore.getState().setRag(null);
      expect(usePortfolioFilterStore.getState().rag).toBeNull();
    });

    it("treats an empty array the same as null (no filter)", () => {
      usePortfolioFilterStore.getState().setRag([]);
      expect(usePortfolioFilterStore.getState().rag).toBeNull();
    });
  });

  describe("resetFilters", () => {
    it("returns every filter to null after they have been set", () => {
      usePortfolioFilterStore.getState().setControlDate("2026-01-01");
      usePortfolioFilterStore.getState().setStatus(["active", "completed"]);
      usePortfolioFilterStore.getState().setRag(["Red"]);

      usePortfolioFilterStore.getState().resetFilters();

      const state = usePortfolioFilterStore.getState();
      expect(state.controlDate).toBeNull();
      expect(state.status).toBeNull();
      expect(state.rag).toBeNull();
    });

    it("resets each field independently (controlDate)", () => {
      usePortfolioFilterStore.getState().setControlDate("2026-02-02");
      usePortfolioFilterStore.getState().resetFilters();
      expect(usePortfolioFilterStore.getState().controlDate).toBeNull();
    });

    it("resets each field independently (status)", () => {
      usePortfolioFilterStore.getState().setStatus(["draft"]);
      usePortfolioFilterStore.getState().resetFilters();
      expect(usePortfolioFilterStore.getState().status).toBeNull();
    });

    it("resets each field independently (rag)", () => {
      usePortfolioFilterStore.getState().setRag(["Amber"]);
      usePortfolioFilterStore.getState().resetFilters();
      expect(usePortfolioFilterStore.getState().rag).toBeNull();
    });
  });

  describe("action isolation", () => {
    it("setStatus does not touch controlDate", () => {
      usePortfolioFilterStore.getState().setControlDate("2026-03-03");
      usePortfolioFilterStore.getState().setStatus(["active"]);
      expect(usePortfolioFilterStore.getState().controlDate).toBe("2026-03-03");
    });

    it("setRag does not touch status or controlDate", () => {
      usePortfolioFilterStore.getState().setControlDate("2026-04-04");
      usePortfolioFilterStore.getState().setStatus(["active", "draft"]);
      usePortfolioFilterStore.getState().setRag(["Green"]);
      expect(usePortfolioFilterStore.getState().controlDate).toBe("2026-04-04");
      expect(usePortfolioFilterStore.getState().status).toEqual([
        "active",
        "draft",
      ]);
    });

    it("setControlDate does not touch status or rag", () => {
      usePortfolioFilterStore.getState().setStatus(["active"]);
      usePortfolioFilterStore.getState().setRag(["Red"]);
      usePortfolioFilterStore.getState().setControlDate("2026-05-05");
      expect(usePortfolioFilterStore.getState().status).toEqual(["active"]);
      expect(usePortfolioFilterStore.getState().rag).toEqual(["Red"]);
    });
  });

  describe("immutability", () => {
    it("setControlDate produces a new state value (consumer-visible change)", () => {
      const before = usePortfolioFilterStore.getState().controlDate;
      usePortfolioFilterStore.getState().setControlDate("2026-06-06");
      expect(usePortfolioFilterStore.getState().controlDate).not.toBe(before);
    });

    it("setStatus produces a new state value (consumer-visible change)", () => {
      const before = usePortfolioFilterStore.getState().status;
      usePortfolioFilterStore.getState().setStatus(["active"]);
      expect(usePortfolioFilterStore.getState().status).not.toBe(before);
    });
  });
});
