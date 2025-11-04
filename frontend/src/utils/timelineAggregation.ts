import type { TimePeriod } from "./progressionCalculations"

/**
 * Aggregate multiple cost element timelines into a single timeline.
 * Merges all unique dates and sums cumulative budgets at each time point.
 *
 * @param timelines - Array of TimePeriod arrays, one per cost element
 * @returns Aggregated timeline with merged dates and summed budgets
 */
export function aggregateTimelines(timelines: TimePeriod[][]): TimePeriod[] {
  // Handle empty input
  if (timelines.length === 0) {
    return []
  }

  // Handle single timeline
  if (timelines.length === 1) {
    return timelines[0].map((period) => ({ ...period }))
  }

  // Collect all unique dates from all timelines
  const allDates = new Set<number>()
  for (const timeline of timelines) {
    for (const period of timeline) {
      allDates.add(period.date.getTime())
    }
  }

  // Sort dates
  const sortedDates = Array.from(allDates).sort((a, b) => a - b)

  // Create a map for quick lookup of cumulative budget by date for each timeline
  const timelineMaps = timelines.map((timeline) => {
    const map = new Map<number, number>()
    for (const period of timeline) {
      map.set(period.date.getTime(), period.cumulativeBudget)
    }
    return map
  })

  // Build aggregated timeline
  const aggregated: TimePeriod[] = []
  let previousCumulativeBudget = 0

  for (const dateTime of sortedDates) {
    // Sum cumulative budgets from all timelines at this date
    let cumulativeBudget = 0
    for (const timelineMap of timelineMaps) {
      // Find the budget value for this date (or the closest previous value)
      const budget = timelineMap.get(dateTime)
      if (budget !== undefined) {
        cumulativeBudget += budget
      } else {
        // If this date doesn't exist in this timeline, find the latest value before this date
        let latestBudget = 0
        for (const [timelineDate, timelineBudget] of timelineMap.entries()) {
          if (timelineDate <= dateTime) {
            latestBudget = Math.max(latestBudget, timelineBudget)
          }
        }
        cumulativeBudget += latestBudget
      }
    }

    // Calculate period budget (difference from previous period)
    const periodBudget = cumulativeBudget - previousCumulativeBudget
    previousCumulativeBudget = cumulativeBudget

    // Calculate cumulative percent (we'll use 0-1 range, but actual percent depends on total BAC)
    // For aggregation, we'll keep cumulativePercent as a normalized value
    // Note: cumulativePercent in aggregated timeline is less meaningful,
    // but we'll calculate it based on the maximum cumulative budget
    // Find max budget from all timelines
    let maxBudget = 0
    for (const timelineMap of timelineMaps) {
      for (const budget of timelineMap.values()) {
        maxBudget = Math.max(maxBudget, budget)
      }
    }
    const cumulativePercent = maxBudget > 0 ? cumulativeBudget / maxBudget : 0

    aggregated.push({
      date: new Date(dateTime),
      cumulativePercent,
      cumulativeBudget,
      periodBudget,
    })
  }

  return aggregated
}
