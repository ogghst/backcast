/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */

/**
 * Properties required for creating a Cost Element.
 */
export type CostElementCreate = {
  code: string;
  name: string;
  budget_amount: number | string;
  description?: string | null;
  wbe_id: string;
  cost_element_type_id: string;
  control_date?: string | null;
};
