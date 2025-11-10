import { describe, expect, it } from "vitest"

import { buildEarnedValueTimeline } from "@/utils/earnedValueAggregation"

describe("buildEarnedValueTimeline", () => {
  it("returns absolute earned value for each date without cumulative aggregation", () => {
    const results = buildEarnedValueTimeline({
      entries: [
        {
          earned_value: 100,
          completion_date: "2024-01-01",
        },
        {
          earned_value: 50,
          completion_date: "2024-01-01",
        },
        {
          earned_value: 75,
          completion_date: "2024-01-02",
        },
      ] as any,
    })

    expect(results).toHaveLength(2)
    expect(results[0]).toMatchObject({
      date: new Date("2024-01-01"),
      earnedValue: 150,
    })
    expect(results[1]).toMatchObject({
      date: new Date("2024-01-02"),
      earnedValue: 75,
    })
  })
})
