import { Form, InputNumber, Switch, Space, Typography } from "antd";
import type { ConfigFormProps } from "./ConfigFormProps";

const { Text } = Typography;

export interface VarianceChartWidgetConfig {
  showThresholds?: boolean;
  thresholdPercent?: number;
}

/**
 * Configuration form for Variance Chart widget.
 */
export function VarianceChartConfigForm({
  config,
  onChange,
}: ConfigFormProps<VarianceChartWidgetConfig>) {
  return (
    <Form layout="vertical">
      <Form.Item label="Show Thresholds">
        <Space direction="vertical" size="small">
          <Switch
            checked={config.showThresholds ?? false}
            onChange={(checked) => onChange({ showThresholds: checked })}
          />
          <Text type="secondary" style={{ fontSize: 12 }}>
            Display variance threshold warning lines on the chart
          </Text>
        </Space>
      </Form.Item>

      <Form.Item
        label="Threshold Percentage"
        help="Variance percentage that triggers a warning (0-50%)"
      >
        <InputNumber
          min={0}
          max={50}
          addonAfter="%"
          value={config.thresholdPercent ?? 10}
          onChange={(value) => onChange({ thresholdPercent: value ?? 10 })}
          style={{ width: "100%" }}
          disabled={!config.showThresholds}
        />
      </Form.Item>
    </Form>
  );
}
