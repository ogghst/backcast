"use client"

import { useQuery } from "@tanstack/react-query"
import { useMemo } from "react"

import { CostElementSchedulesService } from "@/client"

interface UseRegistrationDateValidationResult {
  isValid: boolean
  errorMessage: string | null
  warningMessage: string | null
  isLoading: boolean
}

/**
 * Custom hook to validate registration date against cost element schedule.
 *
 * Validation rules:
 * - If schedule exists and registration_date < start_date: returns error (blocks submission)
 * - If schedule exists and registration_date > end_date: returns warning (allows submission)
 * - If schedule exists and date is within bounds: returns valid
 * - If no schedule exists: returns valid (allow registration)
 *
 * @param costElementId - ID of the cost element to validate against
 * @param registrationDate - The registration date to validate (ISO date string or Date object)
 * @param enabled - Whether to enable the query (default: true)
 * @returns Validation result with isValid, errorMessage, warningMessage, and isLoading
 */
export function useRegistrationDateValidation(
  costElementId: string | undefined,
  registrationDate: string | Date | undefined,
  enabled: boolean = true,
): UseRegistrationDateValidationResult {
  // Fetch schedule for the cost element
  const { data: scheduleData, isLoading } = useQuery({
    queryKey: ["cost-element-schedule", costElementId],
    queryFn: async () => {
      try {
        return await CostElementSchedulesService.readScheduleByCostElement({
          costElementId: costElementId!,
        })
      } catch (error) {
        // Handle 404 gracefully - schedule may not exist
        if (error instanceof ApiError && error.status === 404) {
          return null
        }
        throw error
      }
    },
    enabled: enabled && !!costElementId,
    retry: false, // Don't retry on 404
  })

  const validationResult = useMemo(() => {
    // Default values when data is loading or missing
    if (isLoading || !costElementId || !registrationDate) {
      return {
        isValid: true, // Don't block while loading
        errorMessage: null,
        warningMessage: null,
        isLoading: true,
      }
    }

    // If no schedule exists, allow registration (no validation)
    if (!scheduleData) {
      return {
        isValid: true,
        errorMessage: null,
        warningMessage: null,
        isLoading: false,
      }
    }

    // Parse registration date
    const regDate =
      typeof registrationDate === "string"
        ? new Date(registrationDate)
        : registrationDate
    const startDate = new Date(scheduleData.start_date)
    const endDate = new Date(scheduleData.end_date)

    // Reset time to compare dates only
    regDate.setHours(0, 0, 0, 0)
    startDate.setHours(0, 0, 0, 0)
    endDate.setHours(0, 0, 0, 0)

    // Check if date is before start_date (hard block - error)
    if (regDate < startDate) {
      return {
        isValid: false,
        errorMessage: `Registration date cannot be before schedule start date (${scheduleData.start_date})`,
        warningMessage: null,
        isLoading: false,
      }
    }

    // Check if date is after end_date (warning but allow)
    if (regDate > endDate) {
      return {
        isValid: true, // Still valid - warning doesn't block submission
        errorMessage: null,
        warningMessage: `Warning: Registration date is after schedule end date (${scheduleData.end_date})`,
        isLoading: false,
      }
    }

    // Date is within bounds (valid)
    return {
      isValid: true,
      errorMessage: null,
      warningMessage: null,
      isLoading: false,
    }
  }, [scheduleData, registrationDate, costElementId, isLoading])

  return validationResult
}
