/**
 * WBE Cost History page component.
 *
 * Context: Displays cost history chart for a specific WBE,
 * showing how costs accumulated over time.
 *
 * @module pages/wbes/WBECostHistory
 */

import { useParams } from "react-router-dom";
import { useWBE } from "@/features/wbes/api/useWBEs";
import { CostHistoryChart } from "@/features/cost-registration/components/CostHistoryChart";
import { Spin, theme } from "antd";

/**
 * WBE Cost History page.
 *
 * Fetches WBE data and renders the shared CostHistoryChart
 * scoped to this WBE.
 */
export const WBECostHistory = () => {
  const { wbeId } = useParams<{ wbeId: string }>();
  const { token } = theme.useToken();
  const { data: wbe, isLoading } = useWBE(wbeId!);

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

  return <CostHistoryChart entityType="wbe" entityId={wbeId!} />;
};
