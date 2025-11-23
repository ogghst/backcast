"use client"

import { useMemo } from "react"

/**
 * Custom hook to calculate ETC (Estimate to Complete).
 *
 * Formula: ETC = EAC - AC
 *
 * @param eac - The estimate at completion value
 * @param actualCost - The actual cost (AC)
 * @returns Calculated ETC value or null if calculation not possible
 */
export function useETCCalculation(
  eac: number | string | null | undefined,
  actualCost?: number | string | null,
): number | null {
  const etc = useMemo(() => {
    if (eac === null || eac === undefined) {
      return null
    }

    const eacNum = typeof eac === "string" ? parseFloat(eac) : Number(eac)
    if (Number.isNaN(eacNum)) {
      return null
    }

    const acNum =
      actualCost !== null && actualCost !== undefined
        ? typeof actualCost === "string"
          ? parseFloat(actualCost)
          : Number(actualCost)
        : 0

    if (Number.isNaN(acNum)) {
      return null
    }

    return eacNum - acNum
  }, [eac, actualCost])

  return etc
}
