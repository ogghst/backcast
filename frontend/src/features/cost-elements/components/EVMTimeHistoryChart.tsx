import { useCostElementEvmHistory } from "../api/useCostElements";
import { CollapsibleCard } from "@/components/common/CollapsibleCard";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from "recharts";
import { Select, Spin, Empty } from "antd";
import { useState } from "react";
import dayjs from "dayjs";

interface EVMTimeHistoryChartProps {
  costElementId: string;
}

export const EVMTimeHistoryChart = ({
  costElementId,
}: EVMTimeHistoryChartProps) => {
  const [granularity, setGranularity] = useState<"day" | "week" | "month">(
    "week",
  );
  const { data: history, isLoading } = useCostElementEvmHistory(
    costElementId,
    granularity,
  );

  if (isLoading) {
    return (
      <CollapsibleCard
        id="evm-time-history-loading"
        title="EVM Performance Over Time"
        style={{ minHeight: 400 }}
      >
        <div
          style={{
            display: "flex",
            justifyContent: "center",
            alignItems: "center",
            height: 300,
          }}
        >
          <Spin size="large" />
        </div>
      </CollapsibleCard>
    );
  }

  if (!history || !history.points || history.points.length === 0) {
    return (
      <CollapsibleCard
        id="evm-time-history-empty"
        title="EVM Performance Over Time"
      >
        <Empty description="No history data available" />
      </CollapsibleCard>
    );
  }

  // Format date for X-axis
  const formatDate = (dateStr: string) => {
    return dayjs(dateStr).format(
      granularity === "day"
        ? "DD MMM"
        : granularity === "week"
          ? "DD MMM"
          : "MMM YYYY",
    );
  };

  const formatCurrency = (value: number) => {
    return `€ ${value.toLocaleString()}`;
  };

  return (
    <CollapsibleCard
      id="evm-time-history-card"
      title="EVM Performance Over Time"
      extra={
        <Select
          defaultValue="week"
          value={granularity}
          onChange={(val) => setGranularity(val as "day" | "week" | "month")}
          options={[
            { value: "day", label: "Daily" },
            { value: "week", label: "Weekly" },
            { value: "month", label: "Monthly" },
          ]}
          style={{ width: 120 }}
        />
      }
    >
      <div style={{ height: 400, width: "100%" }}>
        <ResponsiveContainer width="100%" height="100%">
          <LineChart
            data={history.points}
            margin={{ top: 5, right: 30, left: 20, bottom: 5 }}
          >
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="date" tickFormatter={formatDate} minTickGap={30} />
            <YAxis tickFormatter={(val) => `€${val / 1000}k`} />
            <Tooltip
              formatter={(value: number) => formatCurrency(value)}
              labelFormatter={(label) => dayjs(label).format("DD MMM YYYY")}
            />
            <Legend />
            <Line
              type="monotone"
              dataKey="pv"
              name="Planned Value (PV)"
              stroke="#8884d8"
              strokeDasharray="5 5"
            />
            <Line
              type="monotone"
              dataKey="ev"
              name="Earned Value (EV)"
              stroke="#82ca9d"
              strokeWidth={2}
            />
            <Line
              type="monotone"
              dataKey="ac"
              name="Actual Cost (AC)"
              stroke="#ff7300"
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </CollapsibleCard>
  );
};
