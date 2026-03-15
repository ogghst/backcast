import { useParams, useNavigate } from "react-router-dom";
import { Tabs, theme } from "antd";
import { useEffect } from "react";
import {
  useCostElement,
  useCostElementBreadcrumb,
} from "@/features/cost-elements/api/useCostElements";
import { OverviewTab } from "./tabs/OverviewTab";
import { CostRegistrationsTab } from "./tabs/CostRegistrationsTab";
import { ForecastsTab } from "./tabs/ForecastsTab";
import { ScheduleBaselinesTab } from "./tabs/ScheduleBaselinesTab";
import { ProgressEntriesTab } from "@/features/progress-entries/components/ProgressEntriesTab";
import {
  CostElementBreadcrumbBuilder,
  type CostElementBreadcrumb,
} from "@/components/cost-elements/CostElementBreadcrumbBuilder";
import { useTimeMachineStore } from "@/stores/useTimeMachineStore";

export const CostElementDetailPage = () => {
  const { token } = theme.useToken();
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const setCurrentProject = useTimeMachineStore((s) => s.setCurrentProject);

  const { data: breadcrumb, isLoading: breadcrumbLoading } =
    useCostElementBreadcrumb(id!) as {
      data: CostElementBreadcrumb | undefined;
      isLoading: boolean;
    };

  const isProjectReady = useTimeMachineStore(
    (s) => !!breadcrumb?.project?.project_id && s.currentProjectId === breadcrumb.project.project_id
  );

  const { data: costElement, isLoading: costElementLoading } = useCostElement(
    id!,
    undefined,
    { enabled: isProjectReady }
  );

  const isLoading = breadcrumbLoading || costElementLoading || !isProjectReady;

  // Set project context from breadcrumb for Time Machine
  useEffect(() => {
    if (breadcrumb?.project?.project_id) {
      setCurrentProject(breadcrumb.project.project_id);
    }
    // Cleanup when leaving page
    return () => {
      setCurrentProject(null);
    };
  }, [breadcrumb, setCurrentProject]);

  if (!costElement && !isLoading) {
    return (
      <div style={{ padding: 24 }}>
        <h1>Cost Element Not Found</h1>
        <p>The requested cost element could not be found.</p>
        <button onClick={() => navigate(-1)}>Go Back</button>
      </div>
    );
  }

  const tabItems = [
    {
      key: "overview",
      label: "Overview",
      children: costElement ? <OverviewTab costElement={costElement} /> : null,
    },
    {
      key: "forecasts",
      label: "Forecasts",
      children: costElement ? <ForecastsTab costElement={costElement} /> : null,
    },
    {
      key: "schedule-baselines",
      label: "Schedule Baselines",
      children: costElement ? (
        <ScheduleBaselinesTab costElement={costElement} />
      ) : null,
    },
    {
      key: "cost-registrations",
      label: "Cost Registrations",
      children: costElement ? (
        <CostRegistrationsTab costElement={costElement} />
      ) : null,
    },
    {
      key: "progress",
      label: "Progress",
      children: costElement ? (
        <ProgressEntriesTab costElement={costElement} />
      ) : null,
    },
  ];

  return (
    <div style={{ padding: 24 }}>
      {/* Breadcrumb Navigation */}
      <CostElementBreadcrumbBuilder
        breadcrumb={breadcrumb}
        loading={breadcrumbLoading}
      />

      {/* Page Header */}
      <div style={{ marginBottom: 24 }}>
        <h1 style={{ margin: 0 }}>
          {costElement?.code} - {costElement?.name}
        </h1>
        {costElement?.description && (
          <p style={{ color: token.colorTextSecondary, margin: "8px 0 0 0" }}>
            {costElement.description}
          </p>
        )}
      </div>

      {/* Tabs */}
      <Tabs defaultActiveKey="overview" items={tabItems} />
    </div>
  );
};
