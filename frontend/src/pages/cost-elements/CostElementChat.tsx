import { useParams } from "react-router-dom";
import { useCostElement, useCostElementBreadcrumb } from "@/features/cost-elements/api/useCostElements";
import { ChatInterface } from "@/features/ai/chat/components/ChatInterface";

export const CostElementChat = () => {
  const { id } = useParams<{ id: string }>();
  const { data: costElement } = useCostElement(id!);
  const { data: breadcrumb } = useCostElementBreadcrumb(id!);

  return (
    <ChatInterface
      contextOverride={{
        type: "cost_element",
        id: costElement?.cost_element_id,
        project_id: breadcrumb?.project?.project_id,
        name: costElement?.name,
      }}
    />
  );
};
