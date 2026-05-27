import { useParams } from "react-router-dom";
import { useCostElement } from "@/features/cost-elements/api/useCostElements";
import { ChatInterface } from "@/features/ai/chat/components/ChatInterface";

export const CostElementChat = () => {
  const { id } = useParams<{ id: string }>();
  const { data: costElement } = useCostElement(id!);

  return (
    <ChatInterface
      contextOverride={{
        type: "cost_element",
        id: costElement?.cost_element_id,
        name: costElement?.cost_element_type_name ?? undefined,
      }}
    />
  );
};
