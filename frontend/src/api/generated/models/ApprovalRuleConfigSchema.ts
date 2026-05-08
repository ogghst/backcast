/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Schema for an approval rule configuration.
 */
export type ApprovalRuleConfigSchema = {
    /**
     * Impact level this rule applies to
     */
    impact_level_name: string;
    /**
     * Required authority level (LOW/MEDIUM/HIGH/CRITICAL)
     */
    required_authority_level: string;
    /**
     * Role that can approve at this level
     */
    approver_role: string;
};

