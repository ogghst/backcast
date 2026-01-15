import React from "react";
import { Outlet, useParams } from "react-router-dom";
import { PageNavigation } from "@/components/navigation";

export const ProjectLayout: React.FC = () => {
  const { projectId } = useParams<{ projectId: string }>();

  const items = [
    { key: "overview", label: "Overview", path: `/projects/${projectId}` },
    { key: "change-orders", label: "Change Orders", path: `/projects/${projectId}/change-orders` },
  ];

  return (
    <>
      <PageNavigation items={items} />
      <Outlet />
    </>
  );
};
