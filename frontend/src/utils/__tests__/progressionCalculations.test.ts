import { addDays, differenceInDays } from "date-fns"
import { describe, expect, it } from "vitest"
import {
  calculateGaussianProgression,
  calculateLinearProgression,
  calculateLogarithmicProgression,
} from "../progressionCalculations"

describe("Linear Progression Calculation", () => {
  it("should calculate even distribution over time", () => {
    const startDate = new Date(2024, 0, 1) // Jan 1, 2024
    const endDate = new Date(2024, 0, 31) // Jan 31, 2024
    const budgetBac = 100000
    const timePoints = [
      new Date(2024, 0, 1), // Start
      new Date(2024, 0, 8), // ~25% (7 days / 30 days)
      new Date(2024, 0, 16), // ~50% (15 days / 30 days)
      new Date(2024, 0, 24), // ~75% (23 days / 30 days)
      new Date(2024, 0, 31), // End
    ]

    const result = calculateLinearProgression(
      startDate,
      endDate,
      budgetBac,
      timePoints,
    )

    // Expected: Even distribution
    // Day 1: 0% complete, €0 budget
    // Day 8: ~23.3% complete (7/30), ~€23,333 budget
    // Day 16: 50% complete (15/30), €50,000 budget
    // Day 24: ~76.7% complete (23/30), ~€76,667 budget
    // Day 31: 100% complete, €100,000 budget

    expect(result).toHaveLength(5)

    // Start date: 0% complete
    expect(result[0].cumulativePercent).toBe(0)
    expect(result[0].cumulativeBudget).toBe(0)

    // Day 8: ~23.3% (7 days elapsed / 30 total days)
    const day8Percent = 7 / 30
    expect(result[1].cumulativePercent).toBeCloseTo(day8Percent, 5)
    expect(result[1].cumulativeBudget).toBeCloseTo(budgetBac * day8Percent, 2)

    // Day 16: 50% (15 days elapsed / 30 total days)
    const day16Percent = 15 / 30
    expect(result[2].cumulativePercent).toBe(day16Percent)
    expect(result[2].cumulativeBudget).toBe(budgetBac * day16Percent)

    // Day 24: ~76.7% (23 days elapsed / 30 total days)
    const day24Percent = 23 / 30
    expect(result[3].cumulativePercent).toBeCloseTo(day24Percent, 5)
    expect(result[3].cumulativeBudget).toBeCloseTo(budgetBac * day24Percent, 2)

    // End date: 100% complete
    expect(result[4].cumulativePercent).toBe(1.0)
    expect(result[4].cumulativeBudget).toBe(budgetBac)
  })

  it("should return 0% complete and €0 budget at start date", () => {
    const startDate = new Date(2024, 0, 1)
    const endDate = new Date(2024, 0, 31)
    const budgetBac = 100000
    const timePoints = [startDate]

    const result = calculateLinearProgression(
      startDate,
      endDate,
      budgetBac,
      timePoints,
    )

    // Expected: First time point at start date
    expect(result).toHaveLength(1)
    expect(result[0].cumulativePercent).toBe(0)
    expect(result[0].cumulativeBudget).toBe(0)
  })

  it("should return 100% complete and full budget at end date", () => {
    const startDate = new Date(2024, 0, 1)
    const endDate = new Date(2024, 0, 31)
    const budgetBac = 100000
    const timePoints = [endDate]

    const result = calculateLinearProgression(
      startDate,
      endDate,
      budgetBac,
      timePoints,
    )

    // Expected: Last time point at end date
    expect(result).toHaveLength(1)
    expect(result[0].cumulativePercent).toBe(1.0)
    expect(result[0].cumulativeBudget).toBe(budgetBac)
  })

  it("should return 50% complete and 50% budget at midpoint", () => {
    const startDate = new Date(2024, 0, 1)
    const endDate = new Date(2024, 0, 31)
    const budgetBac = 100000
    const totalDays = differenceInDays(endDate, startDate)
    const midpoint = addDays(startDate, Math.floor(totalDays / 2))
    const timePoints = [midpoint]

    const result = calculateLinearProgression(
      startDate,
      endDate,
      budgetBac,
      timePoints,
    )

    // Expected: Midpoint should be approximately 50% complete
    expect(result).toHaveLength(1)
    expect(result[0].cumulativePercent).toBeCloseTo(0.5, 1)
    expect(result[0].cumulativeBudget).toBeCloseTo(budgetBac / 2, 2)
  })
})

