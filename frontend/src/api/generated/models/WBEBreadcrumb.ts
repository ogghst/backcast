/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { ProjectBreadcrumbItem } from "./ProjectBreadcrumbItem";
import type { WBEBreadcrumbItem } from "./WBEBreadcrumbItem";
/**
 * Breadcrumb trail for a WBE showing project and ancestor path.
 */
export type WBEBreadcrumb = {
  project: ProjectBreadcrumbItem;
  /**
   * Ordered list of WBEs from root to current (last item is the current WBE)
   */
  wbe_path: Array<WBEBreadcrumbItem>;
};
