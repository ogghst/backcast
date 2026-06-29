/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Properties returned to client.
 */
export type CurrencyRateRead = {
    /**
     * ISO-4217 code
     */
    currency: string;
    /**
     * 1 unit of currency = rate_to_base base
     */
    rate_to_base: string;
    /**
     * Date from which the rate is valid
     */
    effective_date: string;
    id: string;
};

