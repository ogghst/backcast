/**
 * Two-way URL ↔ store sync for the portfolio filter store.
 *
 * Serialize format mirrors `useTableParams` (`key:val1,val2;...`):
 *   - control_date=<ISO date>   (scalar; omitted = today)
 *   - filters=control_date:<iso>;status:<a,b>;rag:<Green,Red>
 *
 * The whole `filters` blob is used (rather than bespoke top-level params) so
 * the portfolio page composes cleanly with `useTableParams` for the table's
 * own pagination/sort state without colliding on `page`/`per_page`.
 *
 * Loop avoidance: store→URL writes use `replace: true` and only fire when the
 * serialized filter payload actually changes; URL→store hydration only fires
 * set* when the parsed value differs from the current store value.
 */

import { useEffect, useRef } from "react";
import { useSearchParams } from "react-router-dom";
import { usePortfolioFilterStore } from "@/stores/usePortfolioFilterStore";

/** Parse the `filters` blob (`key:val1,val2;key2:val3`) into a map. */
function parseFiltersBlob(blob: string | null): Record<string, string[]> {
  const out: Record<string, string[]> = {};
  if (!blob) return out;
  blob.split(";").forEach((part) => {
    const [key, valStr] = part.split(":");
    if (key && valStr) {
      out[key] = valStr.split(",").filter(Boolean);
    }
  });
  return out;
}

/** Build a `filters` blob from the store state (control_date omitted here). */
function buildFiltersBlob(
  status: string[] | null,
  rag: string[] | null,
): string | null {
  const parts: string[] = [];
  if (status && status.length > 0) parts.push(`status:${status.join(",")}`);
  if (rag && rag.length > 0) parts.push(`rag:${rag.join(",")}`);
  return parts.length > 0 ? parts.join(";") : null;
}

/**
 * Wire the portfolio filter store to the URL search params. Call once on the
 * PortfolioPage (or a child that is always mounted while the page is shown).
 */
export function usePortfolioFilterUrlSync(): void {
  const [searchParams, setSearchParams] = useSearchParams();

  const controlDate = usePortfolioFilterStore((s) => s.controlDate);
  const status = usePortfolioFilterStore((s) => s.status);
  const rag = usePortfolioFilterStore((s) => s.rag);
  const setControlDate = usePortfolioFilterStore((s) => s.setControlDate);
  const setStatus = usePortfolioFilterStore((s) => s.setStatus);
  const setRag = usePortfolioFilterStore((s) => s.setRag);

  // The store→URL effect would otherwise clobber the URL on the first commit
  // (its closure still sees the pre-hydration null store values, so it deletes
  // the very params the hydration effect is trying to load). Suppress the first
  // store→URL write so the URL→store hydration wins on mount; subsequent
  // changes flow both ways normally.
  const hydratedRef = useRef(false);

  // URL → store: hydrate on mount and whenever the search params change.
  useEffect(() => {
    const urlControlDate = searchParams.get("control_date");
    const blob = parseFiltersBlob(searchParams.get("filters"));
    const urlStatus = blob.status ?? null;
    const urlRag = blob.rag ?? null;

    if ((urlControlDate ?? null) !== (controlDate ?? null)) {
      setControlDate(urlControlDate);
    }
    const curStatus = status ?? null;
    const sameStatus =
      (urlStatus === null && curStatus === null) ||
      (urlStatus !== null &&
        curStatus !== null &&
        urlStatus.length === curStatus.length &&
        urlStatus.every((v, i) => v === curStatus[i]));
    if (!sameStatus) setStatus(urlStatus);

    const curRag = rag ?? null;
    const sameRag =
      (urlRag === null && curRag === null) ||
      (urlRag !== null &&
        curRag !== null &&
        urlRag.length === curRag.length &&
        urlRag.every((v, i) => v === curRag[i]));
    if (!sameRag) setRag(urlRag);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [searchParams]);

  // Store → URL: persist changes back (replace, not push — filters are not
  // navigation history steps the user expects to step through). Skipped on the
  // very first commit so the hydration effect above can settle first.
  useEffect(() => {
    if (!hydratedRef.current) {
      hydratedRef.current = true;
      return;
    }
    const next = new URLSearchParams(searchParams);
    if (controlDate) {
      next.set("control_date", controlDate);
    } else {
      next.delete("control_date");
    }
    const blob = buildFiltersBlob(status, rag);
    if (blob) {
      next.set("filters", blob);
    } else {
      next.delete("filters");
    }
    // Only write when something actually changed, to avoid clobbering
    // unrelated params or triggering spurious history entries.
    const nextStr = next.toString();
    const curStr = searchParams.toString();
    if (nextStr !== curStr) {
      setSearchParams(next, { replace: true });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [controlDate, status, rag]);
}
