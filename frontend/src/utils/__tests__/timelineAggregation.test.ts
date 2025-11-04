import { describe, expect, it } from "vitest"
import type { TimePeriod } from "../progressionCalculations"
import { aggregateTimelines } from "../timelineAggregation"

describe("Timeline Aggregation", () => {
  it("should aggregate single element timeline", () => {
    const timeline: TimePeriod[] = [
      {
        date: new Date(2024, 0, 1),
        cumulativePercent: 0,
        cumulativeBudget: 0,
        periodBudget: 0,
      },
      {
        date: new Date(2024, 0, 15),
        cumulativePercent: 0.5,
        cumulativeBudget: 50000,
        periodBudget: 50000,
      },
      {
        date: new Date(2024, 0, 31),
        cumulativePercent: 1.0,
        cumulativeBudget: 100000,
        periodBudget: 50000,
      },
    ]

    const result = aggregateTimelines([timeline])

    // Expected: Should return the same timeline when aggregating a single element
    expect(result).toHaveLength(timeline.length)
    expect(result[0].cumulativeBudget).toBe(timeline[0].cumulativeBudget)
    expect(result[result.length - 1].cumulativeBudget).toBe(
      timeline[timeline.length - 1].cumulativeBudget,
    )
  })

  it("should aggregate multiple elements with same dates", () => {
    const timeline1: TimePeriod[] = [
      {
        date: new Date(2024, 0, 1),
        cumulativePercent: 0,
        cumulativeBudget: 0,
        periodBudget: 0,
      },
      {
        date: new Date(2024, 0, 31),
        cumulativePercent: 1.0,
        cumulativeBudget: 100000,
        periodBudget: 100000,
      },
    ]

    const timeline2: TimePeriod[] = [
      {
        date: new Date(2024, 0, 1),
        cumulativePercent: 0,
        cumulativeBudget: 0,
        periodBudget: 0,
      },
      {
        date: new Date(2024, 0, 31),
        cumulativePercent: 1.0,
        cumulativeBudget: 50000,
        periodBudget: 50000,
      },
    ]

    const result = aggregateTimelines([timeline1, timeline2])

    // Expected: Should sum budgets: 100000 + 50000 = 150000
    expect(result).toHaveLength(2)
    expect(result[0].cumulativeBudget).toBe(0) // Start date
    expect(result[1].cumulativeBudget).toBe(150000) // End date (100000 + 50000)
  })

  it("should aggregate multiple elements with overlapping dates", () => {
    const timeline1: TimePeriod[] = [
      {
        date: new Date(2024, 0, 1),
        cumulativePercent: 0,
        cumulativeBudget: 0,
        periodBudget: 0,
      },
      {
        date: new Date(2024, 0, 15),
        cumulativePercent: 0.5,
        cumulativeBudget: 50000,
        periodBudget: 50000,
      },
      {
        date: new Date(2024, 0, 31),
        cumulativePercent: 1.0,
        cumulativeBudget: 100000,
        periodBudget: 50000,
      },
    ]

    const timeline2: TimePeriod[] = [
      {
        date: new Date(2024, 0, 10), // Different start point
        cumulativePercent: 0,
        cumulativeBudget: 0,
        periodBudget: 0,
      },
      {
        date: new Date(2024, 0, 20), // Different midpoint
        cumulativePercent: 0.5,
        cumulativeBudget: 25000,
        periodBudget: 25000,
      },
      {
        date: new Date(2024, 1, 5), // Different end point
        cumulativePercent: 1.0,
        cumulativeBudget: 50000,
        periodBudget: 25000,
      },
    ]

    const result = aggregateTimelines([timeline1, timeline2])

    // Expected: Should merge dates and sum budgets at each time point
    // Should include all unique dates from both timelines
    expect(result.length).toBeGreaterThan(0)

    // Should include all unique dates
    const dates = result.map((r) => r.date.getTime())
    const uniqueDates = new Set(dates)
    expect(dates.length).toBe(uniqueDates.size)

    // Should sum budgets at overlapping dates
    // At Jan 15: timeline1 has 50000, timeline2 has 0 (hasn't started yet)
    const jan15 = result.find(
      (r) => r.date.getTime() === new Date(2024, 0, 15).getTime(),
    )
    if (jan15) {
      expect(jan15.cumulativeBudget).toBeGreaterThanOrEqual(50000)
    }

    // At Jan 31: timeline1 has 100000, timeline2 has some value (should be interpolated)
    const jan31 = result.find(
      (r) => r.date.getTime() === new Date(2024, 0, 31).getTime(),
    )
    if (jan31) {
      expect(jan31.cumulativeBudget).toBeGreaterThan(100000)
    }
  })

  it("should handle empty timeline array", () => {
    const result = aggregateTimelines([])

    // Expected: Should return empty array
    expect(result).toHaveLength(0)
  })

  it("should aggregate multiple elements with different date ranges", () => {
    const timeline1: TimePeriod[] = [
      {
        date: new Date(2024, 0, 1),
        cumulativePercent: 0,
        cumulativeBudget: 0,
        periodBudget: 0,
      },
      {
        date: new Date(2024, 0, 15),
        cumulativePercent: 1.0,
        cumulativeBudget: 100000,
        periodBudget: 100000,
      },
    ]

    const timeline2: TimePeriod[] = [
      {
        date: new Date(2024, 0, 20), // Starts later
        cumulativePercent: 0,
        cumulativeBudget: 0,
        periodBudget: 0,
      },
      {
        date: new Date(2024, 1, 5), // Ends later
        cumulativePercent: 1.0,
        cumulativeBudget: 50000,
        periodBudget: 50000,
      },
    ]

    const result = aggregateTimelines([timeline1, timeline2])

    // Expected: Should include all dates from both timelines
    // Budget should be summed at overlapping dates, or single value at non-overlapping dates
    expect(result.length).toBeGreaterThan(0)

    // Should include all dates from both timelines
    const dates = result.map((r) => r.date.getTime())
    expect(dates).toContain(new Date(2024, 0, 1).getTime()) // From timeline1
    expect(dates).toContain(new Date(2024, 0, 15).getTime()) // From timeline1
    expect(dates).toContain(new Date(2024, 0, 20).getTime()) // From timeline2
    expect(dates).toContain(new Date(2024, 1, 5).getTime()) // From timeline2

    // At Jan 15: Only timeline1 has value (100000), timeline2 hasn't started yet
    const jan15 = result.find(
      (r) => r.date.getTime() === new Date(2024, 0, 15).getTime(),
    )
    if (jan15) {
      expect(jan15.cumulativeBudget).toBe(100000)
    }

    // At Feb 5: timeline1 has completed (100000), timeline2 has value (50000)
    // Aggregated should be sum: 100000 + 50000 = 150000
    const feb5 = result.find(
      (r) => r.date.getTime() === new Date(2024, 1, 5).getTime(),
    )
    if (feb5) {
      expect(feb5.cumulativeBudget).toBe(150000) // Sum of both timelines
    }
  })
})
