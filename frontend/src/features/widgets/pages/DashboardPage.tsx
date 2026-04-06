import { useParams } from "react-router-dom";
import { Result, theme } from "antd";
import { DashboardContextBus } from "../context/DashboardContextBus";
import { DashboardGrid } from "../components/DashboardGrid";
import { registerAllWidgets } from "../definitions/registerAll";
import { useDashboardPersistence } from "../api/useDashboardPersistence";

// Register all widget types into the global registry.
registerAllWidgets();

/**
 * Hosting page for the composable widget dashboard.
 *
 * Route: `/projects/:projectId/dashboard`
 * Provides the DashboardContextBus and renders the grid.
 * The grid manages the widget palette modal internally.
 */
export function DashboardPage() {
  const { token } = theme.useToken();
  const { projectId } = useParams<{ projectId: string }>();

  // Wire dashboard persistence -- load from backend, auto-save on changes
  useDashboardPersistence(projectId ?? "");

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
    <DashboardContextBus projectId={projectId}>
      <div
        style={{
          height: "100%",
          overflow: "auto",
          padding: token.paddingMD,
        }}
      >
        <DashboardGrid />
      </div>
    </DashboardContextBus>
  );
}
