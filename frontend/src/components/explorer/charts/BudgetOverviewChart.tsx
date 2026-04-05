import { useMemo } from "react";
import { EChartsBaseChart } from "@/features/evm/components/charts/EChartsBaseChart";
import { buildBudgetOverviewOptions } from "@/features/evm/utils/echartsConfig";
import { useEChartsColors } from "@/features/evm/utils/echartsTheme";
import type { EVMMetricsResponse } from "@/features/evm/types";
import { formatCurrency } from "../shared/formatters";

interface BudgetOverviewChartProps {
  metrics: EVMMetricsResponse;
  height?: number;
}

export const BudgetOverviewChart: React.FC<BudgetOverviewChartProps> = ({
  metrics,
  height = 220,
}) => {
  const colors = useEChartsColors();

  const option = useMemo(
    () =>
      buildBudgetOverviewOptions(
        {
          metrics: {
            bac: metrics.bac,
            ac: metrics.ac,
            ev: metrics.ev,
            eac: metrics.eac,
          },
          currencyFormatter: (v: number) => formatCurrency(v),
        },
        colors,
      ),
    [metrics.bac, metrics.ac, metrics.ev, metrics.eac, colors],
  );

  const isLoading = metrics.bac === 0;

  return (
    <EChartsBaseChart
      option={option}
      loading={isLoading}
      height={height}
      emptyDescription="No budget data available"
    />
  );
};
