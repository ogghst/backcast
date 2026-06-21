/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Current Telegram linkage status for the user.
 */
export type TelegramStatusResponse = {
    /**
     * Whether a TelegramAccount row exists
     */
    linked: boolean;
    /**
     * Whether the /start handshake completed
     */
    verified: boolean;
    /**
     * Telegram chat id once verified
     */
    chat_id?: (string | null);
    /**
     * Whether Telegram is configured and enabled server-side
     */
    available: boolean;
};

