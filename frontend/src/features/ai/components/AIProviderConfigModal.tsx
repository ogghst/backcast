import { useState, useMemo } from "react";
import { App, Modal, Table, Button, Input, Space, Form, Select, Tooltip } from "antd";
import { PlusOutlined, DeleteOutlined, EditOutlined, InfoCircleOutlined } from "@ant-design/icons";
import type { ColumnType } from "antd/es/table";
import { useAIProviderConfigs, useSetAIProviderConfig, useDeleteAIProviderConfig } from "../api";
import type { AIProviderConfigPublic } from "../types";
import { useThemeTokens } from "@/hooks/useThemeTokens";

interface AIProviderConfigModalProps {
  open: boolean;
  onCancel: () => void;
  providerId: string;
  providerName: string;
  providerType: string;
}

interface ConfigFormData {
  key: string;
  value: string;
}

const DEEPSEEK_SETTINGS = [
  { key: "reasoning_effort", label: "Reasoning Effort", options: ["high", "max"], description: "Controls reasoning depth (default: high)" },
  { key: "thinking_mode", label: "Thinking Mode", options: ["enabled", "disabled"], description: "Chain-of-thought reasoning mode (default: enabled)" },
] as const;

export const AIProviderConfigModal = ({
  open,
  onCancel,
  providerId,
  providerName,
  providerType,
}: AIProviderConfigModalProps) => {
  const [form] = Form.useForm<ConfigFormData>();
  const [showAddForm, setShowAddForm] = useState(false);
  const [editingConfig, setEditingConfig] = useState<AIProviderConfigPublic | null>(null);
  const [deepseekOverrides, setDeepseekOverrides] = useState<Record<string, string>>({});
  const { modal } = App.useApp();
  const { spacing } = useThemeTokens();

  const isDeepseek = providerType === "deepseek";

  const { data: configs, isLoading, refetch } = useAIProviderConfigs(providerId, {
    enabled: open,
  });

  const { mutate: setConfig, isPending: isSetting } = useSetAIProviderConfig({
    onSuccess: () => {
      form.resetFields();
      setShowAddForm(false);
      setEditingConfig(null);
      refetch();
    },
  });

  const { mutate: deleteConfig } = useDeleteAIProviderConfig({
    onSuccess: () => {
      refetch();
    },
  });

  // Derive DeepSeek settings from loaded configs + local overrides
  const deepseekSettings = useMemo(() => {
    if (!configs || !isDeepseek) return {};
    const settings: Record<string, string> = {};
    for (const setting of DEEPSEEK_SETTINGS) {
      const config = configs.find((c) => c.key === setting.key);
      settings[setting.key] = deepseekOverrides[setting.key] ?? config?.value ?? setting.options[0];
    }
    return settings;
  }, [configs, isDeepseek, deepseekOverrides]);

  const handleDeepseekSettingChange = (key: string, value: string) => {
    setDeepseekOverrides((prev) => ({ ...prev, [key]: value }));
    setConfig({
      providerId,
      data: { key, value, is_encrypted: false },
    });
  };

  const handleAddConfig = async () => {
    try {
      const values = await form.validateFields();
      setConfig({
        providerId,
        data: {
          key: editingConfig?.key || values.key,
          value: values.value,
          is_encrypted: true,
        },
      });
    } catch {
      // Validation failed
    }
  };

  const handleEditConfig = (config: AIProviderConfigPublic) => {
    setEditingConfig(config);
    setShowAddForm(true);
    form.setFieldsValue({
      key: config.key,
      value: "", // Don't pre-fill value for security - user must re-enter
    });
  };

  const handleCancelEdit = () => {
    setShowAddForm(false);
    setEditingConfig(null);
    form.resetFields();
  };

  const handleModalCancel = () => {
    handleCancelEdit();
    onCancel();
  };

  const handleDeleteConfig = (key: string) => {
    modal.confirm({
      title: "Are you sure you want to delete this configuration?",
      content: "This action cannot be undone.",
      okText: "Yes, Delete",
      okType: "danger",
      onOk: () => {
        deleteConfig({ providerId, key });
      },
    });
  };

  // Filter out DeepSeek-managed keys from the generic table
  const deepseekKeys = new Set(DEEPSEEK_SETTINGS.map((s) => s.key));
  const genericConfigs = isDeepseek
    ? (configs || []).filter((c) => !deepseekKeys.has(c.key))
    : configs || [];

  const columns: ColumnType<AIProviderConfigPublic>[] = [
    {
      title: "Key",
      dataIndex: "key",
      key: "key",
    },
    {
      title: (
        <span>
          Value{" "}
          <Tooltip title="API keys are encrypted at rest for security. Masked values are shown as ****.">
            <InfoCircleOutlined />
          </Tooltip>
        </span>
      ),
      dataIndex: "value",
      key: "value",
      render: (value, record) => {
        if (record.is_encrypted) {
          return "****";
        }
        return value;
      },
    },
    {
      title: "Actions",
      key: "actions",
      render: (_, record) => (
        <Space>
          <Button
            icon={<EditOutlined />}
            onClick={() => handleEditConfig(record)}
            aria-label="edit"
            title="Edit Config"
          />
          <Button
            danger
            icon={<DeleteOutlined />}
            onClick={() => handleDeleteConfig(record.key)}
            aria-label="delete"
            title="Delete Config"
          />
        </Space>
      ),
    },
  ];

  return (
    <Modal
      title={`${providerName} - Configuration`}
      open={open}
      onCancel={handleModalCancel}
      footer={null}
      width={700}
      destroyOnHidden
    >
      <Space direction="vertical" style={{ width: "100%" }} size="large">
        {isDeepseek && (
          <div style={{ marginBottom: spacing.md }}>
            <h4 style={{ marginBottom: spacing.sm }}>DeepSeek Settings</h4>
            <Space direction="vertical" style={{ width: "100%" }} size="middle">
              {DEEPSEEK_SETTINGS.map((setting) => (
                <div key={setting.key}>
                  <div style={{ marginBottom: 4 }}>
                    <span>{setting.label}</span>
                    <Tooltip title={setting.description}>
                      <InfoCircleOutlined style={{ marginLeft: 4, color: "var(--ant-color-text-secondary)" }} />
                    </Tooltip>
                  </div>
                  <Select
                    value={deepseekSettings[setting.key] || setting.options[0]}
                    onChange={(value) => handleDeepseekSettingChange(setting.key, value)}
                    style={{ width: "100%" }}
                    options={setting.options.map((opt) => ({ value: opt, label: opt }))}
                  />
                </div>
              ))}
            </Space>
          </div>
        )}

        <Button
          type="dashed"
          icon={<PlusOutlined />}
          onClick={() => {
            if (showAddForm) {
              handleCancelEdit();
            } else {
              setShowAddForm(true);
              setEditingConfig(null);
            }
          }}
          block
        >
          {showAddForm ? "Cancel" : "Add Config"}
        </Button>

        {showAddForm && (
          <Form form={form} layout="vertical" style={{ marginTop: spacing.md }}>
            <Form.Item
              name="key"
              label="Config Key"
              rules={[{ required: true, message: "Please enter a config key" }]}
            >
              <Input
                placeholder="e.g., api_key"
                disabled={!!editingConfig}
              />
            </Form.Item>

            <Form.Item
              name="value"
              label={editingConfig ? "New Value" : "Config Value"}
              rules={[{ required: true, message: "Please enter a config value" }]}
              extra={
                <Tooltip title="This value will be encrypted and stored securely.">
                  <InfoCircleOutlined /> Encrypted at rest
                </Tooltip>
              }
            >
              <Input.Password
                placeholder={editingConfig ? "Enter new value" : "Enter sensitive value"}
              />
            </Form.Item>

            <Form.Item>
              <Button
                type="primary"
                onClick={handleAddConfig}
                loading={isSetting}
                block
              >
                {editingConfig ? "Update Configuration" : "Save Configuration"}
              </Button>
            </Form.Item>
          </Form>
        )}

        <Table
          columns={columns}
          dataSource={genericConfigs}
          rowKey="id"
          loading={isLoading}
          pagination={false}
          size="small"
        />
      </Space>
    </Modal>
  );
};
