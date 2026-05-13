import React, { useMemo, useCallback } from "react";
import {
  Card,
  Collapse,
  Button,
  Typography,
  Row,
  Col,
  Divider,
  theme,
} from "antd";
import { LineChartOutlined } from "@ant-design/icons";

import { MetricCard } from "./MetricCard";
import { EVMCompactSCurve } from "./EVMCompactSCurve";
import { EVMKPIIndicator } from "./EVMKPIIndicator";
import { EVMForecastBar } from "./EVMForecastBar";
import {
  EVMMetricsResponse,
  EVMTimeSeriesResponse,
  getMetricStatus,
  METRIC_DEFINITIONS,
} from "../types";

const { Title, Text } = Typography;

export interface EVMSummaryViewProps {
  metrics: EVMMetricsResponse;
  timeSeries?: EVMTimeSeriesResponse;
  onAdvanced?: () => void;
  hideHeader?: boolean;
}

const DETAIL_METRICS = ["sv", "cv", "ac", "etc"] as const;

function getEACStatus(
  eac: number | null,
  bac: number,
): "good" | "warning" | "bad" {
  if (eac === null) return "warning";
  if (eac <= bac) return "good";
  if (eac <= bac * 1.1) return "warning";
  return "bad";
}

export const EVMSummaryView: React.FC<EVMSummaryViewProps> = ({
  metrics,
  timeSeries,
  onAdvanced,
  hideHeader = false,
}) => {
  const { token } = theme.useToken();

  const handleAdvancedClick = useCallback(() => {
    onAdvanced?.();
  }, [onAdvanced]);

  const collapseItems = useMemo(
    () => [
      {
        key: "detail",
        label: <Text style={{ fontWeight: 500 }}>Detail Metrics</Text>,
        children: (
          <Row gutter={[16, 16]}>
            {DETAIL_METRICS.map((key) => {
              const metadata = METRIC_DEFINITIONS[key];
              if (!metadata) return null;
              const value = metrics[key] as number | null;
              const status = getMetricStatus(key, value);
              return (
                <Col xs={24} sm={12} lg={8} key={key}>
                  <MetricCard
                    metadata={metadata}
                    value={value}
                    status={status}
                    size="small"
                  />
                </Col>
              );
            })}
          </Row>
        ),
      },
    ],
    [metrics],
  );

  return (
    <Card
      variant="borderless"
      style={{
        backgroundColor: token.colorBgContainer,
        borderRadius: token.borderRadiusLG,
      }}
      styles={{ body: { padding: token.paddingLG } }}
    >
      <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
        {!hideHeader && (
          <div
            style={{
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
            }}
          >
            <Title level={4} style={{ margin: 0 }}>
              EVM Summary
            </Title>
            <Button
              type="default"
              icon={<LineChartOutlined />}
              onClick={handleAdvancedClick}
            >
              Advanced
            </Button>
          </div>
        )}

        <EVMCompactSCurve timeSeries={timeSeries} height={220} />

        <Divider style={{ margin: 0 }} />

        <div
          style={{
            display: "flex",
            flexWrap: "wrap",
            gap: 16,
          }}
        >
          <EVMKPIIndicator
            label="CPI"
            value={metrics.cpi}
            format="number"
            status={getMetricStatus("cpi", metrics.cpi)}
          />
          <EVMKPIIndicator
            label="SPI"
            value={metrics.spi}
            format="number"
            status={getMetricStatus("spi", metrics.spi)}
          />
          <EVMKPIIndicator
            label="BAC"
            value={metrics.bac}
            format="currency"
            status="good"
            neutral
          />
          <EVMKPIIndicator
            label="EAC"
            value={metrics.eac}
            format="currency"
            status={getEACStatus(metrics.eac, metrics.bac)}
          />
          <EVMKPIIndicator
            label="VAC"
            value={metrics.vac}
            format="currency"
            status={getMetricStatus("vac", metrics.vac)}
          />
          <EVMKPIIndicator
            label="Progress"
            value={metrics.progress_percentage / 100}
            format="percentage"
            status="good"
            neutral
          />
        </div>

        <Divider style={{ margin: 0 }} />

        <EVMForecastBar
          bac={metrics.bac}
          eac={metrics.eac}
          ac={metrics.ac}
          etc={metrics.etc}
          vac={metrics.vac}
        />

        <Collapse
          ghost
          items={collapseItems}
          style={{ backgroundColor: "transparent" }}
        />
      </div>
    </Card>
  );
};

export default EVMSummaryView;
