import React from "react";
import { useParams } from "react-router-dom";
import { EntityDocumentsTab } from "@/features/documents/components/EntityDocumentsTab";

export const WBEDocuments: React.FC = () => {
  const { projectId, wbeId } = useParams<{ projectId: string; wbeId: string }>();
  if (!projectId || !wbeId) return null;
  return (
    <EntityDocumentsTab
      projectId={projectId}
      entityType="wbe"
      entityId={wbeId}
    />
  );
};
