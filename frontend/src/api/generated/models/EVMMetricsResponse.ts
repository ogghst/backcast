/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { BranchMode } from './BranchMode';
import type { EntityType } from './EntityType';
/**
 * Generic EVM metrics response for any entity type.
 *
 * Provides a flat structure with all EVM metrics explicitly defined.
 * Supports cost_element, wbe, and project entity types.
 *
 * Metrics:
 * - BAC: Budget at Completion (total planned budget)
 * - PV: Planned Value (budgeted cost of work scheduled)
 * - AC: Actual Cost (actual cost incurred)
 * - EV: Earned Value (budgeted cost of work performed)
 * - CV: Cost Variance (EV - AC)
 * - SV: Schedule Variance (EV - PV)
 * - CPI: Cost Performance Index (EV / AC)
 * - SPI: Schedule Performance Index (EV / PV)
 * - EAC: Estimate at Completion
 * - VAC: Variance at Completion (BAC - EAC)
 * - ETC: Estimate to Complete (EAC - AC)
 *
 * This schema uses a flat structure with all metrics as individual fields,
 * not a list-based approach, for better type safety and API clarity.
 */
export type EVMMetricsResponse = {
    /**
     * Entity type (cost_element, wbe, or project)
     */
    entity_type: EntityType;
    /**
     * Entity ID (cost element, WBE, or project)
     */
    entity_id: string;
    /**
     * Budget at Completion (total planned budget)
     */
    bac: number;
    /**
     * Planned Value (budgeted cost of work scheduled)
     */
    pv: number;
    /**
     * Actual Cost (cost incurred to date)
     */
    ac: number;
    /**
     * Earned Value (budgeted cost of work performed)
     */
    ev: number;
    /**
     * Cost Variance (EV - AC, negative = over budget)
     */
    cv: number;
    /**
     * Schedule Variance (EV - PV, negative = behind schedule)
     */
    sv: number;
    /**
     * Cost Performance Index (EV / AC, < 1.0 = over budget)
     */
    cpi?: (number | null);
    /**
     * Schedule Performance Index (EV / PV, < 1.0 = behind schedule)
     */
    spi?: (number | null);
    /**
     * Estimate at Completion (projected total cost at completion)
     */
    eac?: (number | null);
    /**
     * Variance at Completion = BAC - EAC (negative = over budget)
     */
    vac?: (number | null);
    /**
     * Estimate to Complete = EAC - AC (remaining work cost)
     */
    etc?: (number | null);
    /**
     * Control date for time-travel query
     */
    control_date: string;
    /**
     * Branch name
     */
    branch: string;
    /**
     * Branch mode (ISOLATED or MERGE)
     */
    branch_mode: BranchMode;
    /**
     * Progress percentage (0-100)
     */
    progress_percentage?: (number | null);
    /**
     * Warning message (e.g., no progress reported)
     */
    warning?: (string | null);
};

