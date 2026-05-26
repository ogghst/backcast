import React from "react";
import { useParams } from "react-router-dom";
import { EntityDocumentsTab } from "@/features/documents/components/EntityDocumentsTab";
import { useCostElementBreadcrumb } from "@/features/cost-elements/api/useCostElements";
import { Spin } from "antd";

export const CostElementDocuments: React.FC = () => {
  const { id } = useParams<{ id: string }>();

  // Get projectId from breadcrumb (consistent with CostElementLayout pattern)
  const { data: breadcrumb, isLoading } = useCostElementBreadcrumb(id!);
  const projectId = breadcrumb?.project?.project_id;

  if (isLoading) return <Spin />;
  if (!id || !projectId) return null;

  return (
    <EntityDocumentsTab
      projectId={projectId}
      entityType="cost_element"
      entityId={id}
    />
  );
};
