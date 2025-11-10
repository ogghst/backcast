import type { EarnedValueEntryPublic } from "@/client"

export interface EarnedValueTimelinePoint {
  date: Date
  earnedValue: number
}

function toDateKey(date: Date): string {
  return date.toISOString().slice(0, 10)
}

export function buildEarnedValueTimeline({
  entries,
}: {
  entries: EarnedValueEntryPublic[]
}): EarnedValueTimelinePoint[] {
  if (!entries || entries.length === 0) {
    return []
  }

  const valuesByDate = new Map<string, number>()

  for (const entry of entries) {
    const { completion_date: completionDate, earned_value: earnedValueRaw } =
      entry

    if (
      !completionDate ||
      earnedValueRaw === undefined ||
      earnedValueRaw === null
    ) {
      continue
    }

    const parsedDate = new Date(completionDate)
    if (Number.isNaN(parsedDate.getTime())) {
      continue
    }

    const earnedValue = Number(earnedValueRaw)
    if (Number.isNaN(earnedValue)) {
      continue
    }

    const key = toDateKey(parsedDate)
    valuesByDate.set(key, (valuesByDate.get(key) ?? 0) + earnedValue)
  }

  if (valuesByDate.size === 0) {
    return []
  }

  const sortedKeys = Array.from(valuesByDate.keys()).sort()

  return sortedKeys.map((key) => {
    const value = valuesByDate.get(key) ?? 0
    return {
      date: new Date(key),
      earnedValue: value,
    }
  })
}
