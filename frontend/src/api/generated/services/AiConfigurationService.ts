/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { AIAssistantConfigCreate } from '../models/AIAssistantConfigCreate';
import type { AIAssistantConfigPublic } from '../models/AIAssistantConfigPublic';
import type { AIAssistantConfigUpdate } from '../models/AIAssistantConfigUpdate';
import type { AIModelCreate } from '../models/AIModelCreate';
import type { AIModelPublic } from '../models/AIModelPublic';
import type { AIProviderConfigCreate } from '../models/AIProviderConfigCreate';
import type { AIProviderConfigPublic } from '../models/AIProviderConfigPublic';
import type { AIProviderCreate } from '../models/AIProviderCreate';
import type { AIProviderPublic } from '../models/AIProviderPublic';
import type { AIProviderUpdate } from '../models/AIProviderUpdate';
import type { CancelablePromise } from '../core/CancelablePromise';
import { OpenAPI } from '../core/OpenAPI';
import { request as __request } from '../core/request';
export class AiConfigurationService {
    /**
     * List Providers
     * List all AI providers.
     * @param includeInactive
     * @returns AIProviderPublic Successful Response
     * @throws ApiError
     */
    public static listAiProviders(
        includeInactive: boolean = false,
    ): CancelablePromise<Array<AIProviderPublic>> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/ai/config/providers',
            query: {
                'include_inactive': includeInactive,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Create Provider
     * Create a new AI provider.
     * @param requestBody
     * @returns AIProviderPublic Successful Response
     * @throws ApiError
     */
    public static createAiProvider(
        requestBody: AIProviderCreate,
    ): CancelablePromise<AIProviderPublic> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/v1/ai/config/providers',
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Update Provider
     * Update an AI provider.
     * @param providerId
     * @param requestBody
     * @returns AIProviderPublic Successful Response
     * @throws ApiError
     */
    public static updateAiProvider(
        providerId: string,
        requestBody: AIProviderUpdate,
    ): CancelablePromise<AIProviderPublic> {
        return __request(OpenAPI, {
            method: 'PUT',
            url: '/api/v1/ai/config/providers/{provider_id}',
            path: {
                'provider_id': providerId,
            },
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Delete Provider
     * Delete an AI provider.
     * @param providerId
     * @returns void
     * @throws ApiError
     */
    public static deleteAiProvider(
        providerId: string,
    ): CancelablePromise<void> {
        return __request(OpenAPI, {
            method: 'DELETE',
            url: '/api/v1/ai/config/providers/{provider_id}',
            path: {
                'provider_id': providerId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * List Provider Configs
     * List all configs for a provider.
     * @param providerId
     * @returns AIProviderConfigPublic Successful Response
     * @throws ApiError
     */
    public static listProviderConfigs(
        providerId: string,
    ): CancelablePromise<Array<AIProviderConfigPublic>> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/ai/config/providers/{provider_id}/configs',
            path: {
                'provider_id': providerId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Set Provider Config
     * Set a provider config value.
     * @param providerId
     * @param requestBody
     * @returns AIProviderConfigPublic Successful Response
     * @throws ApiError
     */
    public static setProviderConfig(
        providerId: string,
        requestBody: AIProviderConfigCreate,
    ): CancelablePromise<AIProviderConfigPublic> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/v1/ai/config/providers/{provider_id}/configs',
            path: {
                'provider_id': providerId,
            },
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Delete Provider Config
     * Delete a provider config.
     * @param providerId
     * @param key
     * @returns void
     * @throws ApiError
     */
    public static deleteProviderConfig(
        providerId: string,
        key: string,
    ): CancelablePromise<void> {
        return __request(OpenAPI, {
            method: 'DELETE',
            url: '/api/v1/ai/config/providers/{provider_id}/configs/{key}',
            path: {
                'provider_id': providerId,
                'key': key,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * List Provider Models
     * List all models for a provider.
     * @param providerId
     * @param includeInactive
     * @returns AIModelPublic Successful Response
     * @throws ApiError
     */
    public static listProviderModels(
        providerId: string,
        includeInactive: boolean = false,
    ): CancelablePromise<Array<AIModelPublic>> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/ai/config/providers/{provider_id}/models',
            path: {
                'provider_id': providerId,
            },
            query: {
                'include_inactive': includeInactive,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Create Model
     * Create a new AI model for a provider.
     * @param providerId
     * @param requestBody
     * @returns AIModelPublic Successful Response
     * @throws ApiError
     */
    public static createAiModel(
        providerId: string,
        requestBody: AIModelCreate,
    ): CancelablePromise<AIModelPublic> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/v1/ai/config/providers/{provider_id}/models',
            path: {
                'provider_id': providerId,
            },
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * List Assistant Configs
     * List all assistant configurations.
     * @param includeInactive
     * @returns AIAssistantConfigPublic Successful Response
     * @throws ApiError
     */
    public static listAssistantConfigs(
        includeInactive: boolean = false,
    ): CancelablePromise<Array<AIAssistantConfigPublic>> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/ai/config/assistants',
            query: {
                'include_inactive': includeInactive,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Create Assistant Config
     * Create a new assistant configuration.
     * @param requestBody
     * @returns AIAssistantConfigPublic Successful Response
     * @throws ApiError
     */
    public static createAssistantConfig(
        requestBody: AIAssistantConfigCreate,
    ): CancelablePromise<AIAssistantConfigPublic> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/v1/ai/config/assistants',
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Get Assistant Config
     * Get a specific assistant configuration.
     * @param assistantConfigId
     * @returns AIAssistantConfigPublic Successful Response
     * @throws ApiError
     */
    public static getAssistantConfig(
        assistantConfigId: string,
    ): CancelablePromise<AIAssistantConfigPublic> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/ai/config/assistants/{assistant_config_id}',
            path: {
                'assistant_config_id': assistantConfigId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Update Assistant Config
     * Update an assistant configuration.
     * @param assistantConfigId
     * @param requestBody
     * @returns AIAssistantConfigPublic Successful Response
     * @throws ApiError
     */
    public static updateAssistantConfig(
        assistantConfigId: string,
        requestBody: AIAssistantConfigUpdate,
    ): CancelablePromise<AIAssistantConfigPublic> {
        return __request(OpenAPI, {
            method: 'PUT',
            url: '/api/v1/ai/config/assistants/{assistant_config_id}',
            path: {
                'assistant_config_id': assistantConfigId,
            },
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Delete Assistant Config
     * Delete an assistant configuration.
     * @param assistantConfigId
     * @returns void
     * @throws ApiError
     */
    public static deleteAssistantConfig(
        assistantConfigId: string,
    ): CancelablePromise<void> {
        return __request(OpenAPI, {
            method: 'DELETE',
            url: '/api/v1/ai/config/assistants/{assistant_config_id}',
            path: {
                'assistant_config_id': assistantConfigId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
}