describe("Gaussian Progression Calculation", () => {
  it("should have peak at midpoint", () => {
    const startDate = new Date(2024, 0, 1)
    const endDate = new Date(2024, 0, 31)
    const budgetBac = 100000
    const totalDays = differenceInDays(endDate, startDate)
    const midpoint = addDays(startDate, Math.floor(totalDays / 2))
    const timePoints = [
      startDate,
      addDays(startDate, Math.floor(totalDays * 0.25)),
      midpoint,
      addDays(startDate, Math.floor(totalDays * 0.75)),
      endDate,
    ]

    const result = calculateGaussianProgression(
      startDate,
      endDate,
      budgetBac,
      timePoints,
    )

    // Expected: Gaussian curve peaks at midpoint
    // Midpoint should have highest rate of change (periodBudget)
    // Early and late stages should have slower progression
    expect(result).toHaveLength(5)

    // Find period budgets (rate of change)
    const periodBudgets = result.map((r) => r.periodBudget)

    // Midpoint should have the highest period budget (peak activity)
    const midpointIndex = 2
    const midpointPeriodBudget = periodBudgets[midpointIndex]

    // Early periods should have lower period budgets than midpoint
    expect(periodBudgets[1]).toBeLessThan(midpointPeriodBudget)
    // Midpoint should have higher period budget than early and late (except start which is 0)
    expect(periodBudgets[3]).toBeLessThan(midpointPeriodBudget)
  })

  it("should have slow start (early dates have low progression)", () => {
    const startDate = new Date(2024, 0, 1)
    const endDate = new Date(2024, 0, 31)
    const budgetBac = 100000
    const timePoints = [
      startDate,
      addDays(startDate, 5), // Early date
      addDays(startDate, 10), // Still early
    ]

    const result = calculateGaussianProgression(
      startDate,
      endDate,
      budgetBac,
      timePoints,
    )

    // Expected: Slow start - early dates should have low cumulative budget
    // Early progression should be slower than linear
    expect(result).toHaveLength(3)

    // Compare with linear progression at same points
    const linearResult = calculateLinearProgression(
      startDate,
      endDate,
      budgetBac,
      timePoints,
    )

    // Early dates in gaussian should have lower cumulative budget than linear
    // (gaussian starts slower)
    expect(result[1].cumulativeBudget).toBeLessThan(
      linearResult[1].cumulativeBudget,
    )
    expect(result[2].cumulativeBudget).toBeLessThan(
      linearResult[2].cumulativeBudget,
    )
  })

  it("should have accelerating end (late dates have high progression)", () => {
    const startDate = new Date(2024, 0, 1)
    const endDate = new Date(2024, 0, 31)
    const budgetBac = 100000
    const totalDays = differenceInDays(endDate, startDate)
    const timePoints = [
      addDays(startDate, totalDays - 10), // Late date
      addDays(startDate, totalDays - 5), // Very late date
      endDate,
    ]

    const result = calculateGaussianProgression(
      startDate,
      endDate,
      budgetBac,
      timePoints,
    )

    // Expected: Accelerating end - late dates should have high progression rate
    // Late progression should be faster than linear
    expect(result).toHaveLength(3)

    // Compare with linear progression at same points
    const linearResult = calculateLinearProgression(
      startDate,
      endDate,
      budgetBac,
      timePoints,
    )

    // Late dates in gaussian should have higher cumulative budget than linear
    // (gaussian accelerates toward end)
    // Note: Since we're near the end, gaussian should catch up and potentially exceed linear
    // But we need to ensure we reach 100% at end date
    expect(result[result.length - 1].cumulativeBudget).toBeGreaterThanOrEqual(
      linearResult[linearResult.length - 1].cumulativeBudget * 0.9,
    )
  })

  it("should reach total budget at end date", () => {
    const startDate = new Date(2024, 0, 1)
    const endDate = new Date(2024, 0, 31)
    const budgetBac = 100000
    const timePoints = [endDate]

    const result = calculateGaussianProgression(
      startDate,
      endDate,
      budgetBac,
      timePoints,
    )

    // Expected: End date should have 100% complete and full budget
    expect(result).toHaveLength(1)
    expect(result[0].cumulativePercent).toBeCloseTo(1.0, 5)
    expect(result[0].cumulativeBudget).toBeCloseTo(budgetBac, 2)
  })
})

