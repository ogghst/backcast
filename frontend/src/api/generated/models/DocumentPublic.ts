/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { DocumentVersionPublic } from './DocumentVersionPublic';
/**
 * Document representation returned to the client.
 */
export type DocumentPublic = {
    id: string;
    project_id: string;
    folder_id: (string | null);
    name: string;
    extension: string;
    description: (string | null);
    tags: Array<string>;
    current_version?: (DocumentVersionPublic | null);
    is_locked: boolean;
    locked_by: (string | null);
    created_by: string;
    created_by_name?: (string | null);
    size_bytes: number;
    created_at: string;
    updated_at: string;
};

