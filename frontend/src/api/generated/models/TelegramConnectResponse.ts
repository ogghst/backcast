/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Deep-link URL the user opens in Telegram to connect their account.
 */
export type TelegramConnectResponse = {
    /**
     * Telegram bot username
     */
    bot_username: string;
    /**
     * https://t.me/<bot>?start=<token> URL
     */
    connect_url: string;
};

