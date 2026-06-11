import { Alert, Form, Input, theme } from "antd";
import { CollapsibleCard } from "@/components/common/CollapsibleCard";

export const PlanningStrategySection = () => {
  const { token } = theme.useToken();

  return (
    <CollapsibleCard
      id="assistant-planning"
      collapsed={true}
      title={
        <span style={{ fontSize: token.fontSizeLG, fontWeight: token.fontWeightStrong, color: token.colorText }}>
          Planning Strategy
        </span>
      }
      style={{
        marginBottom: token.marginSM,
        borderRadius: token.borderRadiusLG,
        border: `1px solid ${token.colorBorder}`,
      }}
    >
      <div style={{ padding: token.paddingMD }}>
        <Alert
          message="Advanced"
          description="Customize how the AI plans and decomposes requests into specialist tasks. Leave blank to use the default planner. The {specialist_section} placeholder is replaced with the dynamic specialist list."
          type="info"
          showIcon
          style={{ marginBottom: token.marginMD }}
        />
        <Form.Item
          name="planner_prompt"
          label="Planner Prompt"
          tooltip="Controls how the AI decomposes user requests into specialist tasks. Include {specialist_section} for the dynamic specialist list."
          rules={[{ max: 10000, message: "Planner prompt must be 10000 characters or less" }]}
        >
          <Input.TextArea
            rows={8}
            placeholder="Leave blank to use the default planner strategy..."
          />
        </Form.Item>
        <Form.Item
          name="supervisor_prompt"
          label="Supervisor Prompt"
          tooltip="Controls how the supervisor agent coordinates specialist delegation. Include {specialist_section} for the dynamic specialist list. Leave blank to use the system prompt or default."
          rules={[{ max: 10000, message: "Supervisor prompt must be 10000 characters or less" }]}
        >
          <Input.TextArea
            rows={8}
            placeholder="Leave blank to use the system prompt or default supervisor..."
          />
        </Form.Item>
      </div>
    </CollapsibleCard>
  );
};
