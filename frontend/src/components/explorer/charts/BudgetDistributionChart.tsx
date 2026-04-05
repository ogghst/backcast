import { useMemo } from "react";
import { EChartsBaseChart } from "@/features/evm/components/charts/EChartsBaseChart";
import { buildDonutOptions } from "@/features/evm/utils/echartsConfig";
import { useEChartsColors } from "@/features/evm/utils/echartsTheme";
import { formatCurrency } from "../shared/formatters";

interface BudgetDistributionItem {
  name: string;
  value: number;
}

interface BudgetDistributionChartProps {
  items: BudgetDistributionItem[];
  /** Total budget for center label */
  totalBudget?: number;
  height?: number;
}

export const BudgetDistributionChart: React.FC<
  BudgetDistributionChartProps
> = ({ items, totalBudget, height = 220 }) => {
  const colors = useEChartsColors();

  const option = useMemo(
    () =>
      buildDonutOptions(
        {
          items,
          centerLabel: totalBudget !== undefined ? "Total Budget" : undefined,
          centerValue:
            totalBudget !== undefined
              ? formatCurrency(totalBudget)
              : undefined,
        },
        colors,
      ),
    [items, totalBudget, colors],
  );

  return (
    <EChartsBaseChart
      option={option}
      height={height}
      emptyDescription="No budget distribution data"
    />
  );
};
