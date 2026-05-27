import React from "react";
import { useParams } from "react-router-dom";
import { EntityDocumentsTab } from "@/features/documents/components/EntityDocumentsTab";
import { useWorkPackage } from "@/features/work-packages/api/useWorkPackages";
import { Spin } from "antd";

export const WorkPackageDocuments: React.FC = () => {
  const { id, projectId } = useParams<{ id: string; projectId: string }>();

  const { data: workPackage, isLoading } = useWorkPackage(id!);

  if (isLoading) return <Spin />;
  if (!id || !projectId) return null;

  return (
    <EntityDocumentsTab
      projectId={projectId}
      entityType="work_package"
      entityId={workPackage?.work_package_id || id}
    />
  );
};
