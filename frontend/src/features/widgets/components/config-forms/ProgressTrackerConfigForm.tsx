import { Form, InputNumber, Switch, Space, Typography } from "antd";
import type { ConfigFormProps } from "./ConfigFormProps";

const { Text } = Typography;

export interface ProgressTrackerWidgetConfig {
  showHistory?: boolean;
  historyLimit?: number;
}

/**
 * Configuration form for Progress Tracker widget.
 */
export function ProgressTrackerConfigForm({
  config,
  onChange,
}: ConfigFormProps<ProgressTrackerWidgetConfig>) {
  return (
    <Form layout="vertical">
      <Form.Item label="Show History">
        <Space direction="vertical" size="small">
          <Switch
            checked={config.showHistory ?? false}
            onChange={(checked) => onChange({ showHistory: checked })}
          />
          <Text type="secondary" style={{ fontSize: 12 }}>
            Display historical progress entries
          </Text>
        </Space>
      </Form.Item>

      <Form.Item
        label="History Limit"
        help="Number of historical entries to display (1-100)"
      >
        <InputNumber
          min={1}
          max={100}
          value={config.historyLimit ?? 10}
          onChange={(value) =>
            onChange({ historyLimit: value ?? 10 })
          }
          style={{ width: "100%" }}
          disabled={!config.showHistory}
        />
      </Form.Item>
    </Form>
  );
}
