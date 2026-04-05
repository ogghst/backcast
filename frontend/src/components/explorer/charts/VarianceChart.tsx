import { useMemo } from "react";
import { EChartsBaseChart } from "@/features/evm/components/charts/EChartsBaseChart";
import { buildVarianceBarOptions } from "@/features/evm/utils/echartsConfig";
import { useEChartsColors } from "@/features/evm/utils/echartsTheme";
import type { EVMMetricsResponse } from "@/features/evm/types";
import { formatCurrency } from "../shared/formatters";

interface VarianceChartProps {
  metrics: EVMMetricsResponse;
  height?: number;
}

export const VarianceChart: React.FC<VarianceChartProps> = ({
  metrics,
  height = 160,
}) => {
  const colors = useEChartsColors();

  const option = useMemo(
    () =>
      buildVarianceBarOptions(
        {
          metrics: {
            cv: metrics.cv,
            sv: metrics.sv,
          },
          currencyFormatter: (v: number) => formatCurrency(v),
        },
        colors,
      ),
    [metrics.cv, metrics.sv, colors],
  );

  return (
    <EChartsBaseChart
      option={option}
      height={height}
      emptyDescription="No variance data available"
    />
  );
};
