import React from "react";
import { useParams } from "react-router-dom";
import { EntityDocumentsTab } from "@/features/documents/components/EntityDocumentsTab";
import { useCostElement } from "@/features/cost-elements/api/useCostElements";
import { Spin } from "antd";

export const CostElementDocuments: React.FC = () => {
  const { id, projectId } = useParams<{ id: string; projectId: string }>();

  const { data: costElement, isLoading } = useCostElement(id!);

  if (isLoading) return <Spin />;
  if (!id || !projectId) return null;

  return (
    <EntityDocumentsTab
      projectId={projectId}
      entityType="cost_element"
      entityId={costElement?.cost_element_id || id}
    />
  );
};
