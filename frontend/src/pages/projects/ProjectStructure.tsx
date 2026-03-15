import { useState, useCallback, useEffect } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { Card, Tree, Empty, Spin, Alert, Typography } from "antd";
import { FolderOutlined, AppstoreOutlined, PayCircleOutlined } from "@ant-design/icons";
import type { DataNode, EventDataNode } from "antd/es/tree";
import type { Key } from "react";
import { useWBEs } from "@/features/wbes/api/useWBEs";
import { useProject } from "@/features/projects/api/useProjects";
import type { WBERead } from "@/api/generated";
import type { CostElementRead } from "@/api/generated";
import { useQueryClient } from "@tanstack/react-query";
import { useTimeMachineParams } from "@/contexts/TimeMachineContext";
import { queryKeys } from "@/api/queryKeys";
import { request as __request } from "@/api/generated/core/request";
import { OpenAPI } from "@/api/generated/core/OpenAPI";

const { Text } = Typography;

const formatCurrency = (value: string | number | undefined): string => {
  if (value === undefined || value === null) return "€0.00";
  const numValue = typeof value === "string" ? parseFloat(value) : value;
  return new Intl.NumberFormat("en-IE", {
    style: "currency",
    currency: "EUR",
  }).format(numValue);
};

interface TreeNodeData {
  id: string;
  type: "project" | "wbe" | "cost_element";
  name: string;
}

const updateTreeData = (list: DataNode[], key: Key, children: DataNode[]): DataNode[] => {
  return list.map((node) => {
    if (node.key === key) {
      return {
        ...node,
        children,
      };
    }
    if (node.children) {
      return {
        ...node,
        children: updateTreeData(node.children, key, children),
      };
    }
    return node;
  });
};

