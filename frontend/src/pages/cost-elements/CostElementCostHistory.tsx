import { useParams } from "react-router-dom";
import { useCostElement } from "@/features/cost-elements/api/useCostElements";
import { CostHistoryChart } from "@/features/cost-registration/components/CostHistoryChart";
import { useTimeMachineStore } from "@/stores/useTimeMachineStore";

export const CostElementCostHistory = () => {
  const { id } = useParams<{ id: string }>();
  const { data: costElement, isLoading } = useCostElement(id!);

  if (isLoading || !costElement) return null;

  return (
    <CostHistoryChart
      entityType="cost_element"
      entityId={costElement.cost_element_id}
      projectId={useTimeMachineStore.getState().currentProjectId ?? undefined}
    />
  );
};
