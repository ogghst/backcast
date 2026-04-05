import { useMemo } from "react";
import { EChartsBaseChart } from "@/features/evm/components/charts/EChartsBaseChart";
import { buildPerformanceRadarOptions } from "@/features/evm/utils/echartsConfig";
import { useEChartsColors } from "@/features/evm/utils/echartsTheme";
import type { EVMMetricsResponse } from "@/features/evm/types";

interface PerformanceRadarProps {
  metrics: EVMMetricsResponse;
  height?: number;
}

export const PerformanceRadar: React.FC<PerformanceRadarProps> = ({
  metrics,
  height = 250,
}) => {
  const colors = useEChartsColors();

  const option = useMemo(
    () =>
      buildPerformanceRadarOptions(
        {
          metrics: {
            cpi: metrics.cpi ?? 0,
            spi: metrics.spi ?? 0,
            progress_percentage: metrics.progress_percentage,
          },
        },
        colors,
      ),
    [metrics.cpi, metrics.spi, metrics.progress_percentage, colors],
  );

  return (
    <EChartsBaseChart
      option={option}
      height={height}
      emptyDescription="No performance data available"
    />
  );
};
