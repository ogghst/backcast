import { addDays, addMonths, addWeeks } from "date-fns"

export type TimeSeriesGranularity = "daily" | "weekly" | "monthly"

/**
 * Generate a time series array of dates between start and end dates.
 *
 * @param startDate - Start date (inclusive)
 * @param endDate - End date (inclusive)
 * @param granularity - Time interval: 'daily', 'weekly', or 'monthly'
 * @returns Array of Date objects from startDate to endDate
 */
export function generateTimeSeries(
  startDate: Date,
  endDate: Date,
  granularity: TimeSeriesGranularity = "daily",
): Date[] {
  // Validate dates
  if (startDate > endDate) {
    // If start is after end, return empty array or swap (handling edge case)
    return []
  }

  const result: Date[] = []
  let currentDate = new Date(startDate)

  // Always include start date
  result.push(new Date(currentDate))

  // Handle single day case
  if (startDate.getTime() === endDate.getTime()) {
    return result
  }

  // Generate series based on granularity
  switch (granularity) {
    case "daily": {
      while (currentDate < endDate) {
        currentDate = addDays(currentDate, 1)
        if (currentDate <= endDate) {
          result.push(new Date(currentDate))
        }
      }
      break
    }

    case "weekly": {
      while (currentDate < endDate) {
        currentDate = addWeeks(currentDate, 1)
        if (currentDate <= endDate) {
          result.push(new Date(currentDate))
        } else {
          // Ensure end date is included if it's close to the last weekly point
          const lastDate = result[result.length - 1]
          if (lastDate && endDate > lastDate) {
            result.push(new Date(endDate))
          }
          break
        }
      }
      // Ensure end date is included
      if (result.length > 0) {
        const lastDate = result[result.length - 1]
        if (lastDate.getTime() !== endDate.getTime()) {
          result.push(new Date(endDate))
        }
      }
      break
    }

    case "monthly": {
      while (currentDate < endDate) {
        currentDate = addMonths(currentDate, 1)
        if (currentDate <= endDate) {
          result.push(new Date(currentDate))
        } else {
          // Ensure end date is included if it's close to the last monthly point
          const lastDate = result[result.length - 1]
          if (lastDate && endDate > lastDate) {
            result.push(new Date(endDate))
          }
          break
        }
      }
      // Ensure end date is included
      if (result.length > 0) {
        const lastDate = result[result.length - 1]
        if (lastDate.getTime() !== endDate.getTime()) {
          result.push(new Date(endDate))
        }
      }
      break
    }

    default:
      // Invalid granularity - default to daily
      return generateTimeSeries(startDate, endDate, "daily")
  }

  return result
}
