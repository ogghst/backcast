/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */

/**
 * Schema for reading project data.
 */
export type ProjectRead = {
  /**
   * Project name
   */
  name: string;
  /**
   * Unique project code
   */
  code: string;
  /**
   * Project budget
   */
  budget: string;
  /**
   * Contract value
   */
  contract_value?: string | null;
  /**
   * Project start date
   */
  start_date?: string | null;
  /**
   * Project end date
   */
  end_date?: string | null;
  /**
   * Description
   */
  description?: string | null;
  id: string;
  project_id: string;
  branch: string;
  created_at?: string | null;
};
