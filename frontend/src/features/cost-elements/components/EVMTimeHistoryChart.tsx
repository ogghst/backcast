import { useEVMTimeSeries } from "@/features/evm/api/useEVMMetrics";
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
import { EntityType, EVMTimeSeriesGranularity } from "@/features/evm/types";
import { useCostElement } from "@/features/cost-elements/api/useCostElements";
import { useProjectCurrency } from "@/features/projects/api/useProjectCurrency";
import { getCurrencySymbol } from "@/utils/formatters";

interface EVMTimeHistoryChartProps {
  costElementId: string;
}

export const EVMTimeHistoryChart = ({
  costElementId,
}: EVMTimeHistoryChartProps) => {
  const [granularity, setGranularity] = useState<EVMTimeSeriesGranularity>(
    EVMTimeSeriesGranularity.WEEK,
  );

  const { data: timeSeries, isLoading } = useEVMTimeSeries(
    EntityType.COST_ELEMENT,
    costElementId,
    granularity,
  );

  // Trigger cost element query (used indirectly for project currency resolution)
  useCostElement(costElementId);
  const currency = useProjectCurrency(undefined);
  const currencySymbol = getCurrencySymbol(currency);

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

  if (!timeSeries?.points?.length) {
    return (
      <CollapsibleCard
        id="evm-time-history-empty"
        title="EVM Performance Over Time"
        style={{ minHeight: 400 }}
      >
        <Empty description="No EVM history data available" />
      </CollapsibleCard>
    );
  }

  const chartData = timeSeries.points.map((point) => ({
    date: point.date,
    PV: point.pv,
    EV: point.ev,
    AC: point.ac,
    Forecast: point.forecast,
  }));

  return (
    <CollapsibleCard
      id="evm-time-history"
      title="EVM Performance Over Time"
      style={{ minHeight: 400 }}
      extra={
        <Select
          value={granularity}
          onChange={(v) => setGranularity(v as EVMTimeSeriesGranularity)}
          size="small"
          style={{ width: 120 }}
          options={[
            { label: "Daily", value: EVMTimeSeriesGranularity.DAY },
            { label: "Weekly", value: EVMTimeSeriesGranularity.WEEK },
            { label: "Monthly", value: EVMTimeSeriesGranularity.MONTH },
          ]}
        />
      }
    >
      <ResponsiveContainer width="100%" height={350}>
        <LineChart data={chartData}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis dataKey="date" tick={{ fontSize: 11 }} />
          <YAxis tick={{ fontSize: 11 }} />
          <Tooltip />
          <Legend />
          <Line
            type="monotone"
            dataKey="PV"
            stroke="#5b8ff9"
            strokeWidth={2}
            name={`PV (${currencySymbol})`}
          />
          <Line
            type="monotone"
            dataKey="EV"
            stroke="#5ad8a6"
            strokeWidth={2}
            name={`EV (${currencySymbol})`}
          />
          <Line
            type="monotone"
            dataKey="AC"
            stroke="#5d7092"
            strokeWidth={2}
            name={`AC (${currencySymbol})`}
          />
          <Line
            type="monotone"
            dataKey="Forecast"
            stroke="#faad14"
            strokeWidth={2}
            strokeDasharray="5 5"
            name={`Forecast (${currencySymbol})`}
          />
        </LineChart>
      </ResponsiveContainer>
    </CollapsibleCard>
  );
};
