import { useState, useCallback, useEffect, useRef, type ReactNode, type CSSProperties } from "react";
import { Tree, Empty, Spin, Alert, Typography, theme } from "antd";
import {
  FolderOutlined,
  AppstoreOutlined,
  PayCircleOutlined,
  TeamOutlined,
  ScheduleOutlined,
} from "@ant-design/icons";
import type { DataNode, EventDataNode } from "antd/es/tree";
import type { Key } from "react";
import { useProject } from "@/features/projects/api/useProjects";
import type { WBSElementRead } from "@/api/generated";
import type { ControlAccountRead } from "@/api/generated";
import type { WorkPackageRead } from "@/api/generated";
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
  type: "project" | "wbs_element" | "control_account" | "work_package" | "cost_element";
  name: string;
  code?: string;
  wbs_element_id?: string;
  control_account_id?: string;
  work_package_id?: string;
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
  const [expandedKeys, setExpandedKeys] = useState<Key[]>([]);
  const initialLoadDone = useRef(false);
  /** Map from tree node key to TreeNodeData, avoids storing non-standard props on DataNode */
  const nodeMetaRef = useRef(new Map<string, TreeNodeData>());

  const {
    data: projectData,
    isLoading: projectLoading,
    error: projectError,
  } = useProject(projectId);

  // Initial load: fetch root WBS elements using root_only=true
  useEffect(() => {
    if (!projectData) return;

    let cancelled = false;

    const loadRootWBEs = async () => {
      try {
        const response = await queryClient.fetchQuery({
          queryKey: queryKeys.wbsElements.list(projectId, {
            rootOnly: true,
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
                root_only: true,
                branch: branch || "main",
                branch_mode: mode,
                as_of: asOf || undefined,
                per_page: 100,
              },
            }),
        });

        if (cancelled) return;

        const rootWBEs = extractItems(response) as WBSElementRead[];
        const projectCurrency = projectData.currency || "EUR";
        const projectDates = formatDateRange(projectData.start_date, projectData.end_date);
        const projectKey = `project-${projectData.project_id}`;

        nodeMetaRef.current.set(projectKey, {
          id: projectData.project_id,
          type: "project",
          name: projectData.name,
        });

        const wbeNodes: DataNode[] = rootWBEs.map((wbe: WBSElementRead) => {
          const key = `wbe-${wbe.wbs_element_id}`;
          nodeMetaRef.current.set(key, {
            id: wbe.wbs_element_id,
            type: "wbs_element",
            name: `${wbe.code} - ${wbe.name}`,
            code: wbe.code,
            wbs_element_id: wbe.wbs_element_id,
          });
          return {
            key,
            title: (
              <NodeTitle
                icon={<FolderOutlined style={{ color: "var(--ant-color-text-secondary)" }} />}
                name={`${wbe.code} - ${wbe.name}`}
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
          children: wbeNodes,
          isLeaf: false,
        };

        setTreeData([projectRoot]);
        if (!initialLoadDone.current) {
          setExpandedKeys([projectKey]);
          initialLoadDone.current = true;
        }
      } catch (error) {
        console.error("Error loading root WBS elements:", error);
      }
    };

    loadRootWBEs();

    return () => {
      cancelled = true;
    };
  }, [projectData, projectId, queryClient, branch, mode, asOf, showBudget, showDates]);

  const onLoadData = useCallback(
    async (treeNode: EventDataNode<DataNode>) => {
      const meta = nodeMetaRef.current.get(String(treeNode.key));
      if (!meta) return;
      if (treeNode.children && treeNode.children.length > 0) return;

      const projectCurrency = projectData?.currency || "EUR";

      try {
        if (meta.type === "wbs_element") {
          // Fetch child WBS elements (via parent_id) + ControlAccounts (via wbs_element_id)
          const [childWBEsResponse, controlAccountsResponse] = await Promise.all([
            queryClient.fetchQuery({
              queryKey: queryKeys.wbsElements.list(projectId, {
                parentId: meta.wbs_element_id,
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
                    parent_id: meta.wbs_element_id,
                    branch: branch || "main",
                    branch_mode: mode,
                    as_of: asOf || undefined,
                    per_page: 100,
                  },
                }),
            }),
            queryClient.fetchQuery({
              queryKey: queryKeys.controlAccounts.list({
                wbs_element_id: meta.wbs_element_id,
                branch,
                mode,
                asOf,
                perPage: 100,
              }),
              queryFn: () =>
                __request(OpenAPI, {
                  method: "GET",
                  url: "/api/v1/control-accounts",
                  query: {
                    wbs_element_id: meta.wbs_element_id,
                    branch: branch || "main",
                    branch_mode: mode,
                    as_of: asOf || undefined,
                    per_page: 100,
                  },
                }),
            }),
          ]);

          const childWBEs = extractItems(childWBEsResponse) as WBSElementRead[];
          const controlAccounts = extractItems(controlAccountsResponse) as ControlAccountRead[];

          const childWBENodes: DataNode[] = childWBEs.map((wbe) => {
            const key = `wbe-${wbe.wbs_element_id}`;
            nodeMetaRef.current.set(key, {
              id: wbe.wbs_element_id,
              type: "wbs_element",
              name: `${wbe.code} - ${wbe.name}`,
              code: wbe.code,
              wbs_element_id: wbe.wbs_element_id,
            });
            return {
              key,
              title: (
                <NodeTitle
                  icon={<FolderOutlined style={{ color: "var(--ant-color-text-secondary)" }} />}
                  name={`${wbe.code} - ${wbe.name}`}
                  budget={formatCurrency(wbe.budget_allocation, projectCurrency)}
                  showBudget={showBudget}
                  showDates={showDates}
                />
              ),
              isLeaf: false,
            };
          });

          const controlAccountNodes: DataNode[] = controlAccounts.map((ca) => {
            const key = `ca-${ca.control_account_id}`;
            const displayName = ca.code ? `${ca.code}` : ca.name;
            nodeMetaRef.current.set(key, {
              id: ca.control_account_id,
              type: "control_account",
              name: displayName,
              code: ca.code || undefined,
              control_account_id: ca.control_account_id,
              wbs_element_id: ca.wbs_element_id,
            });
            return {
              key,
              title: (
                <NodeTitle
                  icon={<TeamOutlined style={{ color: "var(--ant-color-info)" }} />}
                  name={displayName}
                  showBudget={showBudget}
                  showDates={showDates}
                />
              ),
              isLeaf: false,
            };
          });

          setTreeData((origin) =>
            updateTreeData(origin, treeNode.key, [...childWBENodes, ...controlAccountNodes])
          );
        } else if (meta.type === "control_account") {
          // Fetch WorkPackages by ControlAccount
          const workPackagesResponse = await queryClient.fetchQuery({
            queryKey: queryKeys.workPackages.list(meta.control_account_id, {
              branch,
              mode,
              asOf,
              perPage: 100,
            }),
            queryFn: () =>
              __request(OpenAPI, {
                method: "GET",
                url: "/api/v1/work-packages",
                query: {
                  control_account_id: meta.control_account_id,
                  branch: branch || "main",
                  branch_mode: mode,
                  as_of: asOf || undefined,
                  per_page: 100,
                },
              }),
          });

          const workPackages = extractItems(workPackagesResponse) as WorkPackageRead[];

          // Fetch schedule baselines for work packages when showDates is enabled
          const wpBaselines: Record<string, { start_date: string; end_date: string }> = {};
          if (showDates && workPackages.length > 0) {
            const baselineResults = await Promise.allSettled(
              workPackages
                .filter((wp) => wp.schedule_baseline_id)
                .map((wp) =>
                  __request(OpenAPI, {
                    method: "GET",
                    url: "/api/v1/schedule-baselines/{schedule_baseline_id}",
                    path: { schedule_baseline_id: wp.schedule_baseline_id! },
                    query: { branch: branch || "main" },
                  }).catch(() => null)
                )
            );
            let baselineIdx = 0;
            workPackages.forEach((wp) => {
              if (wp.schedule_baseline_id && baselineResults[baselineIdx]) {
                const result = baselineResults[baselineIdx];
                if (result.status === "fulfilled" && result.value) {
                  wpBaselines[wp.work_package_id] = result.value as { start_date: string; end_date: string };
                }
              }
              if (wp.schedule_baseline_id) baselineIdx++;
            });
          }

          const workPackageNodes: DataNode[] = workPackages.map((wp) => {
            const key = `wp-${wp.work_package_id}`;
            const displayName = `${wp.code} - ${wp.name}`;
            nodeMetaRef.current.set(key, {
              id: wp.work_package_id,
              type: "work_package",
              name: displayName,
              code: wp.code,
              work_package_id: wp.work_package_id,
              control_account_id: wp.control_account_id,
            });
            const baseline = wpBaselines[wp.work_package_id];
            const wpDates = baseline ? formatDateRange(baseline.start_date, baseline.end_date) : null;

            return {
              key,
              title: (
                <NodeTitle
                  icon={<ScheduleOutlined style={{ color: "var(--ant-color-text-secondary)" }} />}
                  name={displayName}
                  budget={formatCurrency(wp.budget_amount, projectCurrency)}
                  dates={wpDates}
                  showBudget={showBudget}
                  showDates={showDates}
                />
              ),
              isLeaf: false,
            };
          });

          setTreeData((origin) =>
            updateTreeData(origin, treeNode.key, workPackageNodes)
          );
        } else if (meta.type === "work_package") {
          // Fetch CostElements by WorkPackage
          const costElementsResponse = await queryClient.fetchQuery({
            queryKey: queryKeys.costElements.list(meta.work_package_id, {
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
                  work_package_id: meta.work_package_id,
                  branch: branch || "main",
                  branch_mode: mode,
                  as_of: asOf || undefined,
                  per_page: 100,
                },
              }),
          });

          const costElements = extractItems(costElementsResponse) as CostElementRead[];

          const costElementNodes: DataNode[] = costElements.map((ce) => {
            const key = `ce-${ce.cost_element_id}`;
            const ceCode = ce.cost_element_type_code || "";
            const ceDescription = ce.description || ce.cost_element_type_name || "Cost Element";
            const displayName = ceCode ? `${ceCode} - ${ceDescription}` : ceDescription;
            nodeMetaRef.current.set(key, {
              id: ce.cost_element_id,
              type: "cost_element",
              name: displayName,
              code: ceCode || undefined,
              cost_element_id: ce.cost_element_id,
              work_package_id: ce.work_package_id,
            });

            return {
              key,
              title: (
                <NodeTitle
                  icon={<PayCircleOutlined style={{ color: "var(--ant-color-success)" }} />}
                  name={displayName}
                  budget={undefined}
                  showBudget={showBudget}
                  showDates={showDates}
                />
              ),
              isLeaf: true,
            };
          });

          setTreeData((origin) =>
            updateTreeData(origin, treeNode.key, costElementNodes)
          );
        }
        // cost_element and project are leaf/root nodes - no loading needed
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

  if (projectLoading && treeData.length === 0) {
    return (
      <div style={{ display: "flex", justifyContent: "center", padding: 40 }}>
        <Spin size="large" />
      </div>
    );
  }

  if (projectError) {
    return (
      <Alert
        title="Error Loading Structure"
        description={projectError?.message}
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
      expandedKeys={expandedKeys}
      onExpand={(keys) => setExpandedKeys(keys)}
      loadData={onLoadData}
      onSelect={handleSelect}
      selectedKeys={selectedKey ? [selectedKey] : undefined}
      blockNode
    />
  );
};
