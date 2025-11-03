"use client"

import { useQuery } from "@tanstack/react-query"
import { useMemo } from "react"

import { ProjectsService, WbesService } from "@/client"

interface UseRevenueAllocationValidationResult {
  isValid: boolean
  errorMessage: string | null
  currentTotal: number
  limit: number
  remaining: number
}

/**
 * Custom hook to validate revenue_allocation against project contract_value limit.
 *
 * @param projectId - ID of the project to validate against
 * @param excludeWbeId - WBE ID to exclude from the sum (for updates)
 * @param newRevenueAllocation - The new revenue_allocation value being validated
 * @returns Validation result with isValid, errorMessage, currentTotal, limit, and remaining
 */
export function useRevenueAllocationValidation(
  projectId: string | undefined,
  excludeWbeId: string | null,
  newRevenueAllocation: number | undefined,
): UseRevenueAllocationValidationResult {
  // Fetch project to get contract_value
  const { data: project } = useQuery({
    queryKey: ["projects", projectId],
    queryFn: () => ProjectsService.readProject({ id: projectId! }),
    enabled: !!projectId,
  })

  // Fetch all WBEs for the project
  const { data: wbesData } = useQuery({
    queryKey: ["wbes", { projectId }],
    queryFn: () =>
      WbesService.readWbes({
        projectId: projectId!,
        skip: 0,
        limit: 1000, // Large limit to get all WBEs
      }),
    enabled: !!projectId,
  })

  const validationResult = useMemo(() => {
    // Default values when data is loading or missing
    if (!project || !wbesData || newRevenueAllocation === undefined) {
      return {
        isValid: true, // Don't block while loading
        errorMessage: null,
        currentTotal: 0,
        limit: 0,
        remaining: 0,
      }
    }

    const limit = Number(project.contract_value) || 0

    // Sum existing revenue_allocation values, excluding the WBE being updated
    const wbes = wbesData.data || []
    const existingTotal = wbes
      .filter((wbe) => wbe.wbe_id !== excludeWbeId)
      .reduce((sum, wbe) => sum + (Number(wbe.revenue_allocation) || 0), 0)

    // Calculate new total
    const newTotal = existingTotal + newRevenueAllocation
    const remaining = limit - newTotal

    // Validate: sum must not exceed limit
    const isValid = newTotal <= limit
    const errorMessage = isValid
      ? null
      : `Total revenue allocation (€${newTotal.toLocaleString("en-US", {
          minimumFractionDigits: 2,
          maximumFractionDigits: 2,
        })}) exceeds project contract value (€${limit.toLocaleString("en-US", {
          minimumFractionDigits: 2,
          maximumFractionDigits: 2,
        })})`

    return {
      isValid,
      errorMessage,
      currentTotal: newTotal,
      limit,
      remaining,
    }
  }, [project, wbesData, excludeWbeId, newRevenueAllocation])

  return validationResult
}
