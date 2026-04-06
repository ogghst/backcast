import { HeartOutlined } from "@ant-design/icons";
import { Card, Col, Row, Statistic, Typography, theme } from "antd";
import type { FC } from "react";
import { EntityType } from "@/features/evm/types";
import type { EVMMetricsResponse } from "@/features/evm/types";
import { WidgetShell } from "../components/WidgetShell";
import { useWidgetEVMData } from "./shared/useWidgetEVMData";
import { registerWidget, widgetTypeId } from "..";
import type { WidgetComponentProps } from "../types";

const { Text } = Typography;

interface HealthSummaryConfig {
  entityType: EntityType;
  goodThreshold: number;
  warningThreshold: number;
}

type HealthColor = "success" | "warning" | "error";

function spiCpiColor(
  value: number | null,
  goodThreshold: number,
  warningThreshold: number,
): HealthColor {
  if (value === null) return "warning";
  if (value >= goodThreshold) return "success";
  if (value >= warningThreshold) return "warning";
  return "error";
}

function svColor(sv: number | null, bac: number): HealthColor {
  if (sv === null) return "warning";
  if (sv >= 0) return "success";
  if (sv >= -0.1 * bac) return "warning";
  return "error";
}

function healthToken(
  color: HealthColor,
  t: { colorSuccess: string; colorWarning: string; colorError: string },
): string {
  switch (color) {
    case "success":
      return t.colorSuccess;
    case "warning":
      return t.colorWarning;
    case "error":
      return t.colorError;
  }
}

interface MetricCardProps {
  title: string;
  value: number | null;
  precision?: number;
  prefix?: string;
  suffix?: string;
  borderColor: string;
  token: ReturnType<typeof theme.useToken>["token"];
}

const MetricCard: FC<MetricCardProps> = ({
  title,
  value,
  precision = 2,
  prefix,
  suffix,
  borderColor,
  token,
}) => (
  <Card
    size="small"
    style={{ borderLeft: `3px solid ${borderColor}` }}
    styles={{ body: { padding: `${token.paddingXS}px ${token.paddingSM}px` } }}
  >
    <Statistic
      title={
        <Text style={{ fontSize: token.fontSizeSM }} type="secondary">
          {title}
        </Text>
      }
      value={value ?? "N/A"}
      precision={value !== null ? precision : undefined}
      prefix={value !== null ? prefix : undefined}
      suffix={value !== null ? suffix : undefined}
      valueStyle={{
        fontSize: token.fontSizeLG,
        color: value !== null ? borderColor : token.colorTextSecondary,
      }}
    />
  </Card>
);

interface HealthContentProps {
  metrics: EVMMetricsResponse;
  config: HealthSummaryConfig;
}

const HealthContent: FC<HealthContentProps> = ({ metrics, config }) => {
  const { token } = theme.useToken();

  const spiBorder = healthToken(
    spiCpiColor(metrics.spi, config.goodThreshold, config.warningThreshold),
    token,
  );
  const cpiBorder = healthToken(
    spiCpiColor(metrics.cpi, config.goodThreshold, config.warningThreshold),
    token,
  );
  const svBorder = healthToken(svColor(metrics.sv, metrics.bac), token);

  return (
    <Row gutter={[token.paddingSM, token.paddingSM]}>
      <Col span={8}>
        <MetricCard
          title="SPI"
          value={metrics.spi}
          borderColor={spiBorder}
          token={token}
        />
      </Col>
      <Col span={8}>
        <MetricCard
          title="CPI"
          value={metrics.cpi}
          borderColor={cpiBorder}
          token={token}
        />
      </Col>
      <Col span={8}>
        <MetricCard
          title="SV"
          value={metrics.sv}
          precision={0}
          prefix={"\u20AC"}
          borderColor={svBorder}
          token={token}
        />
      </Col>
    </Row>
  );
};

const HealthSummaryComponent: FC<WidgetComponentProps<HealthSummaryConfig>> = ({
  config,
  instanceId,
  isEditing,
  onRemove,
  onConfigure,
}) => {
  const { token } = theme.useToken();
  const { metrics, isLoading, error, entityId, refetch } = useWidgetEVMData(
    config.entityType,
  );

  return (
    <WidgetShell
      instanceId={instanceId}
      title="Health Summary"
      icon={<HeartOutlined />}
      isEditing={isEditing}
      isLoading={isLoading}
      error={error}
      onRemove={onRemove}
      onRefresh={refetch}
      onConfigure={onConfigure}
    >
      {metrics ? (
        <HealthContent metrics={metrics} config={config} />
      ) : (
        !isLoading &&
        !error &&
        !entityId && (
          <div
            style={{
              textAlign: "center",
              padding: token.paddingMD,
            }}
          >
            <Text type="secondary">
              Select an entity to view health summary
            </Text>
          </div>
        )
      )}
    </WidgetShell>
  );
};

registerWidget<HealthSummaryConfig>({
  typeId: widgetTypeId("health-summary"),
  displayName: "Health Summary",
  description:
    "At-a-glance SPI, CPI, and SV health indicators with threshold-based color coding",
  category: "diagnostic",
  icon: <HeartOutlined />,
  sizeConstraints: {
    minW: 4,
    minH: 2,
    defaultW: 4,
    defaultH: 2,
  },
  component: HealthSummaryComponent,
  defaultConfig: {
    entityType: EntityType.PROJECT,
    goodThreshold: 1.0,
    warningThreshold: 0.9,
  },
});
