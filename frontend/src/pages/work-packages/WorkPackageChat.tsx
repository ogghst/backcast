import { useParams } from "react-router-dom";
import { useWorkPackage } from "@/features/work-packages/api/useWorkPackages";
import { ChatInterface } from "@/features/ai/chat/components/ChatInterface";

export const WorkPackageChat = () => {
  const { id, projectId } = useParams<{ id: string; projectId: string }>();
  const { data: workPackage } = useWorkPackage(id!);

  return (
    <ChatInterface
      contextOverride={
        workPackage && projectId
          ? {
              type: "work_package" as const,
              id: workPackage.work_package_id,
              project_id: projectId,
              name: workPackage.name,
            }
          : undefined
      }
    />
  );
};
