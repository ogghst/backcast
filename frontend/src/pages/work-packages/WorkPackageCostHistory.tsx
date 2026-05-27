import { useParams } from "react-router-dom";
import { useWorkPackage } from "@/features/work-packages/api/useWorkPackages";
import { CostHistoryChart } from "@/features/cost-registration/components/CostHistoryChart";
import { useTimeMachineStore } from "@/stores/useTimeMachineStore";

export const WorkPackageCostHistory = () => {
  const { id } = useParams<{ id: string }>();
  const { data: workPackage, isLoading } = useWorkPackage(id!);

  if (isLoading || !workPackage) return null;

  return (
    <CostHistoryChart
      entityType="work_package"
      entityId={workPackage.work_package_id}
      projectId={useTimeMachineStore.getState().currentProjectId ?? undefined}
    />
  );
};
