/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Entity type for EVM metrics.
 *
 * Defines the granularity level for EVM calculations:
 * - WBS_ELEMENT: WBS Element (intermediate node)
 * - CONTROL_ACCOUNT: Control Account (WBS x Org Unit intersection)
 * - WORK_PACKAGE: Work Package (PMI budget holder)
 * - COST_ELEMENT: Cost Element / EOC (leaf node)
 * - PROJECT: Project level (root node)
 */
export type app__models__schemas__evm__EntityType = 'wbs_element' | 'control_account' | 'work_package' | 'cost_element' | 'project';
