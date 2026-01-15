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
  const chartData = data?.map((segment) => ({
    name: segment.name,
    value: Number(segment.value),
    isDelta: segment.is_delta ?? false,
    type: segment.is_delta ? "Change" : "Baseline",
  }));

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
    color: ({ type }: { type: string }) => (type === "Change" ? "#cf1322" : "#5b8ff9"),
    columnStyle: {
      radius: [4, 4, 0, 0],
    },
    label: {
      position: "top" as const,
      formatter: (datum: { value: number }) =>
        new Intl.NumberFormat("en-US", {
          style: "currency",
          currency: "EUR",
          minimumFractionDigits: 0,
          maximumFractionDigits: 0,
        }).format(datum.value),
    },
    tooltip: {
      formatter: (datum: { name: string; value: number; type: string }) => ({
        name: datum.name,
        value: new Intl.NumberFormat("en-US", {
          style: "currency",
          currency: "EUR",
        }).format(datum.value),
      }),
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
