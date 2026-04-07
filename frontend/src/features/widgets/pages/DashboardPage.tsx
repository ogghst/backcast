import { useEffect, useRef } from "react";
import { useParams, useBlocker } from "react-router-dom";
import { Modal, Result, Skeleton, theme } from "antd";
import { DashboardContextBus } from "../context/DashboardContextBus";
import { DashboardGrid } from "../components/DashboardGrid";
import { registerAllWidgets } from "../definitions/registerAll";
import { useDashboardPersistence } from "../api/useDashboardPersistence";
import { useDashboardCompositionStore } from "@/stores/useDashboardCompositionStore";
import { DashboardErrorBoundary } from "./DashboardErrorBoundary";

// Register all widget types into the global registry.
registerAllWidgets();

/**
 * Hosting page for the composable widget dashboard.
 *
 * Route: `/projects/:projectId/dashboard`
 * Provides the DashboardContextBus and renders the grid.
 * The grid manages the widget palette modal internally.
 *
 * Navigation guards prevent data loss when navigating away with unsaved changes.
 */
export function DashboardPage() {
  const { token } = theme.useToken();
  const { projectId } = useParams<{ projectId: string }>();
  const [modal, contextHolder] = Modal.useModal();

  // Composition store for dirty state and edit mode
  const isDirty = useDashboardCompositionStore((s) => s.isDirty);
  const isEditing = useDashboardCompositionStore((s) => s.isEditing);
  // Wire dashboard persistence -- load from backend, auto-save on changes
  const { save, isLoading } = useDashboardPersistence(projectId ?? "");

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

  if (!projectId) {
    return (
      <Result
        status="error"
        title="Project not found"
        subTitle="No project ID was provided in the URL."
      />
    );
  }

  return (
    <DashboardErrorBoundary>
      {contextHolder}
      <DashboardContextBus projectId={projectId}>
        <div
          style={{
            padding: token.paddingMD,
          }}
        >
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
        </div>
      </DashboardContextBus>
    </DashboardErrorBoundary>
  );
}
