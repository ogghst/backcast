import { useState, useEffect } from "react";
import { App, Button, Space, Tag, Typography, theme } from "antd";
import {
  DeleteOutlined,
  EditOutlined,
  PlusOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
} from "@ant-design/icons";
import type { ColumnType } from "antd/es/table";
import { useAIProviders, useDeleteAIProvider, useCreateAIProvider } from "../api";
import { AIProviderModal } from "./AIProviderModal";
import { AIProviderConfigModal } from "./AIProviderConfigModal";
import { AIModelManagementModal } from "./AIModelManagementModal";
import { StandardTable } from "@/components/common/StandardTable";
import { useTableParams } from "@/hooks/useTableParams";
import { Can } from "@/components/auth/Can";
import type { AIProviderPublic, AIProviderCreate } from "../types";
import { useThemeTokens } from "@/hooks/useThemeTokens";

const { Text } = Typography;

export const AIProviderList = () => {
  const { tableParams, handleTableChange } = useTableParams<AIProviderPublic>();
  const { data: providers, isLoading, refetch } = useAIProviders(true);
  const { token } = theme.useToken();
  const { typography } = useThemeTokens();

  const [modalOpen, setModalOpen] = useState(false);
  const [configModalOpen, setConfigModalOpen] = useState(false);
  const [modelManagementModalOpen, setModelManagementModalOpen] = useState(false);
  const [selectedProvider, setSelectedProvider] = useState<AIProviderPublic | null>(null);

  const { mutate: deleteProvider } = useDeleteAIProvider({
    onSuccess: () => {
      refetch();
    },
  });

  const { mutateAsync: createProvider } = useCreateAIProvider({
    onSuccess: () => {
      refetch();
      setModalOpen(false);
    },
  });

  const { modal } = App.useApp();

  // Log selectedProvider changes for debugging
  useEffect(() => {
    console.log("[AIProviderList] selectedProvider changed", {
      selectedProvider,
      modelManagementModalOpen,
    });
  }, [selectedProvider, modelManagementModalOpen]);

  const handleDelete = (id: string) => {
    modal.confirm({
      title: "Are you sure you want to delete this AI provider?",
      content: "This action cannot be undone. All associated models and configurations will also be deleted.",
      okText: "Yes, Delete",
      okType: "danger",
      onOk: () => deleteProvider(id),
    });
  };

  const columns: ColumnType<AIProviderPublic>[] = [
    {
      title: "Name",
      dataIndex: "name",
      key: "name",
      sorter: true,
    },
    {
      title: "Provider Type",
      dataIndex: "provider_type",
      key: "provider_type",
      render: (type: string) => <Tag>{type}</Tag>,
      sorter: true,
    },
    {
      title: "Base URL",
      dataIndex: "base_url",
      key: "base_url",
      render: (url: string | null) =>
        url ? (
          <Text ellipsis style={{ maxWidth: 200 }}>
            {url}
          </Text>
        ) : (
          <Text type="secondary">Default</Text>
        ),
    },
    {
      title: "Active",
      dataIndex: "is_active",
      key: "is_active",
      render: (isActive: boolean) =>
        isActive ? (
          <CheckCircleOutlined style={{ color: token.colorSuccess, fontSize: typography.sizes.xl }} />
        ) : (
          <CloseCircleOutlined style={{ color: token.colorTextTertiary, fontSize: typography.sizes.xl }} />
        ),
    },
    {
      title: "Actions",
      key: "actions",
      render: (_, record) => (
        <Space>
          <Can permission="ai-config-update">
            <Button
              icon={<EditOutlined />}
              onClick={() => {
                setSelectedProvider(record);
                setModalOpen(true);
              }}
              aria-label="edit"
              title="Edit Provider"
            />
          </Can>
          <Can permission="ai-config-delete">
            <Button
              danger
              icon={<DeleteOutlined />}
              onClick={() => handleDelete(record.id)}
              aria-label="delete"
              title="Delete Provider"
            />
          </Can>
        </Space>
      ),
    },
  ];

  return (
    <div>
      <StandardTable<AIProviderPublic>
        tableParams={tableParams}
        onChange={handleTableChange}
        loading={isLoading}
        dataSource={providers || []}
        columns={columns}
        rowKey="id"
        toolbar={
          <div
            style={{
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
            }}
          >
            <div style={{ fontSize: typography.sizes.xl, fontWeight: typography.weights.bold }}>
              AI Providers
            </div>
            <Can permission="ai-config-create">
              <Button
                type="primary"
                icon={<PlusOutlined />}
                onClick={() => {
                  setSelectedProvider(null);
                  setModalOpen(true);
                }}
              >
                Add Provider
              </Button>
            </Can>
          </div>
        }
      />

      <AIProviderModal
        open={modalOpen}
        onCancel={() => setModalOpen(false)}
        onOk={async (values) => {
          if (selectedProvider) {
            await updateProvider({
              id: selectedProvider.id,
              data: values,
            });
            setModalOpen(false);
          } else {
            await createProvider(values as AIProviderCreate);
          }
        }}
        confirmLoading={isLoading}
        initialValues={selectedProvider}
        onOpenModels={() => {
          setModalOpen(false);
          setModelManagementModalOpen(true);
        }}
        onOpenConfiguration={() => {
          setModalOpen(false);
          setConfigModalOpen(true);
        }}
      />

      {selectedProvider && (
        <>
          <AIProviderConfigModal
            open={configModalOpen}
            onCancel={() => setConfigModalOpen(false)}
            providerId={selectedProvider.id}
            providerName={selectedProvider.name}
          />

          <AIModelManagementModal
            open={modelManagementModalOpen}
            onCancel={() => setModelManagementModalOpen(false)}
            providerId={selectedProvider.id}
            providerName={selectedProvider.name}
          />
        </>
      )}

      {/* Debug: Log when modal would be rendered */}
      {modelManagementModalOpen && !selectedProvider && (
        <>
          {console.error(
            "[AIProviderList] Model management modal open but no provider selected",
            { modelManagementModalOpen, selectedProvider }
          )}
        </>
      )}
    </div>
  );
};
