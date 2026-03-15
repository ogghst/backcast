/**
 * StatusDistributionChart Component
 *
 * Displays a bar chart showing change order count by status.
 */
import { Card, Typography, Empty, Spin } from "antd";
import { Column } from "@ant-design/charts";
import type { ChangeOrderStatusStats } from "@/features/change-orders/api/useChangeOrderStats";

const { Title } = Typography;

interface StatusDistributionChartProps {
  data: ChangeOrderStatusStats[] | undefined;
  loading?: boolean;
}

// Status color mapping
const STATUS_COLORS: Record<string, string> = {
  Draft: "#8c8c8c",
  "Submitted for Approval": "#1890ff",
  "Under Review": "#722ed1",
  Approved: "#52c41a",
  Rejected: "#ff4d4f",
  Implemented: "#13c2c2",
};

export const StatusDistributionChart = ({
  data,
  loading,
}: StatusDistributionChartProps) => {
  const chartData = data?.map((item) => ({
    status: item.status,
    count: item.count,
    value: item.total_value ?? 0,
  }));

  if (!chartData || chartData.length === 0) {
    return (
      <Card>
        <Title level={5}>Status Distribution</Title>
        {loading ? <Spin /> : <Empty description="No data available" />}
      </Card>
    );
  }

  const config = {
    data: chartData,
    xField: "status",
    yField: "count",
    color: ({ status }: { status: string }) =>
      STATUS_COLORS[status] || "#1890ff",
    columnStyle: {
      radius: [4, 4, 0, 0],
    },
    label: {
      position: "top" as const,
    },
    tooltip: {
      formatter: (datum: { status: string; count: number; value: number }) => {
        return {
          name: datum.status,
          value: `${datum.count} COs (${new Intl.NumberFormat("en-US", {
            style: "currency",
            currency: "EUR",
            minimumFractionDigits: 0,
          }).format(datum.value)})`,
        };
      },
    },
    xAxis: {
      label: {
        autoRotate: true,
        autoHide: false,
      },
    },
  };

  return (
    <Card>
      <Title level={5}>Status Distribution</Title>
      <Column {...config} height={250} />
    </Card>
  );
};
