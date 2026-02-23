import { Card, Typography, Empty } from "antd";
import { Waterfall } from "@ant-design/charts";
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
  const chartData = data?.map((segment) => {
    const parsedValue = Number(segment.value);
    return {
      name: segment.name,
      value: Number.isFinite(parsedValue) ? parsedValue : 0,
      isTotal: !(segment.is_delta ?? false),
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
    linkStyle: {
      lineDash: [4, 2],
      stroke: "#ccc",
    },
    style: {
      maxWidth: 80,
      stroke: "#ccc",
      fill: (d: { isTotal?: boolean; value: number }) => {
        return d.isTotal ? "#5b8ff9" : d.value > 0 ? "#3CC27F" : "#F56E53"; // Gray-blue for totals, Green for positive, Red for negative
      },
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
  };

  return (
    <Card loading={loading ?? false}>
      <Title level={4}>Budget Waterfall</Title>
      <Waterfall {...config} height={300} />
    </Card>
  );
};
