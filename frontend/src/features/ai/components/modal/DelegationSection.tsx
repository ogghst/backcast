import { Checkbox, Form, Space, theme } from "antd";
import { CollapsibleCard } from "@/components/common/CollapsibleCard";
import { ToolSelectorPanel } from "../ToolSelectorPanel";
import type { AIAssistantPublic } from "../../types";

interface DelegationSectionProps {
  specialists: AIAssistantPublic[];
}

export const DelegationSection = ({ specialists }: DelegationSectionProps) => {
  const { token } = theme.useToken();

  return (
    <CollapsibleCard
      id="assistant-delegation"
      collapsed={true}
      title={
        <span style={{ fontSize: token.fontSizeLG, fontWeight: token.fontWeightStrong, color: token.colorText }}>
          Delegation
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
          name={["delegation_config", "direct_tools"]}
          label="Direct Tools"
          tooltip="Tools the main agent can use directly without delegating to specialists"
        >
          <ToolSelectorPanel />
        </Form.Item>
        <Form.Item
          name={["delegation_config", "allowed_specialists"]}
          label="Allowed Specialists"
          tooltip="Specialists this main agent can delegate to. Leave empty for all specialists."
        >
          <Checkbox.Group
            style={{ display: "flex", flexDirection: "column", gap: token.marginXS }}
          >
            {specialists
              .filter(s => s.is_active)
              .map(s => (
                <Checkbox key={s.name} value={s.name}>
                  <Space>
                    <span>{s.name}</span>
                    {s.presentation_prompt || s.description ? (
                      <span style={{ color: token.colorTextSecondary, fontSize: token.fontSizeSM }}>
                        — {s.presentation_prompt || s.description}
                      </span>
                    ) : null}
                  </Space>
                </Checkbox>
              ))}
          </Checkbox.Group>
        </Form.Item>
      </div>
    </CollapsibleCard>
  );
};
