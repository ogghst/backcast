import { Form, Switch, Space, Typography } from "antd";
import type { ConfigFormProps } from "./ConfigFormProps";
import type { ForecastWidgetConfig } from "../../definitions/ForecastWidget";

const { Text } = Typography;

/**
 * Configuration form for Forecast widget.
 */
export function ForecastConfigForm({
  config,
  onChange,
}: ConfigFormProps<ForecastWidgetConfig>) {
  return (
    <Form layout="vertical">
      <Form.Item label="Show VAC">
        <Space direction="vertical" size="small">
          <Switch
            checked={config.showVAC}
            onChange={(checked) => onChange({ showVAC: checked })}
          />
          <Text type="secondary" style={{ fontSize: 12 }}>
            Display Variance at Completion metric
          </Text>
        </Space>
      </Form.Item>

      <Form.Item label="Show ETC">
        <Space direction="vertical" size="small">
          <Switch
            checked={config.showETC}
            onChange={(checked) => onChange({ showETC: checked })}
          />
          <Text type="secondary" style={{ fontSize: 12 }}>
            Display Estimate to Complete metric
          </Text>
        </Space>
      </Form.Item>
    </Form>
  );
}
