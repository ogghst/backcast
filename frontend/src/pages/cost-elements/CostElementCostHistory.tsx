import { useParams } from "react-router-dom";
import { useCostElement } from "@/features/cost-elements/api/useCostElements";
import { CostHistoryChart } from "@/features/cost-registration/components/CostHistoryChart";

export const CostElementCostHistory = () => {
  const { id } = useParams<{ id: string }>();
  const { data: costElement, isLoading } = useCostElement(id!);

  if (isLoading || !costElement) return null;

  return (
    <CostHistoryChart
      entityType="cost_element"
      entityId={costElement.cost_element_id}
      budgetAmount={Number(costElement.budget_amount)}
    />
  );
};
