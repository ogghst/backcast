import { Form, Switch, Space, Typography } from "antd";
import type { ConfigFormProps } from "./ConfigFormProps";

const { Text } = Typography;

export interface WBETreeWidgetConfig {
  showBudget?: boolean;
  showDates?: boolean;
}

/**
 * Configuration form for WBE Tree widget.
 */
export function WBETreeConfigForm({
  config,
  onChange,
}: ConfigFormProps<WBETreeWidgetConfig>) {
  return (
    <Form layout="vertical">
      <Form.Item label="Show Budget">
        <Space direction="vertical" size="small">
          <Switch
            checked={config.showBudget ?? false}
            onChange={(checked) => onChange({ showBudget: checked })}
          />
          <Text type="secondary" style={{ fontSize: 12 }}>
            Display budget information for each WBE node
          </Text>
        </Space>
      </Form.Item>

      <Form.Item label="Show Dates">
        <Space direction="vertical" size="small">
          <Switch
            checked={config.showDates ?? false}
            onChange={(checked) => onChange({ showDates: checked })}
          />
          <Text type="secondary" style={{ fontSize: 12 }}>
            Display start and end dates for each WBE node
          </Text>
        </Space>
      </Form.Item>
    </Form>
  );
}
