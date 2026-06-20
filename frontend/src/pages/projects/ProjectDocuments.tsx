import React from "react";
import { useParams } from "react-router-dom";
import { DocumentBrowser } from "@/features/documents/components/DocumentBrowser";
import { ProjectPage } from "@/features/projects/components/ProjectPage";

export const ProjectDocuments: React.FC = () => {
  const { projectId } = useParams<{ projectId: string }>();
  if (!projectId) return null;
  return (
    <ProjectPage title="Documents">
      <DocumentBrowser projectId={projectId} showFolderTree />
    </ProjectPage>
  );
};
