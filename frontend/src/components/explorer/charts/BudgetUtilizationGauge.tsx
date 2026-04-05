import { EChartsGauge } from "@/features/evm/components/charts/EChartsGauge";

interface BudgetUtilizationGaugeProps {
  /** Budget utilization percentage (0-100) */
  percentage: number;
  height?: number;
}

export const BudgetUtilizationGauge: React.FC<
  BudgetUtilizationGaugeProps
> = ({ percentage, height = 150 }) => {
  return (
    <div style={{ height }}>
      <EChartsGauge
        value={percentage}
        min={0}
        max={100}
        label="Budget Used"
        goodThreshold={75}
        warningThresholdPercent={0.9}
        variant="semi-circle"
        size={180}
      />
    </div>
  );
};
