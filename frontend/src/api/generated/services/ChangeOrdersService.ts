/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { ApprovalInfoPublic } from '../models/ApprovalInfoPublic';
import type { ChangeOrderApproval } from '../models/ChangeOrderApproval';
import type { ChangeOrderCreate } from '../models/ChangeOrderCreate';
import type { ChangeOrderPublic } from '../models/ChangeOrderPublic';
import type { ChangeOrderRecoveryRequest } from '../models/ChangeOrderRecoveryRequest';
import type { ChangeOrderUpdate } from '../models/ChangeOrderUpdate';
import type { ImpactAnalysisResponse } from '../models/ImpactAnalysisResponse';
import type { MergeRequest } from '../models/MergeRequest';
import type { CancelablePromise } from '../core/CancelablePromise';
import { OpenAPI } from '../core/OpenAPI';
import { request as __request } from '../core/request';
export class ChangeOrdersService {
    /**
     * Read Change Orders
     * Retrieve change orders for a project with pagination.
     *
     * Change Orders are always scoped to a specific project.
     * The auto-created branch for each CO is named `co-{code}`.
     *
     * Requires read permission.
     * @param projectId Filter by project ID
     * @param page Page number (1-indexed)
     * @param perPage Items per page
     * @param branch Branch name
     * @param mode Branch mode: merged (combine with main) or isolated (current branch only)
     * @param search Search term (code, title)
     * @param filters Filters in format 'column:value;column:value1,value2'
     * @param sortField Field to sort by
     * @param sortOrder Sort order (asc or desc)
     * @param asOf Time travel: get Change Orders as of this timestamp (ISO 8601)
     * @returns any Successful Response
     * @throws ApiError
     */
    public static getChangeOrders(
        projectId: string,
        page: number = 1,
        perPage: number = 20,
        branch: string = 'main',
        mode: string = 'merged',
        search?: (string | null),
        filters?: (string | null),
        sortField?: (string | null),
        sortOrder: string = 'asc',
        asOf?: (string | null),
    ): CancelablePromise<any> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/change-orders',
            query: {
                'project_id': projectId,
                'page': page,
                'per_page': perPage,
                'branch': branch,
                'mode': mode,
                'search': search,
                'filters': filters,
                'sort_field': sortField,
                'sort_order': sortOrder,
                'as_of': asOf,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Create Change Order
     * Create a new change order with automatic branch creation.
     *
     * This endpoint:
     * 1. Creates the Change Order on the main branch
     * 2. Automatically creates a `co-{code}` branch for isolated work
     * 3. Returns the created Change Order
     *
     * The auto-created branch allows changes to be developed in isolation
     * before merging to main when approved.
     *
     * Requires create permission.
     * @param requestBody
     * @returns ChangeOrderPublic Successful Response
     * @throws ApiError
     */
    public static createChangeOrder(
        requestBody: ChangeOrderCreate,
    ): CancelablePromise<ChangeOrderPublic> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/v1/change-orders',
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Read Change Order
     * Get a specific change order by change_order_id (UUID root identifier).
     *
     * Supports time-travel queries via the as_of parameter to view
     * the change order's state at any historical point in time.
     *
     * Requires read permission.
     * @param changeOrderId
     * @param branch Branch name
     * @param asOf Time travel: get change order state as of this timestamp (ISO 8601)
     * @returns ChangeOrderPublic Successful Response
     * @throws ApiError
     */
    public static getChangeOrder(
        changeOrderId: string,
        branch: string = 'main',
        asOf?: (string | null),
    ): CancelablePromise<ChangeOrderPublic> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/change-orders/{change_order_id}',
            path: {
                'change_order_id': changeOrderId,
            },
            query: {
                'branch': branch,
                'as_of': asOf,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Update Change Order
     * Update a change order's metadata.
     *
     * Creates a new version with the updated metadata. Optionally specify a branch
     * to update on a specific branch (will auto-fork from main if no version exists
     * on the target branch).
     *
     * Requires update permission.
     * @param changeOrderId
     * @param requestBody
     * @returns ChangeOrderPublic Successful Response
     * @throws ApiError
     */
    public static updateChangeOrder(
        changeOrderId: string,
        requestBody: ChangeOrderUpdate,
    ): CancelablePromise<ChangeOrderPublic> {
        return __request(OpenAPI, {
            method: 'PUT',
            url: '/api/v1/change-orders/{change_order_id}',
            path: {
                'change_order_id': changeOrderId,
            },
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Delete Change Order
     * Soft delete a change order.
     *
     * Marks the current version as deleted.
     *
     * Requires delete permission.
     * @param changeOrderId
     * @param controlDate Optional control date for deletion
     * @returns void
     * @throws ApiError
     */
    public static deleteChangeOrder(
        changeOrderId: string,
        controlDate?: (string | null),
    ): CancelablePromise<void> {
        return __request(OpenAPI, {
            method: 'DELETE',
            url: '/api/v1/change-orders/{change_order_id}',
            path: {
                'change_order_id': changeOrderId,
            },
            query: {
                'control_date': controlDate,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Read Change Order By Code
     * Get a change order by business code (e.g., "CO-2026-001").
     *
     * Returns the current active version on the specified branch.
     *
     * Requires read permission.
     * @param code
     * @param branch Branch name
     * @returns ChangeOrderPublic Successful Response
     * @throws ApiError
     */
    public static getChangeOrderByCode(
        code: string,
        branch: string = 'main',
    ): CancelablePromise<ChangeOrderPublic> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/change-orders/by-code/{code}',
            path: {
                'code': code,
            },
            query: {
                'branch': branch,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Read Change Order History
     * Get version history for a change order.
     *
     * Returns all versions across all branches, showing the complete
     * audit trail of changes.
     *
     * Requires read permission.
     * @param changeOrderId
     * @returns ChangeOrderPublic Successful Response
     * @throws ApiError
     */
    public static getChangeOrderHistory(
        changeOrderId: string,
    ): CancelablePromise<Array<ChangeOrderPublic>> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/change-orders/{change_order_id}/history',
            path: {
                'change_order_id': changeOrderId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Get Merge Conflicts
     * Check for merge conflicts between source and target branches.
     *
     * Returns a list of conflict details if conflicts exist, or an empty list if no conflicts.
     *
     * Requires read permission.
     * @param changeOrderId
     * @param sourceBranch Source branch name (e.g., 'co-123')
     * @param targetBranch Target branch name (default: 'main')
     * @returns any Successful Response
     * @throws ApiError
     */
    public static getMergeConflicts(
        changeOrderId: string,
        sourceBranch: string,
        targetBranch: string = 'main',
    ): CancelablePromise<Array<Record<string, any>>> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/change-orders/{change_order_id}/merge-conflicts',
            path: {
                'change_order_id': changeOrderId,
            },
            query: {
                'source_branch': sourceBranch,
                'target_branch': targetBranch,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Merge Change Order
     * Merge a Change Order's branch into the target branch.
     *
     * Infers the source branch from the Change Order code (e.g., `co-{code}`).
     *
     * Checks for merge conflicts before proceeding. If conflicts exist,
     * returns 409 with conflict details.
     *
     * Requires update permission.
     * @param changeOrderId
     * @param requestBody
     * @returns ChangeOrderPublic Successful Response
     * @throws ApiError
     */
    public static mergeChangeOrder(
        changeOrderId: string,
        requestBody: MergeRequest,
    ): CancelablePromise<ChangeOrderPublic> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/v1/change-orders/{change_order_id}/merge',
            path: {
                'change_order_id': changeOrderId,
            },
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Revert Change Order
     * Revert a Change Order to its previous version.
     *
     * Requires update permission.
     * @param changeOrderId
     * @param branch Branch to revert on
     * @returns ChangeOrderPublic Successful Response
     * @throws ApiError
     */
    public static revertChangeOrder(
        changeOrderId: string,
        branch: string = 'main',
    ): CancelablePromise<ChangeOrderPublic> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/v1/change-orders/{change_order_id}/revert',
            path: {
                'change_order_id': changeOrderId,
            },
            query: {
                'branch': branch,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Get Change Order Impact
     * Get impact analysis for a change order by comparing branches.
     *
     * Analyzes the financial and schedule impact of a change order by comparing
     * data between the main branch and the specified change branch.
     *
     * Modes:
     * - merged: Shows merged result (main + change delta) - most intuitive for users
     * - isolated: Shows isolated comparison (delta only) - for detailed analysis
     *
     * Returns:
     * - KPI Scorecard: BAC, Budget Delta, Gross Margin comparison
     * - Entity Changes: Added/Modified/Removed WBEs and Cost Elements
     * - Waterfall Chart: Cost bridge visualization
     * - Time Series: Weekly S-curve budget comparison
     *
     * Requires read permission.
     * @param changeOrderId
     * @param branchName Branch name to compare (e.g., 'co-CO-2026-001')
     * @param mode Comparison mode: merged (main+change) or isolated (change only)
     * @returns ImpactAnalysisResponse Successful Response
     * @throws ApiError
     */
    public static getChangeOrderImpact(
        changeOrderId: string,
        branchName: string,
        mode: string = 'merged',
    ): CancelablePromise<ImpactAnalysisResponse> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/change-orders/{change_order_id}/impact',
            path: {
                'change_order_id': changeOrderId,
            },
            query: {
                'branch_name': branchName,
                'mode': mode,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Submit Change Order For Approval
     * Submit a change order for approval with impact calculation and approver assignment.
     *
     * This endpoint:
     * 1. Calculates financial impact by comparing branches
     * 2. Determines impact level (LOW/MEDIUM/HIGH/CRITICAL)
     * 3. Assigns appropriate approver based on impact level
     * 4. Sets SLA deadline based on impact level
     * 5. Locks the branch to prevent further modifications
     * 6. Transitions status to "Submitted for Approval"
     *
     * Requires update permission.
     * @param changeOrderId
     * @param branch Branch name
     * @param comment Optional comment for audit log
     * @returns ChangeOrderPublic Successful Response
     * @throws ApiError
     */
    public static submitChangeOrderForApproval(
        changeOrderId: string,
        branch: string = 'main',
        comment?: (string | null),
    ): CancelablePromise<ChangeOrderPublic> {
        return __request(OpenAPI, {
            method: 'PUT',
            url: '/api/v1/change-orders/{change_order_id}/submit-for-approval',
            path: {
                'change_order_id': changeOrderId,
            },
            query: {
                'branch': branch,
                'comment': comment,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Approve Change Order
     * Approve a change order and transition to Approved status.
     *
     * Validates that the current user has sufficient authority to approve
     * this change order based on its impact level. Records approval with
     * optional comments in the audit log.
     *
     * Requires approve permission.
     * @param changeOrderId
     * @param requestBody
     * @param branch Branch name
     * @returns ChangeOrderPublic Successful Response
     * @throws ApiError
     */
    public static approveChangeOrder(
        changeOrderId: string,
        requestBody: ChangeOrderApproval,
        branch: string = 'main',
    ): CancelablePromise<ChangeOrderPublic> {
        return __request(OpenAPI, {
            method: 'PUT',
            url: '/api/v1/change-orders/{change_order_id}/approve',
            path: {
                'change_order_id': changeOrderId,
            },
            query: {
                'branch': branch,
            },
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Reject Change Order
     * Reject a change order and transition to Rejected status.
     *
     * Validates that the current user has sufficient authority to reject
     * this change order based on its impact level. Records rejection with
     * optional comments in the audit log and unlocks the branch.
     *
     * Requires approve permission.
     * @param changeOrderId
     * @param requestBody
     * @param branch Branch name
     * @returns ChangeOrderPublic Successful Response
     * @throws ApiError
     */
    public static rejectChangeOrder(
        changeOrderId: string,
        requestBody: ChangeOrderApproval,
        branch: string = 'main',
    ): CancelablePromise<ChangeOrderPublic> {
        return __request(OpenAPI, {
            method: 'PUT',
            url: '/api/v1/change-orders/{change_order_id}/reject',
            path: {
                'change_order_id': changeOrderId,
            },
            query: {
                'branch': branch,
            },
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Recover Change Order
     * Recover a stuck change order workflow (admin only).
     *
     * Admin-only endpoint to recover stuck workflows when impact analysis
     * fails or the change order gets stuck in an intermediate state.
     * Allows manual override of impact level and approver assignment.
     *
     * Requires change-order-recover permission (admin only).
     *
     * Args:
     * change_order_id: UUID of the stuck change order
     * recovery_data: Recovery request with impact level, approver, and reason
     *
     * Returns:
     * Updated ChangeOrder with recovered workflow state
     *
     * Raises:
     * HTTPException: If change order not stuck, invalid data, or not authorized
     * @param changeOrderId
     * @param requestBody
     * @param branch Branch name
     * @returns ChangeOrderPublic Successful Response
     * @throws ApiError
     */
    public static recoverChangeOrder(
        changeOrderId: string,
        requestBody: ChangeOrderRecoveryRequest,
        branch: string = 'main',
    ): CancelablePromise<ChangeOrderPublic> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/v1/change-orders/{change_order_id}/recover',
            path: {
                'change_order_id': changeOrderId,
            },
            query: {
                'branch': branch,
            },
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Get Change Order Approval Info
     * Get approval information for a change order.
     *
     * Returns comprehensive approval information including:
     * - Impact level and financial impact details
     * - Assigned approver details
     * - SLA tracking (assigned date, due date, status, business days remaining)
     * - Whether the current user can approve this change order
     * - Current user's authority level
     *
     * Requires read permission.
     * @param changeOrderId
     * @returns ApprovalInfoPublic Successful Response
     * @throws ApiError
     */
    public static getChangeOrderApprovalInfo(
        changeOrderId: string,
    ): CancelablePromise<ApprovalInfoPublic> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/change-orders/{change_order_id}/approval-info',
            path: {
                'change_order_id': changeOrderId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Get Pending Approvals
     * Get change orders pending approval for the current user.
     *
     * Filters change orders by:
     * - assigned_approver_id = current_user.user_id
     * - status in ("Submitted for Approval", "Under Review")
     *
     * Returns paginated list of change orders awaiting the user's approval.
     *
     * Requires read permission.
     * @param page Page number (1-indexed)
     * @param perPage Items per page
     * @returns any Successful Response
     * @throws ApiError
     */
    public static getPendingApprovals(
        page: number = 1,
        perPage: number = 20,
    ): CancelablePromise<any> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/change-orders/pending-approvals',
            query: {
                'page': page,
                'per_page': perPage,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
}
