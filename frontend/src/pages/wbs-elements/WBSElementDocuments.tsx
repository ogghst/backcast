import React from "react";
import { useParams } from "react-router-dom";
import { EntityDocumentsTab } from "@/features/documents/components/EntityDocumentsTab";

export const WBSElementDocuments: React.FC = () => {
  const { projectId, wbsElementId } = useParams<{ projectId: string; wbsElementId: string }>();
  if (!projectId || !wbsElementId) return null;
  return (
    <EntityDocumentsTab
      projectId={projectId}
      entityType="wbs_element"
      entityId={wbsElementId}
    />
  );
};
