import React from "react";
import { useParams } from "react-router-dom";
import { DocumentBrowser } from "@/features/documents/components/DocumentBrowser";

export const ProjectDocuments: React.FC = () => {
  const { projectId } = useParams<{ projectId: string }>();
  if (!projectId) return null;
  return <DocumentBrowser projectId={projectId} showFolderTree />;
};
