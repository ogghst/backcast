import { Form, Radio, Space, Typography } from "antd";
import type { ConfigFormProps } from "./ConfigFormProps";

const { Text } = Typography;

export type BudgetStatusChartType = "bar" | "pie";

export interface BudgetStatusWidgetConfig {
  chartType?: BudgetStatusChartType;
}

/**
 * Configuration form for Budget Status widget.
 */
export function BudgetStatusConfigForm({
  config,
  onChange,
}: ConfigFormProps<BudgetStatusWidgetConfig>) {
  return (
    <Form layout="vertical">
      <Form.Item label="Chart Type">
        <Radio.Group
          value={config.chartType ?? "bar"}
          onChange={(e) => onChange({ chartType: e.target.value })}
        >
          <Space direction="vertical">
            <Radio value="bar">
              <Text>Bar Chart</Text>
              <Text
                type="secondary"
                style={{ fontSize: 12, marginLeft: 8 }}
              >
                Compare budget vs. actual side by side
              </Text>
            </Radio>
            <Radio value="pie">
              <Text>Pie Chart</Text>
              <Text
                type="secondary"
                style={{ fontSize: 12, marginLeft: 8 }}
              >
                Show budget allocation as proportions
              </Text>
            </Radio>
          </Space>
        </Radio.Group>
      </Form.Item>
    </Form>
  );
}
