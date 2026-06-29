/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Properties required for creating a CurrencyRate.
 */
export type CurrencyRateCreate = {
    /**
     * ISO-4217 code
     */
    currency: string;
    /**
     * 1 unit of currency = rate_to_base base
     */
    rate_to_base: (number | string);
    /**
     * Date from which the rate is valid
     */
    effective_date: string;
};

