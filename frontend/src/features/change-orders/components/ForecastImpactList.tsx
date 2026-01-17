import { Card, Table, Tag, Typography, Empty, Space, Tooltip } from "antd";
import { InfoCircleOutlined, ArrowUpOutlined, ArrowDownOutlined } from "@ant-design/icons";
import type { ColumnsType } from "antd/es/table";
import type { ForecastRead } from "@/api/generated";

const { Title, Text } = Typography;

interface ForecastComparison {
  costElementId: string;
  costElementCode: string;
  costElementName: string;
  budgetAmount: number;
  mainForecast?: ForecastRead;
  branchForecast?: ForecastRead;
}

interface ForecastImpactListProps {
  forecasts: ForecastComparison[];
  loading?: boolean;
  branchName?: string;
}

/**
 * Formats a decimal number to EUR currency.
 */
const formatCurrency = (value: number): string => {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "EUR",
  }).format(value);
};

/**
 * Calculates the VAC (Variance at Complete) = BAC - EAC
 */
const calculateVAC = (bac: number, eac: number): number => {
  return bac - eac;
};

/**
 * Gets the status color for VAC.
 */
const getVACStatus = (vac: number): { color: string; text: string } => {
  if (vac > 0) return { color: "green", text: "Under Budget" };
  if (vac < 0) return { color: "red", text: "Over Budget" };
  return { color: "blue", text: "On Budget" };
};

/**
 * ForecastImpactList Component
 *
 * Displays a comparison of forecasts between main and change order branch.
 * Shows:
 * - Cost element details
 * - Main branch EAC
 * - Branch EAC (proposed)
 * - EAC delta (change)
 * - VAC comparison
 * - Status change
 */
