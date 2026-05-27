import React from "react";
import { Outlet, useParams } from "react-router-dom";
import { PageNavigation } from "@/components/navigation";

export const ProjectLayout: React.FC = () => {
  const { projectId } = useParams<{ projectId: string }>();

  const items = [
    { key: "dashboard", label: "Dashboard", path: `/projects/${projectId}/dashboard` },
    { key: "overview", label: "Overview", path: `/projects/${projectId}` },
    { key: "structure", label: "Structure", path: `/projects/${projectId}/structure` },
    // Explorer tab temporarily disabled
    // { key: "explorer", label: "Explorer", path: `/projects/${projectId}/explorer` },
    { key: "schedule", label: "Schedule", path: `/projects/${projectId}/schedule` },
    { key: "change-orders", label: "Change Orders", path: `/projects/${projectId}/change-orders` },
    { key: "members", label: "Members", path: `/projects/${projectId}/members` },
    { key: "evm-analysis", label: "EVM Analysis", path: `/projects/${projectId}/evm-analysis` },
    { key: "coq-analysis", label: "COQ Analysis", path: `/projects/${projectId}/coq-analysis` },
    { key: "work-packages", label: "Cost Events", path: `/projects/${projectId}/work-packages` },
    { key: "documents", label: "Documents", path: `/projects/${projectId}/documents` },
    { key: "chat", label: "AI Chat", path: `/projects/${projectId}/chat` },
    { key: "admin", label: "Admin", path: `/projects/${projectId}/admin` },
  ];

  return (
    <>
      <PageNavigation items={items} />
      <Outlet />
    </>
  );
};
