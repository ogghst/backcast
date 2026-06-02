import { useParams } from "react-router-dom";
import { useWorkPackage } from "@/features/work-packages/api/useWorkPackages";
import { ChatInterface } from "@/features/ai/chat/components/ChatInterface";

export const WorkPackageChat = () => {
  const { id } = useParams<{ id: string }>();
  const { data: workPackage } = useWorkPackage(id!);

  // Work Package context not yet supported by AI backend.
  // Pass as general context with name until backend is updated.
  return (
    <ChatInterface
      contextOverride={{
        type: "general",
        name: workPackage ? `WP: ${workPackage.name}` : undefined,
      }}
    />
  );
};
