/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { app__models__schemas__document__EntityType } from './app__models__schemas__document__EntityType';
/**
 * Properties required for linking a document to an entity.
 */
export type DocumentLinkCreate = {
    entity_type: app__models__schemas__document__EntityType;
    entity_id: string;
    note?: (string | null);
};

