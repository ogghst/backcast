/**
 * ImpactLevelChart Component
 *
 * Displays a pie/donut chart showing change order distribution by impact level.
 */
import { Card, Typography, Empty, Spin } from "antd";
import { Pie } from "@ant-design/charts";
import type { ChangeOrderImpactStats } from "@/features/change-orders/api/useChangeOrderStats";

const { Title } = Typography;

interface ImpactLevelChartProps {
  data: ChangeOrderImpactStats[] | undefined;
  loading?: boolean;
}

// Impact level color mapping
const IMPACT_COLORS: Record<string, string> = {
  LOW: "#52c41a",
  MEDIUM: "#faad14",
  HIGH: "#fa8c16",
  CRITICAL: "#ff4d4f",
  Unassigned: "#8c8c8c",
};

export const ImpactLevelChart = ({
  data,
  loading,
}: ImpactLevelChartProps) => {
  const chartData = data?.map((item) => ({
    impact_level: item.impact_level,
    count: item.count,
    value: item.total_value ?? 0,
  }));

  if (!chartData || chartData.length === 0) {
    return (
      <Card>
        <Title level={5}>Impact Level Distribution</Title>
        {loading ? <Spin /> : <Empty description="No data available" />}
      </Card>
    );
  }

  const config = {
    data: chartData,
    angleField: "count",
    colorField: "impact_level",
    color: ({ impact_level }: { impact_level: string }) =>
      IMPACT_COLORS[impact_level] || "#1890ff",
    radius: 0.8,
    innerRadius: 0.6,
    label: {
      type: "outer" as const,
      formatter: (datum: { impact_level: string; count: number }) => {
        return `${datum.impact_level}: ${datum.count}`;
      },
    },
    legend: {
      position: "bottom" as const,
    },
    tooltip: {
      formatter: (datum: {
        impact_level: string;
        count: number;
        value: number;
      }) => {
        return {
          name: datum.impact_level,
          value: `${datum.count} COs (${new Intl.NumberFormat("en-US", {
            style: "currency",
            currency: "EUR",
            minimumFractionDigits: 0,
          }).format(datum.value)})`,
        };
      },
    },
    statistic: {
      title: {
        content: "Total",
      },
      content: {
        formatter: () => {
          const total = chartData.reduce((sum, item) => sum + item.count, 0);
          return total.toString();
        },
      },
    },
  };

  return (
    <Card>
      <Title level={5}>Impact Level Distribution</Title>
      <Pie {...config} height={250} />
    </Card>
  );
};
