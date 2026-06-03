import { Form, Input, Radio, Switch, theme } from "antd";
import { CollapsibleCard } from "@/components/common/CollapsibleCard";

interface GeneralSectionProps {
  isEdit: boolean;
}

export const GeneralSection = ({ isEdit }: GeneralSectionProps) => {
  const { token } = theme.useToken();

  return (
    <CollapsibleCard
      id="assistant-general"
      collapsed={false}
      title={
        <span style={{ fontSize: token.fontSizeLG, fontWeight: token.fontWeightStrong, color: token.colorText }}>
          General
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
          name="name"
          label="Name"
          rules={[
            { required: true, message: "Please enter a name" },
            { max: 255, message: "Name must be 255 characters or less" },
          ]}
        >
          <Input placeholder="My AI Assistant" />
        </Form.Item>

        <Form.Item
          name="description"
          label="Description"
          rules={[{ max: 2000, message: "Description must be 2000 characters or less" }]}
        >
          <Input.TextArea rows={2} placeholder="What does this assistant do?" />
        </Form.Item>

        <Form.Item
          name="agent_type"
          label="Agent Type"
          initialValue="specialist"
          tooltip="Main agents orchestrate specialist agents. Specialist agents focus on specific tasks."
          rules={[{ required: true, message: "Please select an agent type" }]}
        >
          <Radio.Group disabled={isEdit}>
            <Radio value="main">Main Agent</Radio>
            <Radio value="specialist">Specialist Agent</Radio>
          </Radio.Group>
        </Form.Item>

        {isEdit && (
          <Form.Item name="is_active" label="Active" valuePropName="checked">
            <Switch />
          </Form.Item>
        )}
      </div>
    </CollapsibleCard>
  );
};
