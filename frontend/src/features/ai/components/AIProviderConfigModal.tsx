import { useState } from "react";
import { Modal, Table, Button, Input, Space, Form, message, Tooltip } from "antd";
import { PlusOutlined, DeleteOutlined, InfoCircleOutlined } from "@ant-design/icons";
import type { ColumnType } from "antd/es/table";
import { useAIProviderConfigs, useSetAIProviderConfig, useDeleteAIProviderConfig } from "../api";
import type { AIProviderConfigPublic } from "../types";

interface AIProviderConfigModalProps {
  open: boolean;
  onCancel: () => void;
  providerId: string;
  providerName: string;
}

interface ConfigFormData {
  key: string;
  value: string;
}

export const AIProviderConfigModal = ({
  open,
  onCancel,
  providerId,
  providerName,
}: AIProviderConfigModalProps) => {
  const [form] = Form.useForm<ConfigFormData>();
  const [showAddForm, setShowAddForm] = useState(false);
  const { modal } = Modal.useModal();

  const { data: configs, isLoading, refetch } = useAIProviderConfigs(providerId, {
    enabled: open,
  });

  const { mutate: setConfig, isPending: isSetting } = useSetAIProviderConfig({
    onSuccess: () => {
      form.resetFields();
      setShowAddForm(false);
      refetch();
    },
  });

  const { mutate: deleteConfig } = useDeleteAIProviderConfig({
    onSuccess: () => {
      refetch();
    },
  });

  const handleAddConfig = async () => {
    try {
      const values = await form.validateFields();
      setConfig({
        providerId,
        data: {
          key: values.key,
          value: values.value,
          is_encrypted: true,
        },
      });
    } catch (error) {
      // Validation failed
    }
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
        if (record.is_encrypted && value === "***MASKED***") {
          return "****";
        }
        return value;
      },
    },
    {
      title: "Actions",
      key: "actions",
      render: (_, record) => (
        <Button
          danger
          icon={<DeleteOutlined />}
          onClick={() => handleDeleteConfig(record.key)}
          aria-label="delete"
        />
      ),
    },
  ];

  return (
    <Modal
      title={`${providerName} - Configuration`}
      open={open}
      onCancel={onCancel}
      footer={null}
      width={700}
    >
      <Space direction="vertical" style={{ width: "100%" }} size="large">
        <Button
          type="dashed"
          icon={<PlusOutlined />}
          onClick={() => setShowAddForm(!showAddForm)}
          block
        >
          {showAddForm ? "Cancel" : "Add Config"}
        </Button>

        {showAddForm && (
          <Form form={form} layout="vertical" style={{ marginTop: 16 }}>
            <Form.Item
              name="key"
              label="Config Key"
              rules={[{ required: true, message: "Please enter a config key" }]}
            >
              <Input placeholder="e.g., api_key" />
            </Form.Item>

            <Form.Item
              name="value"
              label="Config Value"
              rules={[{ required: true, message: "Please enter a config value" }]}
              extra={
                <Tooltip title="This value will be encrypted and stored securely.">
                  <InfoCircleOutlined /> Encrypted at rest
                </Tooltip>
              }
            >
              <Input.Password placeholder="Enter sensitive value" />
            </Form.Item>

            <Form.Item>
              <Button
                type="primary"
                onClick={handleAddConfig}
                loading={isSetting}
                block
              >
                Save Configuration
              </Button>
            </Form.Item>
          </Form>
        )}

        <Table
          columns={columns}
          dataSource={configs || []}
          rowKey="id"
          loading={isLoading}
          pagination={false}
          size="small"
        />
      </Space>
    </Modal>
  );
};
