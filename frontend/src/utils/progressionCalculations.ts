import { differenceInDays } from "date-fns"

export interface TimePeriod {
  date: Date
  cumulativePercent: number // 0.0 to 1.0
  cumulativeBudget: number // 0 to budget_bac
  periodBudget: number // Budget for this period
}

/**
 * Calculate linear progression of budget over time.
 * Budget is distributed evenly across the schedule period.
 *
 * @param startDate - Schedule start date
 * @param endDate - Schedule end date
 * @param budgetBac - Total budget at completion
 * @param timePoints - Array of dates to calculate progression for
 * @returns Array of time periods with cumulative budget values
 */
export function calculateLinearProgression(
  startDate: Date,
  endDate: Date,
  budgetBac: number,
  timePoints: Date[],
): TimePeriod[] {
  const totalDays = differenceInDays(endDate, startDate)

  if (totalDays <= 0) {
    // Handle edge case: start date equals or after end date
    return timePoints.map((date) => ({
      date,
      cumulativePercent: date >= startDate ? 1.0 : 0.0,
      cumulativeBudget: date >= startDate ? budgetBac : 0.0,
      periodBudget: 0.0,
    }))
  }

  let previousBudget = 0.0

  return timePoints.map((date) => {
    // Calculate days elapsed from start date
    const daysElapsed = differenceInDays(date, startDate)

    // Calculate percent complete (clamped between 0 and 1)
    const percentComplete = Math.min(Math.max(daysElapsed / totalDays, 0), 1)

    // Calculate cumulative budget
    const cumulativeBudget = budgetBac * percentComplete

    // Calculate period budget (difference from previous period)
    const periodBudget = cumulativeBudget - previousBudget
    previousBudget = cumulativeBudget

    return {
      date,
      cumulativePercent: percentComplete,
      cumulativeBudget,
      periodBudget,
    }
  })
}

/**
 * Approximate error function (erf) using Abramowitz and Stegun approximation.
 * Used for normal CDF calculation.
 */
function erf(x: number): number {
  // Abramowitz and Stegun approximation
  const a1 = 0.254829592
  const a2 = -0.284496736
  const a3 = 1.421413741
  const a4 = -1.453152027
  const a5 = 1.061405429
  const p = 0.3275911

  const sign = x < 0 ? -1 : 1
  const absX = Math.abs(x)

  const t = 1.0 / (1.0 + p * absX)
  const y =
    1.0 -
    ((((a5 * t + a4) * t + a3) * t + a2) * t + a1) * t * Math.exp(-absX * absX)

  return sign * y
}

/**
 * Normal CDF (Cumulative Distribution Function) approximation.
 * @param x - Value to evaluate
 * @param mean - Mean of the distribution
 * @param stdDev - Standard deviation
 */
function normalCDF(x: number, mean: number, stdDev: number): number {
  return 0.5 * (1 + erf((x - mean) / (stdDev * Math.sqrt(2))))
}

/**
 * Calculate gaussian progression of budget over time.
 * Budget follows a normal distribution curve with peak at midpoint.
 * Slow start, peak at midpoint, accelerating completion.
 *
 * @param startDate - Schedule start date
 * @param endDate - Schedule end date
 * @param budgetBac - Total budget at completion
 * @param timePoints - Array of dates to calculate progression for
 * @returns Array of time periods with cumulative budget values
 */
export function calculateGaussianProgression(
  startDate: Date,
  endDate: Date,
  budgetBac: number,
  timePoints: Date[],
): TimePeriod[] {
  const totalDays = differenceInDays(endDate, startDate)

  if (totalDays <= 0) {
    // Handle edge case: start date equals or after end date
    return timePoints.map((date) => ({
      date,
      cumulativePercent: date >= startDate ? 1.0 : 0.0,
      cumulativeBudget: date >= startDate ? budgetBac : 0.0,
      periodBudget: 0.0,
    }))
  }

  // Parameters for normal distribution
  // Mean at midpoint (0.5 normalized time)
  const mean = 0.5
  // Standard deviation controls the spread (smaller = more concentrated at center)
  // Using 0.25 to create a reasonable curve that starts slow and ends fast
  const stdDev = 0.25

  let previousBudget = 0.0

  return timePoints.map((date) => {
    // Calculate normalized time position (0 to 1)
    const daysElapsed = differenceInDays(date, startDate)
    const normalizedTime = Math.min(Math.max(daysElapsed / totalDays, 0), 1)

    // Use normal CDF to calculate cumulative percent
    // Map normalized time (0-1) to normal distribution
    // The CDF gives us the cumulative probability, which we use as percent complete
    const cumulativePercent = normalCDF(normalizedTime, mean, stdDev)

    // Normalize to ensure we reach 100% at end (CDF may not exactly reach 1.0)
    // We'll scale it so that normalizedTime = 1.0 gives cumulativePercent = 1.0
    const maxCDF = normalCDF(1.0, mean, stdDev)
    const scaledPercent = cumulativePercent / maxCDF

    // Clamp to [0, 1]
    const percentComplete = Math.min(Math.max(scaledPercent, 0), 1)

    // Calculate cumulative budget
    const cumulativeBudget = budgetBac * percentComplete

    // Calculate period budget (difference from previous period)
    const periodBudget = cumulativeBudget - previousBudget
    previousBudget = cumulativeBudget

    return {
      date,
      cumulativePercent: percentComplete,
      cumulativeBudget,
      periodBudget,
    }
  })
}

/**
 * Calculate logarithmic progression of budget over time.
 * Budget follows a logarithmic curve: very slow start, accelerating completion.
 *
 * @param startDate - Schedule start date
 * @param endDate - Schedule end date
 * @param budgetBac - Total budget at completion
 * @param timePoints - Array of dates to calculate progression for
 * @returns Array of time periods with cumulative budget values
 */
export function calculateLogarithmicProgression(
  startDate: Date,
  endDate: Date,
  budgetBac: number,
  timePoints: Date[],
): TimePeriod[] {
  const totalDays = differenceInDays(endDate, startDate)

  if (totalDays <= 0) {
    // Handle edge case: start date equals or after end date
    return timePoints.map((date) => ({
      date,
      cumulativePercent: date >= startDate ? 1.0 : 0.0,
      cumulativeBudget: date >= startDate ? budgetBac : 0.0,
      periodBudget: 0.0,
    }))
  }

  let previousBudget = 0.0

  return timePoints.map((date) => {
    // Calculate normalized time position (0 to 1)
    const daysElapsed = differenceInDays(date, startDate)
    const normalizedTime = Math.min(Math.max(daysElapsed / totalDays, 0), 1)

    // Logarithmic progression: Use power curve for slow start, accelerating completion
    // Using a quadratic curve (normalizedTime^2) creates a slow start that accelerates
    // When normalizedTime = 0: 0^2 = 0
    // When normalizedTime = 1: 1^2 = 1
    // This gives us the desired "logarithmic" behavior (slow start, accelerating completion)
    const power = 2 // Quadratic curve for slow start, accelerating completion
    const percentComplete = normalizedTime ** power

    // Calculate cumulative budget
    const cumulativeBudget = budgetBac * percentComplete

    // Calculate period budget (difference from previous period)
    const periodBudget = cumulativeBudget - previousBudget
    previousBudget = cumulativeBudget

    return {
      date,
      cumulativePercent: percentComplete,
      cumulativeBudget,
      periodBudget,
    }
  })
}
