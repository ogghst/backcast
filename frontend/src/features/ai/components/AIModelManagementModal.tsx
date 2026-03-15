import { useState } from "react";
import { App, Modal, Table, Button, Space, Switch, Tag } from "antd";
import { PlusOutlined, EditOutlined, DeleteOutlined } from "@ant-design/icons";
import type { ColumnType } from "antd/es/table";
import { useAIModels, useCreateAIModel, useUpdateAIModel, useDeleteAIModel } from "../api";
import { AIModelModal } from "./AIModelModal";
import type { AIModelPublic } from "../types";

interface AIModelManagementModalProps {
  open: boolean;
  onCancel: () => void;
  providerId: string;
  providerName: string;
}

export const AIModelManagementModal = ({
  open,
  onCancel,
  providerId,
  providerName,
}: AIModelManagementModalProps) => {
  const [modalOpen, setModalOpen] = useState(false);
  const [selectedModel, setSelectedModel] = useState<AIModelPublic | null>(null);
  const { modal } = App.useApp();

  const { data: models, isLoading, refetch } = useAIModels(providerId, true, {
    enabled: open,
  });

  const { mutateAsync: createModel, isPending: isCreating } = useCreateAIModel({
    onSuccess: () => {
      setModalOpen(false);
      setSelectedModel(null);
      refetch();
    },
  });

  const { mutateAsync: updateModel, isPending: isUpdating } = useUpdateAIModel({
    onSuccess: () => {
      setModalOpen(false);
      setSelectedModel(null);
      refetch();
    },
  });

  const { mutate: deleteModel } = useDeleteAIModel({
    onSuccess: () => {
      refetch();
    },
  });

  const handleAddModel = () => {
    setSelectedModel(null);
    setModalOpen(true);
  };

  const handleEditModel = (model: AIModelPublic) => {
    setSelectedModel(model);
    setModalOpen(true);
  };

  const handleDeleteModel = (model: AIModelPublic) => {
    modal.confirm({
      title: "Are you sure you want to delete this model?",
      content: `This will delete "${model.display_name}". This action cannot be undone.`,
      okText: "Yes, Delete",
      okType: "danger",
      onOk: () => {
        deleteModel({ providerId, modelId: model.id });
      },
    });
  };

  const handleToggleActive = (model: AIModelPublic, checked: boolean) => {
    updateModel({
      providerId,
      modelId: model.id,
      data: { is_active: checked },
    });
  };

  const handleModelSubmit = async (values: { model_id: string; display_name: string; is_active?: boolean }) => {
    console.log("[AIModelManagementModal] handleModelSubmit called", {
      providerId,
      providerName,
      values,
      selectedModel,
    });

    if (!providerId) {
      console.error("[AIModelManagementModal] providerId is missing or invalid", { providerId });
      throw new Error("Provider ID is required");
    }

    if (selectedModel) {
      // Update existing model
      console.log("[AIModelManagementModal] Updating model", {
        providerId,
        modelId: selectedModel.id,
        data: values,
      });
      await updateModel({
        providerId,
        modelId: selectedModel.id,
        data: values,
      });
    } else {
      // Create new model
      console.log("[AIModelManagementModal] Creating model", {
        providerId,
        data: values,
      });
      await createModel({
        providerId,
        data: values,
      });
    }
  };

  const columns: ColumnType<AIModelPublic>[] = [
    {
      title: "Model ID",
      dataIndex: "model_id",
      key: "model_id",
      render: (modelId: string) => <Tag>{modelId}</Tag>,
    },
    {
      title: "Display Name",
      dataIndex: "display_name",
      key: "display_name",
    },
    {
      title: "Active",
      dataIndex: "is_active",
      key: "is_active",
      render: (isActive: boolean, record) => (
        <Switch
          checked={isActive}
          onChange={(checked) => handleToggleActive(record, checked)}
        />
      ),
    },
    {
      title: "Actions",
      key: "actions",
      render: (_, record) => (
        <Space>
          <Button
            icon={<EditOutlined />}
            onClick={() => handleEditModel(record)}
            aria-label="edit"
            title="Edit Model"
          />
          <Button
            danger
            icon={<DeleteOutlined />}
            onClick={() => handleDeleteModel(record)}
            aria-label="delete"
            title="Delete Model"
          />
        </Space>
      ),
    },
  ];

  // Validate providerId before allowing any operations
  const isValidProviderId = providerId && providerId !== "01234567-89ab-cdef-0123-456789abcdef" && providerId.length > 0;

  if (!isValidProviderId && open) {
    console.error("[AIModelManagementModal] Invalid providerId detected", {
      providerId,
      providerName,
      open,
    });
  }

  return (
    <>
      <Modal
        title={`${providerName} - Models`}
        open={open}
        onCancel={onCancel}
        footer={null}
        width={700}
        destroyOnClose
      >
        <Space direction="vertical" style={{ width: "100%" }} size="large">
          <Button
            type="primary"
            icon={<PlusOutlined />}
            onClick={handleAddModel}
            block
            disabled={!isValidProviderId}
          >
            Add Model
          </Button>

          <Table
            columns={columns}
            dataSource={models || []}
            rowKey="id"
            loading={isLoading}
            pagination={false}
            size="small"
          />
        </Space>
      </Modal>

      <AIModelModal
        open={modalOpen}
        onCancel={() => {
          setModalOpen(false);
          setSelectedModel(null);
        }}
        onOk={handleModelSubmit}
        confirmLoading={isCreating || isUpdating}
        initialValues={selectedModel}
        providerId={providerId}
      />
    </>
  );
};
