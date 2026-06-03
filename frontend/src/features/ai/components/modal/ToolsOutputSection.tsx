import { Form, Input, theme } from "antd";
import { CollapsibleCard } from "@/components/common/CollapsibleCard";
import { ToolSelectorPanel } from "../ToolSelectorPanel";

export const ToolsOutputSection = () => {
  const { token } = theme.useToken();

  return (
    <CollapsibleCard
      id="assistant-tools"
      collapsed={true}
      title={
        <span style={{ fontSize: token.fontSizeLG, fontWeight: token.fontWeightStrong, color: token.colorText }}>
          Tools &amp; Output
        </span>
      }
      style={{
        marginBottom: token.marginSM,
        borderRadius: token.borderRadiusLG,
        border: `1px solid ${token.colorBorder}`,
      }}
    >
      <div style={{ padding: token.paddingMD }}>
        <Form.Item
          name="allowed_tools"
          label="Allowed Tools"
          tooltip="Tools this specialist can use directly. Leave empty for all tools."
        >
          <ToolSelectorPanel />
        </Form.Item>
        <Form.Item
          name="structured_output_schema"
          label="Structured Output Schema"
          tooltip="Fully qualified class name of a Pydantic model (e.g. app.models.schemas.evm.EVMMetricsRead)"
          rules={[{ max: 100, message: "Schema must be 100 characters or less" }]}
        >
          <Input placeholder="app.models.schemas.evm.EVMMetricsRead" />
        </Form.Item>
      </div>
    </CollapsibleCard>
  );
};
