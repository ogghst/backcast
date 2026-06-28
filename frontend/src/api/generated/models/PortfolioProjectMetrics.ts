/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Per-project EVM row in the portfolio breakdown.
 */
export type PortfolioProjectMetrics = {
    /**
     * Root project id
     */
    project_id: string;
    /**
     * Project name
     */
    name: string;
    /**
     * Project status (draft/active/...)
     */
    status: string;
    /**
     * Cost Performance Index (null when AC is zero)
     */
    cpi?: (number | null);
    /**
     * Schedule Performance Index (null when PV is zero)
     */
    spi?: (number | null);
    /**
     * Variance at Completion in base currency (BAC - EAC)
     */
    vac?: (number | null);
    /**
     * Contract value converted to the portfolio base currency at control_date (null when the project has no contract value).
     */
    contract_value?: (number | null);
    /**
     * Budget at Completion in base currency
     */
    bac: number;
    /**
     * Estimate at Completion in base currency
     */
    eac?: (number | null);
    /**
     * Project's native ISO-4217 currency code
     */
    currency: string;
    /**
     * Root id of the owning organizational unit
     */
    organizational_unit_id?: (string | null);
    /**
     * Root id of the project manager (User)
     */
    project_manager_id?: (string | null);
    /**
     * Root id of the customer (Customer)
     */
    customer_id?: (string | null);
    /**
     * True when SPI is present and below 0.9 (delay proxy)
     */
    at_risk: boolean;
    /**
     * ΔEAC forecast drift = latest EAC minus previous EAC (summed over the project's work-package forecasts). Null when no forecast history exists.
     */
    delta_eac?: (number | null);
};

