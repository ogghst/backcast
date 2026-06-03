import { useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import { queryKeys as qk } from "@/api/queryKeys";
import { OrganizationalUnitsService } from "@/api/generated/services/OrganizationalUnitsService";
import type { OrganizationalUnitRead } from "@/api/generated";
import {
  buildOrgUnitTreeData,
  getOrgUnitPath,
} from "../utils/orgUnitTree";

export interface OrgUnitTreeResult {
  items: OrganizationalUnitRead[];
  treeData: ReturnType<typeof buildOrgUnitTreeData>;
  flatMap: Map<string, OrganizationalUnitRead>;
  pathMap: Map<string, string>;
  isLoading: boolean;
}

/**
 * Hook to fetch and structure org unit tree data.
 * Returns both raw items and tree-structured data for antd Tree/TreeSelect.
 */
export function useOrgUnitTree(): OrgUnitTreeResult {
  const { data: items = [], isLoading } = useQuery({
    queryKey: qk.organizationalUnits.tree,
    queryFn: () => OrganizationalUnitsService.getOrganizationalUnitTree(),
    staleTime: 5 * 60 * 1000,
  });

  const treeData = useMemo(
    () => buildOrgUnitTreeData(items),
    [items],
  );

  const flatMap = useMemo(
    () =>
      new Map(
        items.map((item) => [item.organizational_unit_id, item]),
      ),
    [items],
  );

  const pathMap = useMemo(
    () =>
      new Map(
        items.map((item) => [
          item.organizational_unit_id,
          getOrgUnitPath(item.organizational_unit_id, items, flatMap),
        ]),
      ),
    [items, flatMap],
  );

  return { items, treeData, flatMap, pathMap, isLoading };
}
