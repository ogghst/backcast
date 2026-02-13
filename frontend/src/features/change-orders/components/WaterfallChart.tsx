import { Card, Typography, Empty } from "antd";
import { Column } from "@ant-design/charts";
import type { WaterfallSegment } from "@/api/generated";

const { Title } = Typography;

interface WaterfallChartProps {
  data: WaterfallSegment[] | undefined;
  loading?: boolean;
}

/**
 * WaterfallChart Component
 *
 * Displays a waterfall chart showing budget impact progression:
 * - Current Margin (baseline)
 * - Change Impact (delta)
 * - New Margin (result)
 *
 * Uses a stacked column chart from @ant-design/charts.
 */
export const WaterfallChart = ({ data, loading }: WaterfallChartProps) => {
  // Transform data for the chart
  // Transform data for the chart
  const chartData = data?.map((segment) => {
    const parsedValue = Number(segment.value);
    return {
      name: segment.name,
      value: Number.isFinite(parsedValue) ? parsedValue : 0,
      isDelta: segment.is_delta ?? false,
      type: segment.is_delta ? "Change" : "Baseline",
    };
  });

  if (!chartData || chartData.length === 0) {
    return (
      <Card loading={loading ?? false}>
        <Title level={4}>Budget Waterfall</Title>
        <Empty description="No waterfall data available" />
      </Card>
    );
  }

  const config = {
    data: chartData,
    xField: "name",
    yField: "value",
    seriesField: "type",
    isStack: true,
    color: ({ type }: { type: string }) =>
      type === "Change" ? "#cf1322" : "#5b8ff9",
    columnStyle: {
      radius: [4, 4, 0, 0],
    },
    label: {
      position: "top" as const,
      formatter: (datum: { value: number } | number) => {
        const val = typeof datum === "number" ? datum : datum?.value;
        if (!Number.isFinite(val)) return "";
        return new Intl.NumberFormat("en-US", {
          style: "currency",
          currency: "EUR",
          minimumFractionDigits: 0,
          maximumFractionDigits: 0,
        }).format(val);
      },
    },
    tooltip: {
      formatter: (datum: { name: string; value: number; type: string }) => {
        const val = typeof datum === "number" ? datum : datum?.value;
        const safeVal = Number.isFinite(val) ? val : 0;
        return {
          name: datum?.name || "Value",
          value: new Intl.NumberFormat("en-US", {
            style: "currency",
            currency: "EUR",
          }).format(safeVal),
        };
      },
    },
    legend: {
      position: "top" as const,
    },
  };

  return (
    <Card loading={loading ?? false}>
      <Title level={4}>Budget Waterfall</Title>
      <Column {...config} height={300} />
    </Card>
  );
};
