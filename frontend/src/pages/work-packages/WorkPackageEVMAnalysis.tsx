import { useParams } from "react-router-dom";
import { EVMAnalysisPage } from "@/features/evm/components/EVMAnalysisPage";
import { EntityType } from "@/features/evm/types";

export const WorkPackageEVMAnalysis = () => {
  const { id } = useParams<{ id: string }>();
  return <EVMAnalysisPage entityType={EntityType.WORK_PACKAGE} entityId={id || ""} />;
};
