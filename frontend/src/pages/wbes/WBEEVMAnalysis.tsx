/**
 * WBE-level EVM Analysis page component.
 *
 * Delegates to the shared EVMAnalysisPage with EntityType.WBE.
 *
 * @module pages/wbes/WBEEVMAnalysis
 */

import { useParams } from "react-router-dom";
import { EVMAnalysisPage } from "@/features/evm/components/EVMAnalysisPage";
import { EntityType } from "@/features/evm/types";

export const WBEEVMAnalysis = () => {
  const { wbeId } = useParams<{ wbeId: string }>();
  return <EVMAnalysisPage entityType={EntityType.WBE} entityId={wbeId || ""} />;
};
