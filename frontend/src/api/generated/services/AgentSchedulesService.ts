/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { AgentScheduleCreate } from '../models/AgentScheduleCreate';
import type { AgentScheduleRead } from '../models/AgentScheduleRead';
import type { AgentScheduleTriggerResponse } from '../models/AgentScheduleTriggerResponse';
import type { AgentScheduleUpdate } from '../models/AgentScheduleUpdate';
import type { CancelablePromise } from '../core/CancelablePromise';
import { OpenAPI } from '../core/OpenAPI';
import { request as __request } from '../core/request';
export class AgentSchedulesService {
    /**
     * List Agent Schedules
     * List schedules. Owner-scoped: callers see their own schedules.
     *
     * An explicit ``owner_user_id`` query param lets an admin list another
     * owner's schedules (RBAC still gates the call).
     * @param isActive
     * @param assistantConfigId
     * @param ownerUserId
     * @returns AgentScheduleRead Successful Response
     * @throws ApiError
     */
    public static listAgentSchedules(
        isActive?: (boolean | null),
        assistantConfigId?: (string | null),
        ownerUserId?: (string | null),
    ): CancelablePromise<Array<AgentScheduleRead>> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/ai/agent-schedules',
            query: {
                'is_active': isActive,
                'assistant_config_id': assistantConfigId,
                'owner_user_id': ownerUserId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Create Agent Schedule
     * Create a schedule. Invalid cron/timezone → 422.
     * @param requestBody
     * @returns AgentScheduleRead Successful Response
     * @throws ApiError
     */
    public static createAgentSchedule(
        requestBody: AgentScheduleCreate,
    ): CancelablePromise<AgentScheduleRead> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/v1/ai/agent-schedules',
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Get Agent Schedule
     * Get a single schedule (owner-scoped).
     * @param scheduleId
     * @returns AgentScheduleRead Successful Response
     * @throws ApiError
     */
    public static getAgentSchedule(
        scheduleId: string,
    ): CancelablePromise<AgentScheduleRead> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/ai/agent-schedules/{schedule_id}',
            path: {
                'schedule_id': scheduleId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Update Agent Schedule
     * Patch a schedule (owner-scoped). Invalid cron/timezone → 422.
     * @param scheduleId
     * @param requestBody
     * @returns AgentScheduleRead Successful Response
     * @throws ApiError
     */
    public static updateAgentSchedule(
        scheduleId: string,
        requestBody: AgentScheduleUpdate,
    ): CancelablePromise<AgentScheduleRead> {
        return __request(OpenAPI, {
            method: 'PUT',
            url: '/api/v1/ai/agent-schedules/{schedule_id}',
            path: {
                'schedule_id': scheduleId,
            },
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Delete Agent Schedule
     * Delete a schedule (owner-scoped).
     * @param scheduleId
     * @returns void
     * @throws ApiError
     */
    public static deleteAgentSchedule(
        scheduleId: string,
    ): CancelablePromise<void> {
        return __request(OpenAPI, {
            method: 'DELETE',
            url: '/api/v1/ai/agent-schedules/{schedule_id}',
            path: {
                'schedule_id': scheduleId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Toggle Agent Schedule
     * Flip is_active; clear next_run_at when deactivated (owner-scoped).
     * @param scheduleId
     * @returns AgentScheduleRead Successful Response
     * @throws ApiError
     */
    public static toggleAgentSchedule(
        scheduleId: string,
    ): CancelablePromise<AgentScheduleRead> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/v1/ai/agent-schedules/{schedule_id}/toggle',
            path: {
                'schedule_id': scheduleId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Trigger Agent Schedule
     * Launch a run for a schedule ("Run now"). Owner or admin.
     *
     * Delegates to ``trigger_schedule_run`` — the same overlap-guarded launcher
     * the in-process scheduler tick uses — so manual and scheduled runs traverse
     * identical code. Authorization is by the schedule's existence (created under
     * ``agent-schedule-manage``); a later permission revocation does not silently
     * halt already-scheduled runs.
     * @param scheduleId
     * @returns AgentScheduleTriggerResponse Successful Response
     * @throws ApiError
     */
    public static triggerAgentSchedule(
        scheduleId: string,
    ): CancelablePromise<AgentScheduleTriggerResponse> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/v1/ai/agent-schedules/{schedule_id}/trigger',
            path: {
                'schedule_id': scheduleId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
}