export const ForecastImpactList = ({
  forecasts,
  loading,
  branchName = "feature",
}: ForecastImpactListProps) => {
  // Filter to only show forecasts that exist in at least one branch
  const activeForecasts = forecasts.filter(
    (f) => f.mainForecast || f.branchForecast
  );

  if (activeForecasts.length === 0) {
    return (
      <Card loading={loading ?? false}>
        <Title level={4}>Forecast Impact</Title>
        <Empty description="No forecast changes detected in this change order" />
      </Card>
    );
  }

  const columns: ColumnsType<ForecastComparison> = [
    {
      title: "Cost Element",
      key: "costElement",
      width: "25%",
      render: (_, record) => (
        <div>
          <div style={{ fontWeight: 500 }}>{record.costElementCode}</div>
          <div style={{ fontSize: 12, color: "#8c8c8c" }}>{record.costElementName}</div>
          <div style={{ fontSize: 11, color: "#999" }}>BAC: {formatCurrency(record.budgetAmount)}</div>
        </div>
      ),
    },
    {
      title: (
        <Space>
          <span>Main EAC</span>
          <Tooltip title="Estimate at Complete in main branch">
            <InfoCircleOutlined style={{ color: "#999" }} />
          </Tooltip>
        </Space>
      ),
      key: "mainEAC",
      width: "18%",
      align: "right" as const,
      render: (_, record) => {
        const eac = record.mainForecast
          ? Number(record.mainForecast.eac_amount)
          : null;
        if (eac === null) {
          return <span style={{ color: "#8c8c8c" }}>-</span>;
        }
        const vac = calculateVAC(record.budgetAmount, eac);
        const status = getVACStatus(vac);
        return (
          <div>
            <div style={{ fontWeight: 500 }}>{formatCurrency(eac)}</div>
            <Tag color={status.color} style={{ fontSize: 10, marginTop: 4 }}>
              VAC: {formatCurrency(Math.abs(vac))}
            </Tag>
          </div>
        );
      },
    },
    {
      title: (
        <Space>
          <span>{branchName} EAC</span>
          <Tooltip title={`Estimate at Complete in ${branchName} branch`}>
            <InfoCircleOutlined style={{ color: "#999" }} />
          </Tooltip>
        </Space>
      ),
      key: "branchEAC",
      width: "18%",
      align: "right" as const,
      render: (_, record) => {
        const eac = record.branchForecast
          ? Number(record.branchForecast.eac_amount)
          : null;
        if (eac === null) {
          return <span style={{ color: "#8c8c8c" }}>-</span>;
        }
        const vac = calculateVAC(record.budgetAmount, eac);
        const status = getVACStatus(vac);
        return (
          <div>
            <div style={{ fontWeight: 500 }}>{formatCurrency(eac)}</div>
            <Tag color={status.color} style={{ fontSize: 10, marginTop: 4 }}>
              VAC: {formatCurrency(Math.abs(vac))}
            </Tag>
          </div>
        );
      },
    },
    {
      title: "EAC Change",
      key: "eacDelta",
      width: "18%",
      align: "right" as const,
      render: (_, record) => {
        const mainEAC = record.mainForecast
          ? Number(record.mainForecast.eac_amount)
          : null;
        const branchEAC = record.branchForecast
          ? Number(record.branchForecast.eac_amount)
          : null;

        if (mainEAC === null && branchEAC === null) {
          return <span style={{ color: "#8c8c8c" }}>-</span>;
        }

        // New forecast in branch
        if (mainEAC === null && branchEAC !== null) {
          return (
            <Space>
              <Tag color="green">NEW</Tag>
              <Text type="secondary">+{formatCurrency(branchEAC)}</Text>
            </Space>
          );
        }

        // Forecast removed in branch
        if (mainEAC !== null && branchEAC === null) {
          return (
            <Space>
              <Tag color="red">REMOVED</Tag>
              <Text type="secondary">-{formatCurrency(mainEAC)}</Text>
            </Space>
          );
        }

        // Both exist - calculate delta
        const delta = branchEAC! - mainEAC!;
        const color = delta > 0 ? "#cf1322" : delta < 0 ? "#3f8600" : undefined;
        const icon =
          delta > 0 ? (
            <ArrowUpOutlined style={{ color }} />
          ) : delta < 0 ? (
            <ArrowDownOutlined style={{ color }} />
          ) : null;

        return (
          <Space>
            {icon}
            <span style={{ color, fontWeight: 500 }}>
              {delta > 0 ? "+" : ""}
              {formatCurrency(delta)}
            </span>
            <Text type="secondary" style={{ fontSize: 11 }}>
              ({((delta / mainEAC!) * 100).toFixed(1)}%)
            </Text>
          </Space>
        );
      },
    },
    {
      title: "Status Change",
      key: "statusChange",
      width: "15%",
      render: (_, record) => {
        const mainEAC = record.mainForecast
          ? Number(record.mainForecast.eac_amount)
          : null;
        const branchEAC = record.branchForecast
          ? Number(record.branchForecast.eac_amount)
          : null;

        if (mainEAC === null || branchEAC === null) {
          return <span style={{ color: "#8c8c8c" }}>-</span>;
        }

        const mainVAC = calculateVAC(record.budgetAmount, mainEAC);
        const branchVAC = calculateVAC(record.budgetAmount, branchEAC);
        const mainStatus = getVACStatus(mainVAC);
        const branchStatus = getVACStatus(branchVAC);

        const statusChanged = mainStatus.text !== branchStatus.text;

        if (!statusChanged) {
          return (
            <Tag color={branchStatus.color}>{branchStatus.text}</Tag>
          );
        }

        return (
          <Space orientation="vertical" size={2}>
            <Tag color={mainStatus.color} style={{ fontSize: 10, margin: 0 }}>
              {mainStatus.text}
            </Tag>
            <span style={{ fontSize: 10, color: "#999" }}>→</span>
            <Tag color={branchStatus.color} style={{ fontSize: 10, margin: 0 }}>
              {branchStatus.text}
            </Tag>
          </Space>
        );
      },
    },
  ];

  // Calculate summary statistics
  const totalMainEAC = activeForecasts.reduce((sum, f) => {
    return sum + (f.mainForecast ? Number(f.mainForecast.eac_amount) : 0);
  }, 0);

  const totalBranchEAC = activeForecasts.reduce((sum, f) => {
    return sum + (f.branchForecast ? Number(f.branchForecast.eac_amount) : 0);
  }, 0);

  const totalDelta = totalBranchEAC - totalMainEAC;
  const deltaPercent = totalMainEAC > 0 ? (totalDelta / totalMainEAC) * 100 : 0;

  const forecasterAddedCount = activeForecasts.filter(
    (f) => !f.mainForecast && f.branchForecast
  ).length;
  const forecastsRemovedCount = activeForecasts.filter(
    (f) => f.mainForecast && !f.branchForecast
  ).length;
  const forecastsModifiedCount = activeForecasts.filter(
    (f) =>
      f.mainForecast &&
      f.branchForecast &&
      Number(f.mainForecast.eac_amount) !== Number(f.branchForecast.eac_amount)
  ).length;

  return (
    <Card loading={loading ?? false}>
      <Title level={4}>Forecast Impact Analysis</Title>

      {/* Summary Statistics */}
      <Card
        type="inner"
        size="small"
        style={{ marginBottom: 16, backgroundColor: "#fafafa" }}
      >
        <Space size="large">
          <div>
            <Text type="secondary">Total EAC Change:</Text>
            <div
              style={{
                fontSize: 18,
                fontWeight: "bold",
                color: totalDelta > 0 ? "#cf1322" : totalDelta < 0 ? "#3f8600" : undefined,
              }}
            >
              {totalDelta > 0 ? "+" : ""}
              {formatCurrency(totalDelta)}
              <span style={{ fontSize: 12, color: "#999", marginLeft: 4 }}>
                ({deltaPercent.toFixed(1)}%)
              </span>
            </div>
          </div>
          <div>
            <Text type="secondary">Main Total:</Text>
            <div style={{ fontSize: 16, fontWeight: 500 }}>
              {formatCurrency(totalMainEAC)}
            </div>
          </div>
          <div>
            <Text type="secondary">{branchName} Total:</Text>
            <div style={{ fontSize: 16, fontWeight: 500 }}>
              {formatCurrency(totalBranchEAC)}
            </div>
          </div>
        </Space>
        <div style={{ marginTop: 12, paddingTop: 12, borderTop: "1px solid #e8e8e8" }}>
          <Space>
            <Tag color="blue">Total: {activeForecasts.length}</Tag>
            <Tag color="green">Added: {forecasterAddedCount}</Tag>
            <Tag color="red">Removed: {forecastsRemovedCount}</Tag>
            <Tag color="orange">Modified: {forecastsModifiedCount}</Tag>
          </Space>
        </div>
      </Card>

      {/* Forecasts Table */}
      <Table
        dataSource={activeForecasts}
        columns={columns}
        rowKey={(record) => record.costElementId}
        pagination={false}
        size="small"
      />
    </Card>
  );
};
