import { useEffect, useRef } from "react";
import { useBlocker } from "react-router-dom";
import { Modal, Skeleton, theme } from "antd";
import { DashboardContextBus } from "../context/DashboardContextBus";
import { DashboardGrid } from "../components/DashboardGrid";
import { registerAllWidgets } from "../definitions/registerAll";
import { useDashboardPersistence } from "../api/useDashboardPersistence";
import { useDashboardCompositionStore } from "@/stores/useDashboardCompositionStore";
import { DashboardErrorBoundary } from "./DashboardErrorBoundary";
import { PageWrapper } from "@/components/layout/PageWrapper";
import { useAuthStore } from "@/stores/useAuthStore";
import { usePortfolioFilterStore } from "@/stores/usePortfolioFilterStore";
import { usePortfolioFilterUrlSync } from "@/stores/usePortfolioFilterUrlSync";
import { FilterBar } from "@/features/portfolio/components/FilterBar";

// Register all widget types into the global registry.
registerAllWidgets();

/**
 * Hosting page for the global (portfolio) widget dashboard.
 *
 * Route: `/portfolio` (gated by `portfolio-read`).
 *
 * Mirrors `DashboardPage` but with no projectId (the global sentinel is
 * `undefined`, NEVER "" — G6 cache-key split) and a portfolio scope + filter.
 * On first visit with no saved global layout, `useDashboardPersistence` clones
 * the user's role-default portfolio template (project_id=null, is_default=true).
 *
 * FilterBar is imported cross-feature from features/portfolio (Phase 10 will
 * relocate it to features/widgets — deferred).
 *
 * Navigation guards prevent data loss when navigating away with unsaved changes.
 *
 * NOTE: the beforeunload + useBlocker guard block below is duplicated VERBATIM
 * from DashboardPage.tsx (it keys on isDirty/isEditing, scope-agnostic). A
 * shared <DashboardHost> extraction is deferred to a later cleanup phase.
 */
export function GlobalDashboardPage() {
  const { token } = theme.useToken();
  const [modal, contextHolder] = Modal.useModal();

  // Role drives which role-tagged portfolio template is cloned on first visit.
  const role = useAuthStore((s) => s.user?.role) ?? null;

  // Composition store for dirty state and edit mode
  const isDirty = useDashboardCompositionStore((s) => s.isDirty);
  const isEditing = useDashboardCompositionStore((s) => s.isEditing);

  // Wire dashboard persistence -- global: projectId is undefined (G6), so
  // saveDashboard sends project_id: null (G7) and the cache key is
  // ["dashboard-layouts","list",undefined].
  const { save, isLoading } = useDashboardPersistence(
    undefined,
    undefined,
    role,
  );

  // Portfolio filter (controlDate/status/rag) from the store, pushed into the
  // context bus so portfolio widgets can read ctx.portfolioFilter.
  const controlDate = usePortfolioFilterStore((s) => s.controlDate);
  const status = usePortfolioFilterStore((s) => s.status);
  const rag = usePortfolioFilterStore((s) => s.rag);
  const portfolioFilter = { controlDate, status, rag };

  // URL <-> store sync mounted ONCE at the host level (same place PortfolioPage
  // mounted it). Never inside a widget.
  usePortfolioFilterUrlSync();

  // Browser-level navigation guard (refresh, close, back/forward buttons)
  useEffect(() => {
    const handleBeforeUnload = (e: BeforeUnloadEvent) => {
      if (isDirty || isEditing) {
        e.preventDefault();
        e.returnValue = ""; // Required for Chrome
      }
    };

    window.addEventListener("beforeunload", handleBeforeUnload);
    return () => window.removeEventListener("beforeunload", handleBeforeUnload);
  }, [isDirty, isEditing]);

  // React Router navigation guard (tab changes, programmatic navigation)
  const blocker = useBlocker(
    ({ currentLocation, nextLocation }) =>
      (isDirty || isEditing) && currentLocation.pathname !== nextLocation.pathname,
  );

  const modalShownRef = useRef(false);

  // Show confirmation modal when navigation is blocked
  useEffect(() => {
    if (blocker.state === "blocked" && !modalShownRef.current) {
      modalShownRef.current = true;

      if (isEditing) {
        modal.confirm({
          title: "Unsaved Changes",
          content: "You have unsaved changes to your dashboard. What would you like to do?",
          okText: "Discard and Leave",
          cancelText: "Stay and Save",
          okButtonProps: { danger: true },
          onOk: () => {
            useDashboardCompositionStore.getState().discardChanges();
            blocker.proceed();
          },
          onCancel: async () => {
            await save();
          },
          afterClose: () => {
            modalShownRef.current = false;
          },
        });
      } else {
        modal.confirm({
          title: "Unsaved Changes",
          content: "You have unsaved changes to your dashboard. What would you like to do?",
          okText: "Leave",
          cancelText: "Stay and Save",
          okButtonProps: { danger: true },
          onOk: () => {
            blocker.proceed();
          },
          onCancel: async () => {
            await save();
          },
          afterClose: () => {
            modalShownRef.current = false;
          },
        });
      }
    }
    if (blocker.state !== "blocked") {
      modalShownRef.current = false;
    }
  }, [blocker, modal, save, isEditing]);

  return (
    <DashboardErrorBoundary>
      {contextHolder}
      <DashboardContextBus scope="portfolio" portfolioFilter={portfolioFilter}>
        <PageWrapper>
          <FilterBar />
          {isLoading ? (
            <div style={{ display: "flex", flexDirection: "column", gap: token.paddingMD }}>
              <Skeleton.Input active block style={{ height: 48 }} />
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: token.paddingMD }}>
                <Skeleton active paragraph={{ rows: 4 }} style={{ height: 200 }} />
                <Skeleton active paragraph={{ rows: 4 }} style={{ height: 200 }} />
              </div>
            </div>
          ) : (
            <DashboardGrid onSave={save} />
          )}
        </PageWrapper>
      </DashboardContextBus>
    </DashboardErrorBoundary>
  );
}
