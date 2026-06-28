/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { EVMMetricsResponse } from './EVMMetricsResponse';
import type { PortfolioProjectMetrics } from './PortfolioProjectMetrics';
/**
 * Response for ``GET /api/v1/evm/portfolio``.
 *
 * Combines a rolled-up portfolio summary (industry-standard 'roll up, never
 * average' across the accessible project set) with a per-project breakdown
 * and the SPI-based at-risk subset.
 *
 * Currency assumption: every monetary value is expressed in the project base
 * currency (EUR) via ``convert_to_base`` applied per project at
 * ``control_date``. Today all projects are EUR so conversion is a no-op, but
 * the path is wired for the multi-currency case.
 */
export type PortfolioEVMResponse = {
    /**
     * Rolled-up portfolio EVM metrics
     */
    summary: EVMMetricsResponse;
    /**
     * Per-project breakdown of the accessible portfolio
     */
    projects: Array<PortfolioProjectMetrics>;
    /**
     * Subset of ``projects`` where SPI is present and < 0.9 (the interim at-risk / delayed proxy)
     */
    at_risk_projects: Array<PortfolioProjectMetrics>;
    /**
     * Control date used for the time-travel EVM query
     */
    control_date: string;
};

