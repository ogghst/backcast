"use client"

import { useMemo } from "react"

interface UseEACValidationResult {
  isValid: boolean
  warningMessages: string[]
}

/**
 * Custom hook to validate EAC and show warnings.
 *
 * Validation rules:
 * - EAC must be > 0 (enforced by backend)
 * - Warning if EAC > BAC
 * - Warning if EAC < AC
 *
 * @param eac - The estimate at completion value
 * @param budgetBac - The budget at completion (BAC)
 * @param actualCost - The actual cost (AC)
 * @returns Validation result with isValid and warningMessages
 */
export function useEACValidation(
  eac: number | string | null | undefined,
  budgetBac?: number | string | null,
  actualCost?: number | string | null,
): UseEACValidationResult {
  const validationResult = useMemo(() => {
    const warnings: string[] = []

    if (eac === null || eac === undefined) {
      return {
        isValid: true,
        warningMessages: [],
      }
    }

    const eacNum = typeof eac === "string" ? parseFloat(eac) : Number(eac)
    if (Number.isNaN(eacNum)) {
      return {
        isValid: true,
        warningMessages: [],
      }
    }

    // Warning if EAC > BAC
    if (budgetBac !== null && budgetBac !== undefined) {
      const bacNum =
        typeof budgetBac === "string"
          ? parseFloat(budgetBac)
          : Number(budgetBac)
      if (!Number.isNaN(bacNum) && eacNum > bacNum) {
        warnings.push(
          `EAC (€${eacNum.toLocaleString("en-US", {
            minimumFractionDigits: 2,
            maximumFractionDigits: 2,
          })}) exceeds Budget BAC (€${bacNum.toLocaleString("en-US", {
            minimumFractionDigits: 2,
            maximumFractionDigits: 2,
          })})`,
        )
      }
    }

    // Warning if EAC < AC
    if (actualCost !== null && actualCost !== undefined) {
      const acNum =
        typeof actualCost === "string"
          ? parseFloat(actualCost)
          : Number(actualCost)
      if (!Number.isNaN(acNum) && eacNum < acNum) {
        warnings.push(
          `EAC (€${eacNum.toLocaleString("en-US", {
            minimumFractionDigits: 2,
            maximumFractionDigits: 2,
          })}) is less than Actual Cost (€${acNum.toLocaleString("en-US", {
            minimumFractionDigits: 2,
            maximumFractionDigits: 2,
          })})`,
        )
      }
    }

    return {
      isValid: true, // Warnings don't block submission
      warningMessages: warnings,
    }
  }, [eac, budgetBac, actualCost])

  return validationResult
}
