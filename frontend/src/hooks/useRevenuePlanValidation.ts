"use client"

import { useQuery } from "@tanstack/react-query"
import { useMemo } from "react"

import { CostElementsService, WbesService } from "@/client"

interface UseRevenuePlanValidationResult {
  isValid: boolean
  errorMessage: string | null
  currentTotal: number
  limit: number
  remaining: number
}

/**
 * Custom hook to validate revenue_plan against WBE revenue_allocation limit.
 *
 * @param wbeId - ID of the WBE to validate against
 * @param excludeCostElementId - Cost element ID to exclude from the sum (for updates)
 * @param newRevenuePlan - The new revenue_plan value being validated
 * @returns Validation result with isValid, errorMessage, currentTotal, limit, and remaining
 */
export function useRevenuePlanValidation(
  wbeId: string | undefined,
  excludeCostElementId: string | null,
  newRevenuePlan: number | undefined,
): UseRevenuePlanValidationResult {
  // Fetch WBE to get revenue_allocation
  const { data: wbe } = useQuery({
    queryKey: ["wbes", wbeId],
    queryFn: () => WbesService.readWbe({ id: wbeId! }),
    enabled: !!wbeId,
  })

  // Fetch all cost elements for the WBE
  const { data: costElementsData } = useQuery({
    queryKey: ["cost-elements", { wbeId }],
    queryFn: () =>
      CostElementsService.readCostElements({
        wbeId: wbeId!,
        skip: 0,
        limit: 1000, // Large limit to get all cost elements
      }),
    enabled: !!wbeId,
  })

  const validationResult = useMemo(() => {
    // Default values when data is loading or missing
    if (!wbe || !costElementsData || newRevenuePlan === undefined) {
      return {
        isValid: true, // Don't block while loading
        errorMessage: null,
        currentTotal: 0,
        limit: 0,
        remaining: 0,
      }
    }

    const limit = Number(wbe.revenue_allocation) || 0

    // Sum existing revenue_plan values, excluding the cost element being updated
    const costElements = costElementsData.data || []
    const existingTotal = costElements
      .filter((ce) => ce.cost_element_id !== excludeCostElementId)
      .reduce((sum, ce) => sum + (Number(ce.revenue_plan) || 0), 0)

    // Calculate new total
    const newTotal = existingTotal + newRevenuePlan
    const remaining = limit - newTotal

    // Validate: sum must not exceed limit
    const isValid = newTotal <= limit
    const errorMessage = isValid
      ? null
      : `Total revenue plan (€${newTotal.toLocaleString("en-US", {
          minimumFractionDigits: 2,
          maximumFractionDigits: 2,
        })}) exceeds WBE revenue allocation (€${limit.toLocaleString("en-US", {
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
  }, [wbe, costElementsData, excludeCostElementId, newRevenuePlan])

  return validationResult
}
