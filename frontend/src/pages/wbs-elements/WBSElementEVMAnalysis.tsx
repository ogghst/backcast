/**
 * WBE-level EVM Analysis page component.
 *
 * Delegates to the shared EVMAnalysisPage with EntityType.WBS_ELEMENT.
 *
 * @module pages/wbs-elements/WBSElementEVMAnalysis
 */

import { useParams } from "react-router-dom";
import { EVMAnalysisPage } from "@/features/evm/components/EVMAnalysisPage";
import { EntityType } from "@/features/evm/types";

export const WBSElementEVMAnalysis = () => {
  const { wbsElementId } = useParams<{ wbsElementId: string }>();
  return <EVMAnalysisPage entityType={EntityType.WBS_ELEMENT} entityId={wbsElementId || ""} />;
};
