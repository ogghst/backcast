import { DashboardOutlined } from "@ant-design/icons";
import { Col, Progress, Row, Typography, theme } from "antd";
import type { FC } from "react";
import { EntityType } from "@/features/evm/types";
import { WidgetShell } from "../components/WidgetShell";
import { useWidgetEVMData } from "./shared/useWidgetEVMData";
import { registerWidget, widgetTypeId } from "..";
import type { WidgetComponentProps } from "../types";

const { Text } = Typography;

interface EVMEfficiencyGaugesConfig {
  entityType: EntityType;
  goodThreshold: number;
  warningPercent: number;
}

const EVMEfficiencyGaugesComponent: FC<
  WidgetComponentProps<EVMEfficiencyGaugesConfig>
> = ({ config, instanceId, isEditing, onRemove, onConfigure, onFullscreen, widgetType, dashboardName }) => {
  const { token } = theme.useToken();
  const { metrics, isLoading, error, entityId, refetch } = useWidgetEVMData(
    config.entityType,
  );

  return (
    <WidgetShell
      instanceId={instanceId}
      title="Efficiency Gauges"
      icon={<DashboardOutlined />}
      isEditing={isEditing}
      isLoading={isLoading}
      error={error}
      onRemove={onRemove}
      onRefresh={refetch}
      onConfigure={onConfigure}
      onFullscreen={onFullscreen}
      widgetType={widgetType}
      dashboardName={dashboardName}
    >
      {metrics ? (
        <Row gutter={[token.marginMD, token.marginMD]} justify="space-around" align="middle" style={{ height: "100%" }}>
          <Col style={{ textAlign: "center" }}>
            <Progress
              type="circle"
              percent={Math.min((metrics.cpi ?? 0) / 2 * 100, 100)}
              size={130}
              strokeColor={
                (metrics.cpi ?? 0) >= config.goodThreshold
                  ? token.colorSuccess
                  : (metrics.cpi ?? 0) >= config.goodThreshold * config.warningPercent
                    ? token.colorWarning
                    : token.colorError
              }
              format={() => (
                <div>
                  <div style={{ fontSize: token.fontSizeXL, fontWeight: 600 }}>
                    {metrics.cpi !== null ? metrics.cpi.toFixed(2) : "—"}
                  </div>
                  <div style={{ fontSize: token.fontSizeSM, color: token.colorTextSecondary }}>
                    CPI
                  </div>
                </div>
              )}
            />
            <div style={{ marginTop: token.marginSM }}>
              <Text type="secondary" style={{ fontSize: token.fontSizeSM }}>Cost Performance</Text>
            </div>
          </Col>
          <Col style={{ textAlign: "center" }}>
            <Progress
              type="circle"
              percent={Math.min((metrics.spi ?? 0) / 2 * 100, 100)}
              size={130}
              strokeColor={
                (metrics.spi ?? 0) >= config.goodThreshold
                  ? token.colorSuccess
                  : (metrics.spi ?? 0) >= config.goodThreshold * config.warningPercent
                    ? token.colorWarning
                    : token.colorError
              }
              format={() => (
                <div>
                  <div style={{ fontSize: token.fontSizeXL, fontWeight: 600 }}>
                    {metrics.spi !== null ? metrics.spi.toFixed(2) : "—"}
                  </div>
                  <div style={{ fontSize: token.fontSizeSM, color: token.colorTextSecondary }}>
                    SPI
                  </div>
                </div>
              )}
            />
            <div style={{ marginTop: token.marginSM }}>
              <Text type="secondary" style={{ fontSize: token.fontSizeSM }}>Schedule Performance</Text>
            </div>
          </Col>
        </Row>
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
              Select an entity to view efficiency gauges
            </Text>
          </div>
        )
      )}
    </WidgetShell>
  );
};

registerWidget<EVMEfficiencyGaugesConfig>({
  typeId: widgetTypeId("evm-efficiency-gauges"),
  displayName: "Efficiency Gauges",
  description: "CPI and SPI gauge visualizations with threshold-based coloring",
  category: "diagnostic",
  icon: <DashboardOutlined />,
  sizeConstraints: {
    minW: 4,
    minH: 2,
    defaultW: 4,
    defaultH: 2,
  },
  component: EVMEfficiencyGaugesComponent,
  defaultConfig: {
    entityType: EntityType.PROJECT,
    goodThreshold: 1.0,
    warningPercent: 0.9,
  },
  scope: "project",
  requiredPermission: "evm-read",
});
