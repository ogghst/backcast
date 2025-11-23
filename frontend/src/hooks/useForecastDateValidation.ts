"use client"

import { useMemo } from "react"

interface UseForecastDateValidationResult {
  isValid: boolean
  warningMessage: string | null
}

/**
 * Custom hook to validate forecast date.
 *
 * Validation rules:
 * - Forecast date should be in the past (warning if future, not blocked)
 *
 * @param forecastDate - The forecast date to validate (ISO date string or Date object)
 * @returns Validation result with isValid and warningMessage
 */
export function useForecastDateValidation(
  forecastDate: string | Date | undefined,
): UseForecastDateValidationResult {
  const validationResult = useMemo(() => {
    if (!forecastDate) {
      return {
        isValid: true,
        warningMessage: null,
      }
    }

    const date =
      typeof forecastDate === "string" ? new Date(forecastDate) : forecastDate
    const today = new Date()
    today.setHours(0, 0, 0, 0)
    date.setHours(0, 0, 0, 0)

    // Check if date is in the future (warning, not blocked)
    if (date > today) {
      return {
        isValid: true, // Still valid - warning doesn't block submission
        warningMessage: `Forecast date is in the future. Forecasts should typically be dated in the past.`,
      }
    }

    return {
      isValid: true,
      warningMessage: null,
    }
  }, [forecastDate])

  return validationResult
}
