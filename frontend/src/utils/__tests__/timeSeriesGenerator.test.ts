import { differenceInDays } from "date-fns"
import { describe, expect, it } from "vitest"
import { generateTimeSeries } from "../timeSeriesGenerator"

describe("Time Series Generation", () => {
  it("should generate daily time series", () => {
    const startDate = new Date(2024, 0, 1) // Jan 1, 2024
    const endDate = new Date(2024, 0, 5) // Jan 5, 2024

    const result = generateTimeSeries(startDate, endDate, "daily")

    // Expected: Should include all days from start to end (inclusive)
    // [Jan 1, Jan 2, Jan 3, Jan 4, Jan 5]
    expect(result).toHaveLength(5)
    expect(result[0].getTime()).toBe(startDate.getTime())
    expect(result[result.length - 1].getTime()).toBe(endDate.getTime())
  })

  it("should generate weekly time series", () => {
    const startDate = new Date(2024, 0, 1) // Jan 1, 2024
    const endDate = new Date(2024, 0, 22) // Jan 22, 2024 (3 weeks)

    const result = generateTimeSeries(startDate, endDate, "weekly")

    // Expected: Should include weekly intervals
    // Should include start date and end date
    expect(result.length).toBeGreaterThan(0)
    expect(result[0].getTime()).toBe(startDate.getTime())
    expect(result[result.length - 1].getTime()).toBe(endDate.getTime())
    // Should have weekly intervals (approximately 7 days between points, except last)
    if (result.length > 2) {
      const daysBetween = differenceInDays(result[1], result[0])
      expect(daysBetween).toBeGreaterThanOrEqual(6)
      expect(daysBetween).toBeLessThanOrEqual(8)
    }
  })

  it("should generate monthly time series", () => {
    const startDate = new Date(2024, 0, 1) // Jan 1, 2024
    const endDate = new Date(2024, 2, 31) // Mar 31, 2024 (3 months)

    const result = generateTimeSeries(startDate, endDate, "monthly")

    // Expected: Should include monthly intervals
    // Should include start date and end date
    expect(result.length).toBeGreaterThan(0)
    expect(result[0].getTime()).toBe(startDate.getTime())
    expect(result[result.length - 1].getTime()).toBe(endDate.getTime())
    // Should have monthly intervals (approximately 28-31 days between points, except last)
    if (result.length > 2) {
      const daysBetween = differenceInDays(result[1], result[0])
      expect(daysBetween).toBeGreaterThanOrEqual(28)
      expect(daysBetween).toBeLessThanOrEqual(32)
    }
  })

  it("should include start and end dates", () => {
    const startDate = new Date(2024, 0, 1)
    const endDate = new Date(2024, 0, 31)

    const result = generateTimeSeries(startDate, endDate, "daily")

    // Expected: First date should be startDate, last date should be endDate
    expect(result.length).toBeGreaterThan(0)
    expect(result[0].getTime()).toBe(startDate.getTime())
    expect(result[result.length - 1].getTime()).toBe(endDate.getTime())
  })
})

describe("Time Series Generation Edge Cases", () => {
  it("should handle single day range", () => {
    const startDate = new Date(2024, 0, 1)
    const endDate = new Date(2024, 0, 1) // Same day

    const result = generateTimeSeries(startDate, endDate, "daily")

    // Expected: Should return array with single date
    expect(result).toHaveLength(1)
    expect(result[0].getTime()).toBe(startDate.getTime())
  })

  it("should handle very short ranges (< 7 days)", () => {
    const startDate = new Date(2024, 0, 1)
    const endDate = new Date(2024, 0, 3) // 2 days

    const result = generateTimeSeries(startDate, endDate, "daily")

    // Expected: Should still generate daily series even for short ranges
    expect(result.length).toBeGreaterThan(0)
    expect(result[0].getTime()).toBe(startDate.getTime())
    expect(result[result.length - 1].getTime()).toBe(endDate.getTime())
  })

  it("should handle very long ranges (> 365 days)", () => {
    const startDate = new Date(2024, 0, 1)
    const endDate = new Date(2025, 0, 1) // 1 year

    const result = generateTimeSeries(startDate, endDate, "monthly")

    // Expected: Should handle long ranges efficiently
    expect(result.length).toBeGreaterThan(0)
    expect(result[0].getTime()).toBe(startDate.getTime())
    expect(result[result.length - 1].getTime()).toBe(endDate.getTime())
    // Should have approximately 12 monthly points for 1 year
    expect(result.length).toBeGreaterThanOrEqual(12)
    expect(result.length).toBeLessThanOrEqual(13) // May include end date
  })
})
