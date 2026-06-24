/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { ApprovalRuleConfigSchema } from './ApprovalRuleConfigSchema';
import type { CustomFieldDefinition } from './CustomFieldDefinition';
import type { ImpactLevelConfigSchema_Output } from './ImpactLevelConfigSchema_Output';
import type { ImpactWeightsSchema_Output } from './ImpactWeightsSchema_Output';
import type { ScoreBoundariesSchema_Output } from './ScoreBoundariesSchema_Output';
import type { SLARuleConfigSchema_Output } from './SLARuleConfigSchema_Output';
import type { WorkflowTransitionsSchema } from './WorkflowTransitionsSchema';
/**
 * Response schema for workflow configuration.
 */
export type WorkflowConfigResponse = {
    /**
     * Config record ID
     */
    id: string;
    /**
     * Root config UUID
     */
    config_id: string;
    /**
     * Project ID (null for global config)
     */
    project_id?: (string | null);
    /**
     * Whether this config is active
     */
    is_active: boolean;
    /**
     * Optimistic locking version
     */
    version: number;
    /**
     * User who created this config
     */
    created_by: string;
    created_by_name?: (string | null);
    /**
     * User who last updated this config
     */
    updated_by?: (string | null);
    /**
     * When created
     */
    created_at: string;
    /**
     * When last updated
     */
    updated_at: string;
    /**
     * Impact level configurations
     */
    impact_levels: Array<ImpactLevelConfigSchema_Output>;
    /**
     * Approval rules
     */
    approval_rules: Array<ApprovalRuleConfigSchema>;
    /**
     * SLA rules
     */
    sla_rules: Array<SLARuleConfigSchema_Output>;
    /**
     * Impact calculation weights
     */
    impact_weights: ImpactWeightsSchema_Output;
    /**
     * Score-to-impact-level boundaries
     */
    score_boundaries: ScoreBoundariesSchema_Output;
    /**
     * Workflow transition configuration
     */
    workflow_transitions?: (WorkflowTransitionsSchema | null);
    /**
     * ISO 3166-1 alpha-2 country code for holiday calendar
     */
    holiday_country_code?: (string | null);
    /**
     * Custom field definitions for change orders
     */
    custom_fields?: (Array<CustomFieldDefinition> | null);
};

