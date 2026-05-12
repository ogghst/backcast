/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Change Order workflow statuses.
 *
 * Each status has an associated Ant Design color name for UI rendering.
 * All status values are lowercase with underscores for consistency.
 */
export enum ChangeOrderStatus {
    DRAFT = 'draft',
    SUBMITTED_FOR_APPROVAL = 'submitted_for_approval',
    UNDER_REVIEW = 'under_review',
    APPROVED = 'approved',
    IMPLEMENTED = 'implemented',
    REJECTED = 'rejected',
}
