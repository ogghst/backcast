/**
 * Portfolio dashboard filter store (Zustand + immer).
 *
 * v1 slicers (locked decision, functional-analysis.md §13): Date + Status +
 * RAG only. BU/PM/customer columns exist backend-side but have NO slicer UI.
 *
 * State:
 *   - controlDate: EVM as-of ISO date (null = today / server default).
 *   - status:      subset of active/draft/completed/on_hold (null = no filter).
 *   - rag:         subset of Green/Amber/Red (null = no filter).
 *
 * URL persistence lives in the sibling `usePortfolioFilterUrlSync` hook
 * (uses the `key:val1,val2;...` serialize format shared with useTableParams).
 */

import { create } from "zustand";
import { immer } from "zustand/middleware/immer";

/** State + actions for the portfolio filter store. */
interface PortfolioFilterState {
  /** EVM control date (as-of) as an ISO date string; null = today. */
  controlDate: string | null;
  /** Selected project statuses; null = no status filter. */
  status: string[] | null;
  /** Selected RAG bands; null = no RAG filter. */
  rag: string[] | null;
  /** Set the EVM as-of control date (null clears it → today). */
  setControlDate: (d: string | null) => void;
  /** Set the status multi-select (null or empty = no filter). */
  setStatus: (s: string[] | null) => void;
  /** Set the RAG multi-select (null or empty = no filter). */
  setRag: (r: string[] | null) => void;
  /** Reset every filter to its default (cleared) state. */
  resetFilters: () => void;
}

export const usePortfolioFilterStore = create<PortfolioFilterState>()(
  immer((set) => ({
    controlDate: null,
    status: null,
    rag: null,

    setControlDate: (d) =>
      set((state) => {
        state.controlDate = d;
      }),

    setStatus: (s) =>
      set((state) => {
        // Treat an empty array the same as null (no filter) so downstream
        // checks can be a simple truthiness/null test.
        state.status = s && s.length > 0 ? s : null;
      }),

    setRag: (r) =>
      set((state) => {
        state.rag = r && r.length > 0 ? r : null;
      }),

    resetFilters: () =>
      set((state) => {
        state.controlDate = null;
        state.status = null;
        state.rag = null;
      }),
  })),
);
