import { Card, Table, Tag, Typography, Empty, Space, Tooltip, theme } from "antd";
import { InfoCircleOutlined, ArrowUpOutlined, ArrowDownOutlined } from "@ant-design/icons";
import type { ColumnsType } from "antd/es/table";

const { Title, Text } = Typography;

interface ForecastRead {
  eac_amount: number;
}

interface ForecastComparison {
  cost_element_id: string;
  cost_element_code: string;
  cost_element_name: string;
  budget_amount: number;
  main_eac?: number;
  main_forecast?: ForecastRead;
  change_eac?: number;
  branch_forecast?: ForecastRead;
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
  const { token } = theme.useToken();

  // Filter to only show forecasts that exist in at least one branch
  const activeForecasts = forecasts.filter(
    (f) => f.main_forecast || f.branch_forecast
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
          <div style={{ fontWeight: 500 }}>{record.cost_element_code}</div>
          <div style={{ fontSize: 12, color: "#8c8c8c" }}>{record.cost_element_name}</div>
          <div style={{ fontSize: 11, color: token.colorTextTertiary }}>BAC: {formatCurrency(record.budget_amount)}</div>
        </div>
      ),
    },
    {
      title: (
        <Space>
          <span>Main EAC</span>
          <Tooltip title="Estimate at Complete in main branch">
            <InfoCircleOutlined style={{ color: token.colorTextTertiary }} />
          </Tooltip>
        </Space>
      ),
      key: "mainEAC",
      width: "18%",
      align: "right" as const,
      render: (_, record) => {
        const eac = record.main_forecast
          ? Number(record.main_forecast.eac_amount)
          : (record.main_eac ?? null);
        if (eac === null) {
          return <span style={{ color: token.colorTextSecondary }}>-</span>;
        }
        const vac = calculateVAC(record.budget_amount, eac);
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
            <InfoCircleOutlined style={{ color: token.colorTextTertiary }} />
          </Tooltip>
        </Space>
      ),
      key: "branchEAC",
      width: "18%",
      align: "right" as const,
      render: (_, record) => {
        const eac = record.branch_forecast
          ? Number(record.branch_forecast.eac_amount)
          : (record.change_eac ?? null);
        if (eac === null) {
          return <span style={{ color: token.colorTextSecondary }}>-</span>;
        }
        const vac = calculateVAC(record.budget_amount, eac);
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
        const mainEAC = record.main_forecast
          ? Number(record.main_forecast.eac_amount)
          : (record.main_eac ?? null);
        const branchEAC = record.branch_forecast
          ? Number(record.branch_forecast.eac_amount)
          : (record.change_eac ?? null);

        if (mainEAC === null && branchEAC === null) {
          return <span style={{ color: token.colorTextSecondary }}>-</span>;
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
        const color = delta > 0 ? token.colorError : delta < 0 ? token.colorSuccess : undefined;
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
        const mainEAC = record.main_forecast
          ? Number(record.main_forecast.eac_amount)
          : (record.main_eac ?? null);
        const branchEAC = record.branch_forecast
          ? Number(record.branch_forecast.eac_amount)
          : (record.change_eac ?? null);

        if (mainEAC === null || branchEAC === null) {
          return <span style={{ color: token.colorTextSecondary }}>-</span>;
        }

        const mainVAC = calculateVAC(record.budget_amount, mainEAC);
        const branchVAC = calculateVAC(record.budget_amount, branchEAC);
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
            <span style={{ fontSize: 10, color: token.colorTextTertiary }}>→</span>
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
    return sum + (f.main_forecast ? Number(f.main_forecast.eac_amount) : (f.main_eac ?? 0));
  }, 0);

  const totalBranchEAC = activeForecasts.reduce((sum, f) => {
    return sum + (f.branch_forecast ? Number(f.branch_forecast.eac_amount) : (f.change_eac ?? 0));
  }, 0);

  const totalDelta = totalBranchEAC - totalMainEAC;
  const deltaPercent = totalMainEAC > 0 ? (totalDelta / totalMainEAC) * 100 : 0;

  const forecastAddedCount = activeForecasts.filter(
    (f) => !f.main_forecast && f.branch_forecast
  ).length;
  const forecastsRemovedCount = activeForecasts.filter(
    (f) => f.main_forecast && !f.branch_forecast
  ).length;
  const forecastsModifiedCount = activeForecasts.filter(
    (f) =>
      f.main_forecast &&
      f.branch_forecast &&
      Number(f.main_forecast.eac_amount) !== Number(f.branch_forecast.eac_amount)
  ).length;

  return (
    <Card loading={loading ?? false}>
      <Title level={4}>Forecast Impact Analysis</Title>

      {/* Summary Statistics */}
      <Card
        type="inner"
        size="small"
        style={{ marginBottom: 16, backgroundColor: token.colorFillSecondary }}
      >
        <Space size="large">
          <div>
            <Text type="secondary">Total EAC Change:</Text>
            <div
              style={{
                fontSize: 18,
                fontWeight: "bold",
                color: totalDelta > 0 ? token.colorError : totalDelta < 0 ? token.colorSuccess : undefined,
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
        <div style={{ marginTop: 12, paddingTop: 12, borderTop: `1px solid ${token.colorBorderSecondary}` }}>
          <Space>
            <Tag color="blue">Total: {activeForecasts.length}</Tag>
            <Tag color="green">Added: {forecastAddedCount}</Tag>
            <Tag color="red">Removed: {forecastsRemovedCount}</Tag>
            <Tag color="orange">Modified: {forecastsModifiedCount}</Tag>
          </Space>
        </div>
      </Card>

      {/* Forecasts Table */}
      <Table
        dataSource={activeForecasts}
        columns={columns}
        rowKey={(record) => record.cost_element_id}
        pagination={false}
        size="small"
      />
    </Card>
  );
};
