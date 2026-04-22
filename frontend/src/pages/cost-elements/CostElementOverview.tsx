import { useParams } from "react-router-dom";
import { Space } from "antd";
import { useCostElement } from "@/features/cost-elements/api/useCostElements";
import { useBudgetStatus } from "@/features/cost-registration/api/useCostRegistrations";
import { CostElementHeaderCard } from "@/components/cost-elements/CostElementHeaderCard";
import { CostElementInfoCard } from "@/components/cost-elements/CostElementInfoCard";
import { CostHistoryChart } from "@/features/cost-registration/components/CostHistoryChart";

export const CostElementOverview = () => {
  const { id } = useParams<{ id: string }>();
  const { data: costElement, isLoading } = useCostElement(id!);
  const { data: budgetStatus } = useBudgetStatus(id!);

  if (isLoading || !costElement) return null;

  return (
    <Space direction="vertical" size="middle" style={{ width: "100%" }}>
      <CostElementHeaderCard
        costElement={costElement}
        loading={isLoading}
        actualCosts={budgetStatus?.used}
        extraContent={
          id ? (
            <CostHistoryChart
              entityType="cost_element"
              entityId={id}
              headless
            />
          ) : undefined
        }
      />

      <CostElementInfoCard costElement={costElement} loading={isLoading} />
    </Space>
  );
};
