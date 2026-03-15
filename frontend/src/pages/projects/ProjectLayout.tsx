import React from "react";
import { Outlet, useParams } from "react-router-dom";
import { PageNavigation } from "@/components/navigation";

export const ProjectLayout: React.FC = () => {
  const { projectId } = useParams<{ projectId: string }>();

  const items = [
    { key: "overview", label: "Overview", path: `/projects/${projectId}` },
    { key: "structure", label: "Structure", path: `/projects/${projectId}/structure` },
    { key: "change-orders", label: "Change Orders", path: `/projects/${projectId}/change-orders` },
    { key: "evm-analysis", label: "EVM Analysis", path: `/projects/${projectId}/evm-analysis` },
  ];

  return (
    <>
      <PageNavigation items={items} />
      <Outlet />
    </>
  );
};
