import { useState } from "react";
import { App, Button, Space, Tag, theme } from "antd";
import {
  DeleteOutlined,
  EditOutlined,
  PlusOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
} from "@ant-design/icons";
import type { ColumnType } from "antd/es/table";
import { useAIAssistants, useUpdateAIAssistant, useDeleteAIAssistant, useCreateAIAssistant, useAllAIModels } from "../api";
import { AIAssistantModal } from "./AIAssistantModal";
import { StandardTable } from "@/components/common/StandardTable";
import { useTableParams } from "@/hooks/useTableParams";
import { Can } from "@/components/auth/Can";
import type { AIAssistantPublic, AIAssistantCreate } from "../types";
import { useAIProviders } from "../api";
import { useThemeTokens } from "@/hooks/useThemeTokens";


export const AIAssistantList = () => {
  const { tableParams, handleTableChange } = useTableParams<AIAssistantPublic>();
  const { data: assistants, isLoading, refetch } = useAIAssistants(true);
  const { data: providers } = useAIProviders(true);
  const { data: models } = useAllAIModels(true);
  const { token } = theme.useToken();
  const { typography } = useThemeTokens();

  const [modalOpen, setModalOpen] = useState(false);
  const [selectedAssistant, setSelectedAssistant] = useState<AIAssistantPublic | null>(null);

  const { mutateAsync: updateAssistant } = useUpdateAIAssistant({
    onSuccess: () => {
      refetch();
      setModalOpen(false);
    },
  });

  const { mutate: deleteAssistant } = useDeleteAIAssistant({
    onSuccess: () => {
      refetch();
    },
  });

  const { mutateAsync: createAssistant } = useCreateAIAssistant({
    onSuccess: () => {
      refetch();
      setModalOpen(false);
    },
  });

  const { modal } = App.useApp();

  const handleDelete = (id: string) => {
    modal.confirm({
      title: "Are you sure you want to delete this AI assistant?",
      content: "This action cannot be undone.",
      okText: "Yes, Delete",
      okType: "danger",
      onOk: () => deleteAssistant(id),
    });
  };

  // Build a map of provider IDs to provider names
  const providerNameMap = providers?.reduce((acc, provider) => {
    acc[provider.id] = provider.name;
    return acc;
  }, {} as Record<string, string>) || {};

  // Build available models list for the modal with provider information
  const availableModels = models?.map((model) => ({
    id: model.id,
    display_name: model.display_name,
    provider_name: providerNameMap[model.provider_id] || "Unknown Provider",
    model_id: model.model_id,
  })) || [];

  const columns: ColumnType<AIAssistantPublic>[] = [
    {
      title: "Name",
      dataIndex: "name",
      key: "name",
      sorter: true,
    },
    {
      title: "Model",
      dataIndex: "model_id",
      key: "model_id",
      render: (modelId: string) => {
        const model = availableModels.find(m => m.id === modelId);
        return <Tag>{model?.display_name || modelId}</Tag>;
      },
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
                setSelectedAssistant(record);
                setModalOpen(true);
              }}
              aria-label="edit"
              title="Edit Assistant"
            />
          </Can>
          <Can permission="ai-config-delete">
            <Button
              danger
              icon={<DeleteOutlined />}
              onClick={() => handleDelete(record.id)}
              aria-label="delete"
              title="Delete Assistant"
            />
          </Can>
        </Space>
      ),
    },
  ];

  return (
    <div>
      <StandardTable<AIAssistantPublic>
        tableParams={tableParams}
        onChange={handleTableChange}
        loading={isLoading}
        dataSource={assistants || []}
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
              AI Assistants
            </div>
            <Can permission="ai-config-create">
              <Button
                type="primary"
                icon={<PlusOutlined />}
                onClick={() => {
                  setSelectedAssistant(null);
                  setModalOpen(true);
                }}
              >
                Add Assistant
              </Button>
            </Can>
          </div>
        }
      />

      <AIAssistantModal
        open={modalOpen}
        onCancel={() => setModalOpen(false)}
        onOk={async (values) => {
          if (selectedAssistant) {
            await updateAssistant({
              id: selectedAssistant.id,
              data: values,
            });
          } else {
            await createAssistant(payload as AIAssistantCreate);
          }
        }}
        confirmLoading={isLoading}
        initialValues={selectedAssistant}
        models={availableModels}
      />
    </div>
  );
};