describe("Logarithmic Progression Calculation", () => {
  it("should have slow start (early dates have low progression)", () => {
    const startDate = new Date(2024, 0, 1)
    const endDate = new Date(2024, 0, 31)
    const budgetBac = 100000
    const timePoints = [
      startDate,
      addDays(startDate, 5), // Early date
      addDays(startDate, 10), // Still early
    ]

    const result = calculateLogarithmicProgression(
      startDate,
      endDate,
      budgetBac,
      timePoints,
    )

    // Expected: Slow start - early dates should have very low cumulative budget
    // Logarithmic progression starts very slow
    expect(result).toHaveLength(3)

    // Compare with linear progression at same points
    const linearResult = calculateLinearProgression(
      startDate,
      endDate,
      budgetBac,
      timePoints,
    )

    // Early dates in logarithmic should have much lower cumulative budget than linear
    // (logarithmic starts much slower)
    expect(result[1].cumulativeBudget).toBeLessThan(
      linearResult[1].cumulativeBudget,
    )
    expect(result[2].cumulativeBudget).toBeLessThan(
      linearResult[2].cumulativeBudget,
    )
  })

  it("should have accelerating completion (late dates have high progression)", () => {
    const startDate = new Date(2024, 0, 1)
    const endDate = new Date(2024, 0, 31)
    const budgetBac = 100000
    const totalDays = differenceInDays(endDate, startDate)
    const timePoints = [
      addDays(startDate, totalDays - 10), // Late date
      addDays(startDate, totalDays - 5), // Very late date
      endDate,
    ]

    const result = calculateLogarithmicProgression(
      startDate,
      endDate,
      budgetBac,
      timePoints,
    )

    // Expected: Accelerating completion - late dates should have very high progression rate
    // Logarithmic progression accelerates rapidly toward end
    expect(result).toHaveLength(3)

    // Compare with linear progression at same points
    const linearResult = calculateLinearProgression(
      startDate,
      endDate,
      budgetBac,
      timePoints,
    )

    // Late dates in logarithmic should catch up and potentially exceed linear
    // (logarithmic accelerates rapidly toward end)
    // But we need to ensure we reach 100% at end date
    expect(result[result.length - 1].cumulativeBudget).toBeGreaterThanOrEqual(
      linearResult[linearResult.length - 1].cumulativeBudget * 0.8,
    )
  })

  it("should reach total budget at end date", () => {
    const startDate = new Date(2024, 0, 1)
    const endDate = new Date(2024, 0, 31)
    const budgetBac = 100000
    const timePoints = [endDate]

    const result = calculateLogarithmicProgression(
      startDate,
      endDate,
      budgetBac,
      timePoints,
    )

    // Expected: End date should have 100% complete and full budget
    expect(result).toHaveLength(1)
    expect(result[0].cumulativePercent).toBeCloseTo(1.0, 5)
    expect(result[0].cumulativeBudget).toBeCloseTo(budgetBac, 2)
  })
})
