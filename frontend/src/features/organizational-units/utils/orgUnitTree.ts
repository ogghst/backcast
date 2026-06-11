import type { DefaultOptionType } from "antd/es/select";
import type { OrganizationalUnitRead } from "@/api/generated";

/** Data node for antd Tree (no value field). */
export interface OrgUnitTreeNode {
  key: string;
  title: React.ReactNode | string;
  children?: OrgUnitTreeNode[];
}

/** Data node for antd TreeSelect (includes value field). */
export interface OrgUnitTreeSelectNode extends DefaultOptionType {
  key: string;
  value: string;
  title: string;
  children?: OrgUnitTreeSelectNode[];
}

/**
 * Build antd Tree data nodes from flat org unit list.
 * Groups by parent_unit_id (null = root), recurses children.
 */
export function buildOrgUnitTreeData(
  items: OrganizationalUnitRead[],
): OrgUnitTreeNode[] {
  const childrenMap = new Map<string, OrganizationalUnitRead[]>();
  const roots: OrganizationalUnitRead[] = [];

  for (const item of items) {
    if (!item.parent_unit_id) {
      roots.push(item);
    } else {
      const children = childrenMap.get(item.parent_unit_id) || [];
      children.push(item);
      childrenMap.set(item.parent_unit_id, children);
    }
  }

  const toNode = (item: OrganizationalUnitRead): OrgUnitTreeNode => ({
    key: item.organizational_unit_id,
    title: `${item.code} — ${item.name}`,
    children: (
      childrenMap.get(item.organizational_unit_id) || []
    ).map(toNode),
  });

  return roots.map(toNode);
}

/**
 * Build antd TreeSelect data nodes from flat org unit list.
 * Titles show hierarchy path for clarity.
 */
export function buildOrgUnitTreeSelectData(
  items: OrganizationalUnitRead[],
  excludeIds?: Set<string>,
): OrgUnitTreeSelectNode[] {
  // Build filtered idMap once — excluded IDs are removed
  const idMap = new Map<string, OrganizationalUnitRead>();
  for (const item of items) {
    if (excludeIds?.has(item.organizational_unit_id)) continue;
    idMap.set(item.organizational_unit_id, item);
  }

  // Build tree structure from filtered map
  const childrenMap = new Map<string, OrganizationalUnitRead[]>();
  const roots: OrganizationalUnitRead[] = [];

  for (const item of idMap.values()) {
    if (!item.parent_unit_id || !idMap.has(item.parent_unit_id)) {
      roots.push(item);
    } else {
      const children = childrenMap.get(item.parent_unit_id) || [];
      children.push(item);
      childrenMap.set(item.parent_unit_id, children);
    }
  }

  const toNode = (item: OrganizationalUnitRead): OrgUnitTreeSelectNode => {
    const path = getOrgUnitPath(item.organizational_unit_id, items, idMap);
    return {
      key: item.organizational_unit_id,
      value: item.organizational_unit_id,
      title: path,
      children: (
        childrenMap.get(item.organizational_unit_id) || []
      ).map(toNode),
    };
  };

  return roots.map(toNode);
}

/**
 * Resolve the full hierarchy path for an org unit (e.g., "Engineering / Mechanical Engineering").
 * Walks up parent_unit_id chain from the target unit.
 */
export function getOrgUnitPath(
  unitId: string,
  items: OrganizationalUnitRead[],
  idMap?: Map<string, OrganizationalUnitRead>,
): string {
  const map = idMap ?? new Map(items.map((item) => [item.organizational_unit_id, item]));

  const path: string[] = [];
  let currentId: string | null | undefined = unitId;

  while (currentId) {
    const unit = map.get(currentId);
    if (!unit) break;
    path.unshift(unit.name);
    currentId = unit.parent_unit_id;
  }

  return path.join(" / ");
}

/**
 * Get all descendant IDs of a given org unit (for exclusion in TreeSelect).
 */
export function getDescendantIds(
  unitId: string,
  items: OrganizationalUnitRead[],
): Set<string> {
  const childrenMap = new Map<string, string[]>();
  for (const item of items) {
    if (item.parent_unit_id) {
      const children = childrenMap.get(item.parent_unit_id) || [];
      children.push(item.organizational_unit_id);
      childrenMap.set(item.parent_unit_id, children);
    }
  }

  const descendants = new Set<string>();
  const queue = [...(childrenMap.get(unitId) || [])];
  while (queue.length > 0) {
    const id = queue.shift()!;
    if (descendants.has(id)) continue;
    descendants.add(id);
    queue.push(...(childrenMap.get(id) || []));
  }

  return descendants;
}
