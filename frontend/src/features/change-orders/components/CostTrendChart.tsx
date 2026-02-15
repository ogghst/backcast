/**
 * CostTrendChart Component
 *
 * Displays a line chart showing cumulative cost impact over time.
 */
import { Card, Typography, Empty, Spin } from "antd";
import { Line } from "@ant-design/charts";
import type { ChangeOrderTrendPoint } from "@/features/change-orders/api/useChangeOrderStats";

const { Title } = Typography;

interface CostTrendChartProps {
  data: ChangeOrderTrendPoint[] | undefined;
  loading?: boolean;
}

export const CostTrendChart = ({ data, loading }: CostTrendChartProps) => {
  const chartData = data?.map((item) => ({
    date: item.date,
    cumulative_value: Number(item.cumulative_value),
    count: item.count,
  }));

  if (!chartData || chartData.length === 0) {
    return (
      <Card>
        <Title level={5}>Cost Trend Over Time</Title>
        {loading ? <Spin /> : <Empty description="No trend data available" />}
      </Card>
    );
  }

  const config = {
    data: chartData,
    xField: "date",
    yField: "cumulative_value",
    point: {
      size: 4,
      shape: "circle",
    },
    smooth: true,
    tooltip: {
      formatter: (datum: {
        date: string;
        cumulative_value: number;
        count: number;
      }) => {
        return {
          name: "Cumulative Cost",
          value: new Intl.NumberFormat("en-US", {
            style: "currency",
            currency: "EUR",
          }).format(datum.cumulative_value),
        };
      },
      fields: ["date", "cumulative_value", "count"],
    },
    yAxis: {
      label: {
        formatter: (value: number) =>
          new Intl.NumberFormat("en-US", {
            style: "currency",
            currency: "EUR",
            notation: "compact",
          }).format(value),
      },
    },
    xAxis: {
      label: {
        autoRotate: true,
      },
    },
  };

  return (
    <Card>
      <Title level={5}>Cost Trend Over Time</Title>
      <Line {...config} height={250} />
    </Card>
  );
};
