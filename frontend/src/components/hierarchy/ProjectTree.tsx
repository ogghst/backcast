import { useState, useCallback, useEffect, useRef, type ReactNode, type CSSProperties } from "react";
import { Tree, Empty, Spin, Alert, Typography, theme } from "antd";
import { FolderOutlined, AppstoreOutlined, PayCircleOutlined } from "@ant-design/icons";
import type { DataNode, EventDataNode } from "antd/es/tree";
import type { Key } from "react";
import { useWBSElements } from "@/features/wbs-elements/api/useWBSElements";
import { useProject } from "@/features/projects/api/useProjects";
import type { WBSElementRead } from "@/api/generated";
import type { CostElementRead } from "@/api/generated";
import { useQueryClient } from "@tanstack/react-query";
import { useTimeMachineParams } from "@/contexts/TimeMachineContext";
import { queryKeys } from "@/api/queryKeys";
import { request as __request } from "@/api/generated/core/request";
import { OpenAPI } from "@/api/generated/core/OpenAPI";
import { formatDate } from "@/utils/formatters";

const { Text } = Typography;

const InfoPill = ({ children, style }: { children: ReactNode; style?: CSSProperties }) => {
  const { token } = theme.useToken();
  return (
    <span style={{
      display: "inline-flex",
      alignItems: "center",
      padding: `1px ${token.paddingXS}px`,
      borderRadius: token.borderRadiusSM,
      backgroundColor: token.colorFillQuaternary,
      color: token.colorTextSecondary,
      fontSize: token.fontSizeSM,
      lineHeight: token.lineHeightSM,
      whiteSpace: "nowrap",
      ...style,
    }}>
      {children}
    </span>
  );
};

const formatCurrency = (value: string | number | undefined, currency: string = "EUR"): string => {
  if (value === undefined || value === null) return "-";
  const numValue = typeof value === "string" ? parseFloat(value) : value;
  try {
    return new Intl.NumberFormat("en-US", {
      style: "currency",
      currency,
      currencyDisplay: "narrowSymbol",
    }).format(numValue);
  } catch {
    return `${currency}${numValue}`;
  }
};

const formatDateShort = (dateStr: string | null | undefined): string | null => {
  if (!dateStr) return null;
  return formatDate(dateStr, { style: "short" });
};

const formatDateRange = (
  start: string | null | undefined,
  end: string | null | undefined,
): string | null => {
  const s = formatDateShort(start);
  const e = formatDateShort(end);
  if (s && e) return `${s} → ${e}`;
  if (s) return `from ${s}`;
  if (e) return `until ${e}`;
  return null;
};

export interface TreeNodeData {
  id: string;
  type: "project" | "wbs_element" | "cost_element";
  name: string;
  // Entity-specific IDs for better type safety
  wbs_element_id?: string;
  cost_element_id?: string;
}

const updateTreeData = (
  list: DataNode[],
  key: Key,
  children: DataNode[],
): DataNode[] =>
  list.map((node) => {
    if (node.key === key) {
      return { ...node, children };
    }
    if (node.children) {
      return { ...node, children: updateTreeData(node.children, key, children) };
    }
    return node;
  });

export interface ProjectTreeProps {
  projectId: string;
  onSelect?: (node: TreeNodeData) => void;
  selectedKey?: string | null;
  /** Show budget amounts on nodes. Default: true */
  showBudget?: boolean;
  /** Show schedule baseline date ranges on nodes. Default: false */
  showDates?: boolean;
}

/** Node title component that renders icon, name, budget, and dates. */
const NodeTitle = ({
  icon,
  name,
  strong,
  budget,
  dates,
  showBudget,
  showDates,
}: {
  icon: ReactNode;
  name: string;
  strong?: boolean;
  budget?: string;
  dates?: string | null;
  showBudget: boolean;
  showDates: boolean;
}) => {
  const showRight = (showBudget && budget) || (showDates && dates);
  return (
    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 8, flex: 1 }}>
      <div style={{ display: "flex", alignItems: "center", gap: 8, minWidth: 0 }}>
        {icon}
        <Text strong={strong} ellipsis style={{ minWidth: 0 }}>{name}</Text>
      </div>
      {showRight ? (
        <div style={{ display: "flex", gap: 8, alignItems: "center", flexShrink: 0 }}>
          {showBudget && budget && <InfoPill>{budget}</InfoPill>}
          {showDates && dates && <InfoPill>{dates}</InfoPill>}
        </div>
      ) : null}
    </div>
  );
};

