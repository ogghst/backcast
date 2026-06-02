/**
 * WBS Element Cost History page component.
 *
 * Context: Displays cost history chart for a specific WBE,
 * showing how costs accumulated over time.
 *
 * @module pages/wbs-elements/WBSElementCostHistory
 */

import { useParams } from "react-router-dom";
import { useWBSElement } from "@/features/wbs-elements/api/useWBSElements";
import { CostHistoryChart } from "@/features/cost-registration/components/CostHistoryChart";
import { Spin, theme } from "antd";

/**
 * WBS Element Cost History page.
 *
 * Fetches WBS Element data and renders the shared CostHistoryChart
 * scoped to this WBE.
 */
export const WBSElementCostHistory = () => {
  const { projectId, wbsElementId } = useParams<{ projectId: string; wbsElementId: string }>();
  const { token } = theme.useToken();
  const { data: wbe, isLoading } = useWBSElement(wbsElementId!);

  if (isLoading) {
    return (
      <div
        style={{
          display: "flex",
          justifyContent: "center",
          padding: token.paddingXL * 1.5,
        }}
      >
        <Spin size="large" />
      </div>
    );
  }

  if (!wbe) return null;

  return <CostHistoryChart entityType="wbs_element" entityId={wbsElementId!} projectId={projectId} />;
};
