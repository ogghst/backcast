/**
 * TemplateManagementModal
 *
 * Modal for saving the current dashboard as a template and managing existing templates.
 * Provides CRUD operations for dashboard layout templates via TanStack Query mutations.
 */

import { useState, useCallback } from "react";
import {
  Modal,
  Typography,
  Select,
  Input,
  Button,
  Space,
  Divider,
  List,
  Popconfirm,
  message,
} from "antd";
import { SaveOutlined, DeleteOutlined, LockOutlined } from "@ant-design/icons";
import { useDashboardCompositionStore } from "@/stores/useDashboardCompositionStore";
import {
  useDashboardLayoutTemplates,
  useCreateDashboardLayout,
  useUpdateDashboardTemplate,
  useDeleteDashboardLayout,
} from "@/features/widgets/api/useDashboardLayouts";

const { Text } = Typography;

/** Sentinel value for the "New template..." select option. */
const NEW_TEMPLATE_VALUE = "__new__";

interface TemplateManagementModalProps {
  /** Whether the modal is open. */
  open: boolean;
  /** Callback when the modal requests to close. */
  onClose: () => void;
}

/**
 * Modal for managing dashboard layout templates.
 *
 * Section 1: Save the current dashboard widgets as a new or existing template.
 * Section 2: List and delete existing templates.
 */
export function TemplateManagementModal({
  open,
  onClose,
}: TemplateManagementModalProps) {
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [newName, setNewName] = useState("");

  useDashboardCompositionStore((s) => s.activeDashboard);

  const { data: templates = [] } = useDashboardLayoutTemplates();

  const createMutation = useCreateDashboardLayout();
  const updateMutation = useUpdateDashboardTemplate();
  const deleteMutation = useDeleteDashboardLayout();

  const selectedTemplate =
    selectedId && selectedId !== NEW_TEMPLATE_VALUE
      ? templates.find((t) => t.id === selectedId)
      : undefined;

  const canSave =
    selectedId === NEW_TEMPLATE_VALUE
      ? newName.trim().length > 0
      : !!selectedId;

  const isSaving = createMutation.isPending || updateMutation.isPending;

  const handleSave = useCallback(async () => {
    const currentWidgets = useDashboardCompositionStore.getState().activeDashboard?.widgets ?? [];
    const serialized = currentWidgets.map((w) => ({
      instanceId: w.instanceId,
      typeId: w.typeId,
      config: w.config,
      layout: w.layout,
    }));

    try {
      if (selectedId === NEW_TEMPLATE_VALUE) {
        await createMutation.mutateAsync({
          name: newName.trim(),
          is_template: true,
          widgets: serialized,
        });
        message.success("Template created");
      } else if (selectedId) {
        await updateMutation.mutateAsync({
          id: selectedId,
          data: { widgets: serialized },
        });
        message.success("Template updated");
      }
      setSelectedId(null);
      setNewName("");
    } catch {
      message.error("Failed to save template");
    }
  }, [selectedId, newName, createMutation, updateMutation]);

  const handleSelectChange = useCallback((value: string) => {
    setSelectedId(value);
    setNewName("");
  }, []);

  return (
    <Modal
      title="Manage Templates"
      open={open}
      onCancel={onClose}
      footer={null}
      width={560}
      destroyOnHidden
    >
      {/* Section 1: Save as Template */}
      <Typography.Title level={5}>Save as Template</Typography.Title>
      <Space orientation="vertical" style={{ width: "100%" }}>
        <Select
          style={{ width: "100%" }}
          placeholder="Select template..."
          value={selectedId ?? undefined}
          onChange={handleSelectChange}
          allowClear
        >
          <Select.Option value={NEW_TEMPLATE_VALUE}>
            New template...
          </Select.Option>
          {templates.map((t) => (
            <Select.Option key={t.id} value={t.id}>
              {t.name}
            </Select.Option>
          ))}
        </Select>
        {selectedId === NEW_TEMPLATE_VALUE && (
          <Input
            placeholder="Template name"
            value={newName}
            onChange={(e) => setNewName(e.target.value)}
          />
        )}
        {selectedId && selectedId !== NEW_TEMPLATE_VALUE && selectedTemplate && (
          <div>
            <LockOutlined style={{ marginRight: 8 }} />
            <Text>{selectedTemplate.name}</Text>
          </div>
        )}
        <Button
          icon={<SaveOutlined />}
          disabled={!canSave}
          loading={isSaving}
          onClick={handleSave}
        >
          Save
        </Button>
      </Space>

      <Divider />

      {/* Section 2: Manage Templates */}
      <Typography.Title level={5}>Manage Templates</Typography.Title>
      {templates.length === 0 ? (
        <Text type="secondary">No templates</Text>
      ) : (
        <List
          dataSource={templates}
          renderItem={(template) => (
            <List.Item
              actions={[
                <Popconfirm
                  key="delete"
                  title="Delete this template?"
                  onConfirm={() => deleteMutation.mutateAsync(template.id)}
                >
                  <Button
                    icon={<DeleteOutlined />}
                    danger
                    size="small"
                    aria-label={`Delete ${template.name}`}
                  />
                </Popconfirm>,
              ]}
            >
              <List.Item.Meta
                title={template.name}
                description={`${template.widgets.length} widgets`}
              />
            </List.Item>
          )}
        />
      )}
    </Modal>
  );
}