export const ProjectStructure = () => {
  const { projectId } = useParams<{ projectId: string }>();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { branch, mode, asOf } = useTimeMachineParams();

  const [treeData, setTreeData] = useState<DataNode[]>([]);

  // Fetch Project Details
  const {
    data: projectData,
    isLoading: projectLoading,
    error: projectError
  } = useProject(projectId);

  // Fetch root WBEs (parent_wbe_id is null or undefined)
  const {
    data: wbesData,
    isLoading: wbesLoading,
    error: wbesError,
  } = useWBEs({
    projectId,
    parentWbeId: "null", // Fetch only root WBEs
  });

  useEffect(() => {
    if (projectData && wbesData?.items) {
      const wbeRoots = wbesData.items.map((wbe: WBERead) => ({
        key: `wbe-${wbe.wbe_id}`,
        title: (
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 8, flex: 1 }}>
            <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
              <FolderOutlined style={{ color: "var(--ant-color-text-secondary)" }} />
              <Text strong>{wbe.name}</Text>
            </div>
            <Text type="secondary">{formatCurrency(wbe.budget_allocation)}</Text>
          </div>
        ),
        isLeaf: false,
        data: {
          id: wbe.wbe_id,
          type: "wbe" as const,
          name: wbe.name,
        } as TreeNodeData,
      }));

      // Wrap WBEs under a root Project node
      const projectRoot: DataNode = {
        key: `project-${projectData.project_id}`,
        title: (
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 8, flex: 1 }}>
            <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
              <AppstoreOutlined style={{ color: "var(--ant-color-primary)" }} />
              <Text strong>{projectData.code} - {projectData.name}</Text>
            </div>
          </div>
        ),
        children: wbeRoots,
        isLeaf: false, // The project is never a leaf if it can hold structure
        data: {
          id: projectData.project_id,
          type: "project" as const,
          name: projectData.name,
        } as TreeNodeData,
      };

      // Derive tree data from query results - this is a valid use of setState in effect
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setTreeData([projectRoot]);
    } else {
      setTreeData([]);
    }
  }, [wbesData, projectData]);
  const onLoadData = useCallback(
    async (treeNode: EventDataNode<DataNode>) => {
      const nodeData = treeNode.data as TreeNodeData;

      if (nodeData.type !== "wbe") {
        return;
      }

      // If already loaded
      if (treeNode.children && treeNode.children.length > 0) {
        return;
      }

      try {
        const childWBEsPromise = queryClient.fetchQuery({
          queryKey: queryKeys.wbes.list(projectId || "", {
            parentWbeId: nodeData.id,
            branch,
            mode,
            asOf,
            perPage: 100, // Reasonable max
          }),
          queryFn: () =>
            __request(OpenAPI, {
              method: "GET",
              url: "/api/v1/wbes",
              query: {
                project_id: projectId,
                parent_wbe_id: nodeData.id,
                branch: branch || "main",
                mode: mode,
                as_of: asOf || undefined,
                per_page: 100,
              },
            }),
        });

        const costElementsPromise = queryClient.fetchQuery({
          queryKey: queryKeys.costElements.list({
            wbe_id: nodeData.id,
            branch,
            mode,
            asOf,
            perPage: 100,
          }),
          queryFn: () =>
            __request(OpenAPI, {
              method: "GET",
              url: "/api/v1/cost-elements",
              query: {
                wbe_id: nodeData.id,
                branch: branch || "main",
                mode: mode,
                as_of: asOf || undefined,
                per_page: 100,
              },
            }),
        });

        const [childWBEsResponse, costElementsResponse] = await Promise.all([
          childWBEsPromise,
          costElementsPromise,
        ]);

        const childWBEs = Array.isArray(childWBEsResponse)
          ? childWBEsResponse
          : (childWBEsResponse as { items?: typeof childWBEsResponse }).items || [];
        const costElements = Array.isArray(costElementsResponse)
          ? costElementsResponse
          : (costElementsResponse as { items?: typeof costElementsResponse }).items || [];

        const childWBENodes: DataNode[] = childWBEs.map((wbe: WBERead) => ({
          key: `wbe-${wbe.wbe_id}`,
          title: (
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 8, flex: 1 }}>
              <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                <FolderOutlined style={{ color: "var(--ant-color-text-secondary)" }} />
                <Text>{wbe.name}</Text>
              </div>
              <Text type="secondary">{formatCurrency(wbe.budget_allocation)}</Text>
            </div>
          ),
          isLeaf: false,
          data: {
            id: wbe.wbe_id,
            type: "wbe" as const,
            name: wbe.name,
          } as TreeNodeData,
        }));

        const costElementNodes: DataNode[] = costElements.map((ce: CostElementRead) => ({
          key: `ce-${ce.cost_element_id}`,
          title: (
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 8, flex: 1 }}>
              <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                <PayCircleOutlined style={{ color: "var(--ant-color-success)" }} />
                <Text>{ce.name}</Text>
              </div>
              <Text type="secondary">{formatCurrency(ce.budget_amount)}</Text>
            </div>
          ),
          isLeaf: true,
          data: {
            id: ce.cost_element_id,
            type: "cost_element" as const,
            name: ce.name,
          } as TreeNodeData,
        }));

        const allChildren = [...childWBENodes, ...costElementNodes];

        setTreeData((origin) =>
          updateTreeData(origin, treeNode.key, allChildren)
        );
      } catch (error) {
        console.error("Error loading children:", error);
      }
    },
    [projectId, queryClient, branch, mode, asOf]
  );

  const handleSelect = useCallback(
    (_selectedKeys: Key[], info: { node: EventDataNode<DataNode> }) => {
      const nodeData = info.node.data as TreeNodeData;

      // Navigate based on node type
      if (nodeData.type === "project" && projectId) {
        navigate(`/projects/${projectId}/overview`);
      } else if (nodeData.type === "wbe" && projectId) {
        navigate(`/projects/${projectId}/wbes/${nodeData.id}`);
      } else if (nodeData.type === "cost_element") {
        navigate(`/cost-elements/${nodeData.id}`);
      }
    },
    [navigate, projectId]
  );

  if ((wbesLoading || projectLoading) && treeData.length === 0) {
    return (
      <Card>
        <div style={{ display: "flex", justifyContent: "center", padding: 40 }}>
          <Spin size="large" />
        </div>
      </Card>
    );
  }

  if (wbesError || projectError) {
    return (
      <Card>
        <Alert
          title="Error Loading Structure"
          description={(wbesError || projectError)?.message}
          type="error"
          showIcon
        />
      </Card>
    );
  }

  if (!projectData) {
    return (
      <Card>
        <Empty description="No Project found." />
      </Card>
    );
  }

  return (
    <Card title="Project Structure">
      <Tree
        treeData={treeData}
        showLine
        defaultExpandAll={true} // Since the root node is just one, let's expand it by default to reveal the first WBEs
        loadData={onLoadData}
        onSelect={handleSelect}
        blockNode
      />
    </Card>
  );
};
