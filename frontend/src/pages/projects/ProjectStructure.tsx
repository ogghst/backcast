import { useState, useCallback, useEffect } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { Card, Tree, Empty, Spin, Alert, Typography } from "antd";
import type { DataNode, EventDataNode } from "antd/es/tree";
import type { Key } from "react";
import { useWBEs } from "@/features/wbes/api/useWBEs";
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
  type: "wbe" | "cost_element";
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
    if (wbesData?.items) {
      const roots = wbesData.items.map((wbe: WBERead) => ({
        key: `wbe-${wbe.wbe_id}`,
        title: (
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 8 }}>
            <Text strong>{wbe.name}</Text>
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
      setTreeData(roots);
    } else {
      setTreeData([]);
    }
  }, [wbesData]);

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
          : (childWBEsResponse as any).items || [];
        const costElements = Array.isArray(costElementsResponse)
          ? costElementsResponse
          : (costElementsResponse as any).items || [];

        const childWBENodes: DataNode[] = childWBEs.map((wbe: WBERead) => ({
          key: `wbe-${wbe.wbe_id}`,
          title: (
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 8 }}>
              <Text>{wbe.name}</Text>
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
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 8 }}>
              <Text>{ce.name}</Text>
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

      if (nodeData.type === "wbe" && projectId) {
        navigate(`/projects/${projectId}/wbes/${nodeData.id}`);
      } else if (nodeData.type === "cost_element") {
        navigate(`/cost-elements/${nodeData.id}`);
      }
    },
    [navigate, projectId]
  );

  if (wbesLoading && treeData.length === 0) {
    return (
      <Card>
        <div style={{ display: "flex", justifyContent: "center", padding: 40 }}>
          <Spin size="large" />
        </div>
      </Card>
    );
  }

  if (wbesError) {
    return (
      <Card>
        <Alert
          title="Error Loading Structure"
          description={wbesError.message}
          type="error"
          showIcon
        />
      </Card>
    );
  }

  if (!wbesData?.items || wbesData.items.length === 0) {
    return (
      <Card>
        <Empty description="No Work Breakdown Elements found for this project." />
      </Card>
    );
  }

  return (
    <Card title="Project Structure">
      <Tree
        treeData={treeData}
        showLine
        loadData={onLoadData}
        onSelect={handleSelect}
      />
    </Card>
  );
};
