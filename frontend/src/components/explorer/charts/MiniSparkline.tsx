import { useMemo } from "react";
import { EChartsBaseChart } from "@/features/evm/components/charts/EChartsBaseChart";
import { buildMiniSparklineOptions } from "@/features/evm/utils/echartsConfig";
import { useEChartsColors } from "@/features/evm/utils/echartsTheme";

interface MiniSparklineProps {
  data: Array<[string, number | null]>;
  color?: string;
  showArea?: boolean;
  height?: number;
}

export const MiniSparkline: React.FC<MiniSparklineProps> = ({
  data,
  color,
  showArea,
  height = 60,
}) => {
  const colors = useEChartsColors();

  const option = useMemo(
    () =>
      buildMiniSparklineOptions(
        {
          data,
          color: color ?? colors.primary,
          showArea,
        },
        colors,
      ),
    [data, color, showArea, colors],
  );

  return (
    <EChartsBaseChart
      option={option}
      height={height}
      showWhenEmpty
      emptyDescription="No trend data"
    />
  );
};
