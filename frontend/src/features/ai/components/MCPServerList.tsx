import { useState } from "react";
import { App, Button, Space, Tag, Typography, theme, List } from "antd";
import {
  DeleteOutlined,
  EditOutlined,
  PlusOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  ApiOutlined,
  ToolOutlined,
} from "@ant-design/icons";
import type { ColumnType } from "antd/es/table";
import {
  useMCPServers,
  useCreateMCPServer,
  useUpdateMCPServer,
  useDeleteMCPServer,
  useTestMCPServer,
  useMCPServerTools,
} from "../api/useMCPQuery";
import { MCPServerModal } from "./MCPServerModal";
import { StandardTable } from "@/components/common/StandardTable";
import { useTableParams } from "@/hooks/useTableParams";
import { Can } from "@/components/auth/Can";
import type { MCPServerPublic, MCPServerCreate } from "../types";
import { useThemeTokens } from "@/hooks/useThemeTokens";

const { Text } = Typography;

const ExpandedToolsRow = ({ serverId }: { serverId: string }) => {
  const { data: tools, isLoading } = useMCPServerTools(serverId);
  const { token } = theme.useToken();

  if (isLoading) {
    return <Text type="secondary">Loading tools...</Text>;
  }

  if (!tools || tools.length === 0) {
    return <Text type="secondary">No tools discovered</Text>;
  }

  return (
    <div style={{ padding: token.paddingSM }}>
      <Text strong style={{ marginBottom: token.marginXS, display: "block" }}>
        Discovered Tools ({tools.length}):
      </Text>
      <List
        size="small"
        dataSource={tools}
        renderItem={(tool) => (
          <List.Item>
            <Text code>{tool.name}</Text>
            {tool.description && (
              <Text type="secondary" style={{ marginLeft: token.marginSM }}>
                {tool.description}
              </Text>
            )}
          </List.Item>
        )}
      />
    </div>
  );
};

export const MCPServerList = () => {
  const { tableParams, handleTableChange } = useTableParams<MCPServerPublic>();
  const { data: servers, isLoading, refetch } = useMCPServers(true);
  const { token } = theme.useToken();
  const { typography } = useThemeTokens();

  const [modalOpen, setModalOpen] = useState(false);
  const [selectedServer, setSelectedServer] = useState<MCPServerPublic | null>(null);
  const [testResults, setTestResults] = useState<Record<string, number>>({});

  const { mutate: deleteServer } = useDeleteMCPServer({
    onSuccess: () => refetch(),
  });

  const { mutateAsync: createServer, isPending: isCreating } = useCreateMCPServer({
    onSuccess: () => {
      refetch();
      setModalOpen(false);
    },
  });

  const { mutateAsync: updateServer, isPending: isUpdating } = useUpdateMCPServer({
    onSuccess: () => {
      refetch();
      setModalOpen(false);
    },
  });

  const { mutate: testConnection, isPending: isTesting } = useTestMCPServer();

  const { modal } = App.useApp();

  const handleDelete = (id: string) => {
    modal.confirm({
      title: "Are you sure you want to delete this MCP server?",
      content: "This action cannot be undone.",
      okText: "Yes, Delete",
      okType: "danger",
      onOk: () => deleteServer(id),
    });
  };

  const handleTestConnection = (server: MCPServerPublic) => {
    testConnection(server.id, {
      onSuccess: (tools) => {
        setTestResults((prev) => ({ ...prev, [server.id]: tools.length }));
        modal.info({
          title: `Connection Test: ${server.name}`,
          content: (
            <div>
              <p>Successfully connected. Discovered {tools.length} tool(s):</p>
              <List
                size="small"
                dataSource={tools}
                renderItem={(tool) => (
                  <List.Item>
                    <Text code>{tool.name}</Text>
                    {tool.description && (
                      <Text type="secondary" style={{ marginLeft: 8 }}>
                        {tool.description}
                      </Text>
                    )}
                  </List.Item>
                )}
              />
            </div>
          ),
          width: 600,
        });
      },
    });
  };

  const columns: ColumnType<MCPServerPublic>[] = [
    {
      title: "Name",
      dataIndex: "name",
      key: "name",
      sorter: true,
    },
    {
      title: "Transport",
      key: "transport",
      render: (_, record) => {
        const transport = record.config?.transport as string | undefined;
        if (!transport) return <Text type="secondary">Unknown</Text>;
        return <Tag>{transport}</Tag>;
      },
    },
    {
      title: "Active",
      dataIndex: "is_active",
      key: "is_active",
      render: (isActive: boolean) =>
        isActive ? (
          <CheckCircleOutlined
            style={{ color: token.colorSuccess, fontSize: typography.sizes.xl }}
          />
        ) : (
          <CloseCircleOutlined
            style={{ color: token.colorTextTertiary, fontSize: typography.sizes.xl }}
          />
        ),
    },
    {
      title: "Tools",
      key: "tools_count",
      render: (_, record) => {
        const count = testResults[record.id];
        if (count !== undefined) {
          return <Tag icon={<ToolOutlined />}>{count} tools</Tag>;
        }
        return <Text type="secondary">--</Text>;
      },
    },
    {
      title: "Actions",
      key: "actions",
      render: (_, record) => (
        <Space>
          <Button
            icon={<ApiOutlined />}
            onClick={() => handleTestConnection(record)}
            loading={isTesting}
            title="Test Connection"
            aria-label="test connection"
          />
          <Can permission="ai-config-update">
            <Button
              icon={<EditOutlined />}
              onClick={() => {
                setSelectedServer(record);
                setModalOpen(true);
              }}
              aria-label="edit"
              title="Edit Server"
            />
          </Can>
          <Can permission="ai-config-delete">
            <Button
              danger
              icon={<DeleteOutlined />}
              onClick={() => handleDelete(record.id)}
              aria-label="delete"
              title="Delete Server"
            />
          </Can>
        </Space>
      ),
    },
  ];

  return (
    <div>
      <StandardTable<MCPServerPublic>
        tableParams={tableParams}
        onChange={handleTableChange}
        loading={isLoading}
        dataSource={servers || []}
        columns={columns}
        rowKey="id"
        expandable={{
          expandedRowRender: (record) => <ExpandedToolsRow serverId={record.id} />,
          rowExpandable: (record) => record.is_active,
        }}
        toolbar={
          <div
            style={{
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
            }}
          >
            <div
              style={{ fontSize: typography.sizes.xl, fontWeight: typography.weights.bold }}
            >
              MCP Servers
            </div>
            <Can permission="ai-config-create">
              <Button
                type="primary"
                icon={<PlusOutlined />}
                onClick={() => {
                  setSelectedServer(null);
                  setModalOpen(true);
                }}
              >
                Add Server
              </Button>
            </Can>
          </div>
        }
      />

      <MCPServerModal
        open={modalOpen}
        onCancel={() => setModalOpen(false)}
        onOk={async (values) => {
          if (selectedServer) {
            await updateServer({
              id: selectedServer.id,
              data: values,
            });
          } else {
            await createServer(values as MCPServerCreate);
          }
        }}
        confirmLoading={selectedServer ? isUpdating : isCreating}
        initialValues={selectedServer}
      />
    </div>
  );
};
