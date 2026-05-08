/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { ApprovalRuleConfigSchema } from './ApprovalRuleConfigSchema';
import type { CustomFieldDefinition } from './CustomFieldDefinition';
import type { ImpactLevelConfigSchema_Input } from './ImpactLevelConfigSchema_Input';
import type { ImpactWeightsSchema_Input } from './ImpactWeightsSchema_Input';
import type { ScoreBoundariesSchema_Input } from './ScoreBoundariesSchema_Input';
import type { SLARuleConfigSchema_Input } from './SLARuleConfigSchema_Input';
import type { WorkflowTransitionsSchema } from './WorkflowTransitionsSchema';
/**
 * Request schema for creating/updating workflow configuration.
 */
export type WorkflowConfigUpdateRequest = {
    /**
     * Impact level configurations (exactly 4)
     */
    impact_levels: Array<ImpactLevelConfigSchema_Input>;
    /**
     * Approval rules (one per impact level)
     */
    approval_rules: Array<ApprovalRuleConfigSchema>;
    /**
     * SLA rules (one per impact level)
     */
    sla_rules: Array<SLARuleConfigSchema_Input>;
    /**
     * Impact calculation weights
     */
    impact_weights: ImpactWeightsSchema_Input;
    /**
     * Score-to-impact-level boundaries
     */
    score_boundaries: ScoreBoundariesSchema_Input;
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

