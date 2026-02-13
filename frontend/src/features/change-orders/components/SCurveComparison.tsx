import { Card, Typography, Empty } from "antd";
import { Line } from "@ant-design/charts";
import type { TimeSeriesData } from "@/api/generated";

const { Title } = Typography;

interface SCurveComparisonProps {
  timeSeries: TimeSeriesData[] | undefined;
  loading?: boolean;
}

/**
 * SCurveComparison Component
 *
 * Displays an S-curve comparison between main branch and change branch
 * showing budget progression over time (weekly data points).
 *
 * Uses a dual-line chart from @ant-design/charts.
 */
export const SCurveComparison = ({ timeSeries, loading }: SCurveComparisonProps) => {
  // Find the budget metric (typically the first or only metric)
  const budgetData = timeSeries?.find((ts) => ts.metric_name === "budget");

  if (!budgetData?.data_points || budgetData.data_points.length === 0) {
    return (
      <Card loading={loading ?? false}>
        <Title level={4}>S-Curve Comparison</Title>
        <Empty description="No time-series data available" />
      </Card>
    );
  }

  // Transform data into dual-line format
  const chartData = budgetData.data_points.flatMap((point) => {
    const items: Array<{
      week: string;
      branch: string;
      value: number;
    }> = [];

    if (point.main_value !== null && point.main_value !== undefined) {
      items.push({
        week: point.week_start,
        branch: "Main Branch",
        value: Number(point.main_value),
      });
    }

    if (point.change_value !== null && point.change_value !== undefined) {
      items.push({
        week: point.week_start,
        branch: "Change Branch",
        value: Number(point.change_value),
      });
    }

    return items;
  });

  const config = {
    data: chartData,
    xField: "week",
    yField: "value",
    seriesField: "branch",
    smooth: true,
    color: ["#5b8ff9", "#cf1322"], // blue for main, red for change
    legend: {
      position: "top" as const,
    },
    tooltip: {
      formatter: (datum: { week: string; branch: string; value: number }) => ({
        name: datum.branch,
        value: new Intl.NumberFormat("en-US", {
          style: "currency",
          currency: "EUR",
        }).format(datum.value),
      }),
    },
    yAxis: {
      label: {
        formatter: (value: number) =>
          new Intl.NumberFormat("en-US", {
            style: "currency",
            currency: "EUR",
            minimumFractionDigits: 0,
            maximumFractionDigits: 0,
          }).format(value),
      },
    },
    xAxis: {
      label: {
        formatter: (value: string) => {
          const date = new Date(value);
          return date.toLocaleDateString("en-US", { month: "short", day: "numeric" });
        },
      },
    },
  };

  return (
    <Card loading={loading ?? false}>
      <Title level={4}>S-Curve Comparison</Title>
      <Line {...config} height={300} />
    </Card>
  );
};