/**
 * Extract items from an API response that may be an array or paginated object.
 */
// eslint-disable-next-line @typescript-eslint/no-explicit-any
const extractItems = (response: any): any[] => {
  if (Array.isArray(response)) return response;
  if (response?.items) return response.items;
  return [];
};

export const ProjectTree = ({
  projectId,
  onSelect,
  selectedKey,
  showBudget = true,
  showDates = false,
}: ProjectTreeProps) => {
  const queryClient = useQueryClient();
  const { branch, mode, asOf } = useTimeMachineParams();

  const [treeData, setTreeData] = useState<DataNode[]>([]);
  /** Map from tree node key to TreeNodeData, avoids storing non-standard props on DataNode */
  const nodeMetaRef = useRef(new Map<string, TreeNodeData>());

  const {
    data: projectData,
    isLoading: projectLoading,
    error: projectError,
  } = useProject(projectId);

  const {
    data: wbesData,
    isLoading: wbesLoading,
    error: wbesError,
  } = useWBSElements({
    projectId,
    parentWbsElementId: "null",
  });

  useEffect(() => {
    if (projectData && wbesData?.items) {
      const projectDates = formatDateRange(projectData.start_date, projectData.end_date);
      const projectCurrency = projectData.currency || "EUR";
      const projectKey = `project-${projectData.project_id}`;
      nodeMetaRef.current.set(projectKey, {
        id: projectData.project_id,
        type: "project",
        name: projectData.name,
      });

      const wbeRoots: DataNode[] = wbesData.items.map((wbe: WBSElementRead) => {
        const key = `wbe-${wbe.wbs_element_id}`;
        nodeMetaRef.current.set(key, {
          id: wbe.wbs_element_id,
          type: "wbs_element",
          name: wbe.name,
          wbs_element_id: wbe.wbs_element_id,
        });
        return {
          key,
          title: (
            <NodeTitle
              icon={<FolderOutlined style={{ color: "var(--ant-color-text-secondary)" }} />}
              name={wbe.name}
              strong
              budget={formatCurrency(wbe.budget_allocation, projectCurrency)}
              showBudget={showBudget}
              showDates={showDates}
            />
          ),
          isLeaf: false,
        };
      });

      const projectRoot: DataNode = {
        key: projectKey,
        title: (
          <NodeTitle
            icon={<AppstoreOutlined style={{ color: "var(--ant-color-primary)" }} />}
            name={`${projectData.code} - ${projectData.name}`}
            strong
            budget={formatCurrency(projectData.budget, projectCurrency)}
            dates={projectDates}
            showBudget={showBudget}
            showDates={showDates}
          />
        ),
        children: wbeRoots,
        isLeaf: false,
      };

      setTreeData([projectRoot]);
    } else {
      setTreeData([]);
    }
  }, [wbesData, projectData, showBudget, showDates]);

  const onLoadData = useCallback(
    async (treeNode: EventDataNode<DataNode>) => {
      const meta = nodeMetaRef.current.get(String(treeNode.key));

      if (meta?.type !== "wbs_element") return;
      if (treeNode.children && treeNode.children.length > 0) return;

      try {
        const projectCurrency = projectData?.currency || "EUR";
        const [childWBEsResponse, costElementsResponse] = await Promise.all([
          queryClient.fetchQuery({
            queryKey: queryKeys.wbsElements.list(projectId, {
              parentWbsElementId: meta.id,
              branch,
              mode,
              asOf,
              perPage: 100,
            }),
            queryFn: () =>
              __request(OpenAPI, {
                method: "GET",
                url: "/api/v1/wbs-elements",
                query: {
                  project_id: projectId,
                  parent_wbs_element_id: meta.id,
                  branch: branch || "main",
                  mode,
                  as_of: asOf || undefined,
                  per_page: 100,
                },
              }),
            staleTime: 0, // Always refetch to ensure we get the correct children for this parent
          }),
          queryClient.fetchQuery({
            queryKey: queryKeys.costElements.list(undefined, {
              wbs_element_id: meta.id,
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
                  wbs_element_id: meta.id,
                  branch: branch || "main",
                  mode,
                  as_of: asOf || undefined,
                  per_page: 100,
                },
              }),
          }),
        ]);

        const childWBEs = extractItems(childWBEsResponse) as WBSElementRead[];
        const costElements = extractItems(costElementsResponse) as CostElementRead[];

        // Fetch schedule baselines for cost elements when showDates is enabled
        const baselines: Record<string, { start_date: string; end_date: string }> = {};
        if (showDates && costElements.length > 0) {
          const baselineResults = await Promise.allSettled(
            costElements.map((ce) =>
              __request(OpenAPI, {
                method: "GET",
                url: "/api/v1/cost-elements/{cost_element_id}/schedule-baseline",
                path: { cost_element_id: ce.cost_element_id },
                query: { branch: branch || "main" },
              }).catch(() => null)
            )
          );
          baselineResults.forEach((result, idx) => {
            if (result.status === "fulfilled" && result.value) {
              const ce = costElements[idx];
              baselines[ce.cost_element_id] = result.value as { start_date: string; end_date: string };
            }
          });
        }

        const childWBENodes: DataNode[] = childWBEs.map((wbe) => {
          const key = `wbe-${wbe.wbs_element_id}`;
          nodeMetaRef.current.set(key, {
            id: wbe.wbs_element_id,
            type: "wbs_element",
            name: wbe.name,
            wbs_element_id: wbe.wbs_element_id,
          });
          return {
            key,
            title: (
              <NodeTitle
                icon={<FolderOutlined style={{ color: "var(--ant-color-text-secondary)" }} />}
                name={wbe.name}
                budget={formatCurrency(wbe.budget_allocation, projectCurrency)}
                showBudget={showBudget}
                showDates={showDates}
              />
            ),
            isLeaf: false,
          };
        });

        const costElementNodes: DataNode[] = costElements.map((ce) => {
          const key = `ce-${ce.cost_element_id}`;
          nodeMetaRef.current.set(key, {
            id: ce.cost_element_id,
            type: "cost_element",
            name: ce.cost_element_type_name || ce.description || "Cost Element",
            cost_element_id: ce.cost_element_id,
          });
          const baseline = baselines[ce.cost_element_id];
          const ceDates = baseline ? formatDateRange(baseline.start_date, baseline.end_date) : null;

          return {
            key,
            title: (
              <NodeTitle
                icon={<PayCircleOutlined style={{ color: "var(--ant-color-success)" }} />}
                name={ce.cost_element_type_name || ce.description || "Cost Element"}
                budget={ce.amount ? formatCurrency(ce.amount, projectCurrency) : undefined}
                dates={ceDates}
                showBudget={showBudget}
                showDates={showDates}
              />
            ),
            isLeaf: true,
          };
        });

        setTreeData((origin) =>
          updateTreeData(origin, treeNode.key, [...childWBENodes, ...costElementNodes])
        );
      } catch (error) {
        console.error("Error loading children:", error);
      }
    },
    [projectId, queryClient, branch, mode, asOf, showBudget, showDates, projectData],
  );

  const handleSelect = useCallback(
    (_selectedKeys: Key[], info: { node: EventDataNode<DataNode> }) => {
      const meta = nodeMetaRef.current.get(String(info.node.key));
      if (meta) {
        onSelect?.(meta);
      }
    },
    [onSelect],
  );

  if ((wbesLoading || projectLoading) && treeData.length === 0) {
    return (
      <div style={{ display: "flex", justifyContent: "center", padding: 40 }}>
        <Spin size="large" />
      </div>
    );
  }

  if (wbesError || projectError) {
    return (
      <Alert
        title="Error Loading Structure"
        description={(wbesError || projectError)?.message}
        type="error"
        showIcon
      />
    );
  }

  if (!projectData) {
    return <Empty description="No Project found." />;
  }

  return (
    <Tree
      treeData={treeData}
      showLine
      defaultExpandAll
      loadData={onLoadData}
      onSelect={handleSelect}
      selectedKeys={selectedKey ? [selectedKey] : undefined}
      blockNode
    />
  );
};
