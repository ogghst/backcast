import { describe, expect, it } from "vitest"

import { createBudgetTimelineConfig } from "../BudgetTimeline"

const sampleDates = {
  jan1: new Date("2024-01-01T00:00:00.000Z"),
  jan2: new Date("2024-01-02T00:00:00.000Z"),
}

describe("BudgetTimeline chart configuration", () => {
  it("includes PV, AC, and EV datasets in aggregated view", () => {
    const config = createBudgetTimelineConfig({
      viewMode: "aggregated",
      plannedValue: [
        {
          label: "Planned Value (PV)",
          data: [
            { x: sampleDates.jan1, y: 100 },
            { x: sampleDates.jan2, y: 200 },
          ],
        },
      ],
      actualCost: [
        { x: sampleDates.jan1, y: 80 },
        { x: sampleDates.jan2, y: 160 },
      ],
      earnedValue: [
        { date: sampleDates.jan1, earnedValue: 70 },
        { date: sampleDates.jan2, earnedValue: 120 },
      ],
    })

    const labels = config.datasets.map((dataset) => dataset.label)
    expect(labels).toContain("Planned Value (PV)")
    expect(labels).toContain("Actual Cost (AC)")
    expect(labels).toContain("Earned Value (EV)")
  })

  it("keeps earned value line styling aligned with actual cost styling", () => {
    const config = createBudgetTimelineConfig({
      viewMode: "aggregated",
      plannedValue: [],
      actualCost: [{ x: sampleDates.jan1, y: 10 }],
      earnedValue: [{ date: sampleDates.jan1, earnedValue: 5 }],
    })

    const actualCostDataset = config.datasets.find(
      (dataset) => dataset.label === "Actual Cost (AC)",
    )
    const earnedValueDataset = config.datasets.find(
      (dataset) => dataset.label === "Earned Value (EV)",
    )

    expect(actualCostDataset).toBeDefined()
    expect(earnedValueDataset).toBeDefined()
    expect(earnedValueDataset?.borderColor).toEqual(
      actualCostDataset?.borderColor,
    )
    expect(earnedValueDataset?.borderDash).toEqual(
      actualCostDataset?.borderDash,
    )
  })

  it("leaves earned value data as provided (no cumulative transformation)", () => {
    const config = createBudgetTimelineConfig({
      viewMode: "aggregated",
      plannedValue: [],
      actualCost: [],
      earnedValue: [
        { date: sampleDates.jan1, earnedValue: 100 },
        { date: sampleDates.jan2, earnedValue: 50 },
      ],
    })

    const earnedValueDataset = config.datasets.find(
      (dataset) => dataset.label === "Earned Value (EV)",
    )

    expect(earnedValueDataset?.data).toEqual([
      { x: sampleDates.jan1, y: 100 },
      { x: sampleDates.jan2, y: 50 },
    ])
  })

  it("formats tooltip labels for every measure", () => {
    const config = createBudgetTimelineConfig({
      viewMode: "aggregated",
      plannedValue: [],
      actualCost: [{ x: sampleDates.jan1, y: 42 }],
      earnedValue: [{ date: sampleDates.jan1, earnedValue: 21 }],
    })

    const tooltipLabel = config.options.plugins?.tooltip?.callbacks?.label
    const actualCostDataset = config.datasets.find(
      (dataset) => dataset.label === "Actual Cost (AC)",
    )
    const earnedValueDataset = config.datasets.find(
      (dataset) => dataset.label === "Earned Value (EV)",
    )

    expect(tooltipLabel).toBeTypeOf("function")
    expect(actualCostDataset).toBeDefined()
    expect(earnedValueDataset).toBeDefined()

    const acLabel = tooltipLabel!.call(
      {} as any,
      {
        dataset: actualCostDataset,
        parsed: { y: 42 },
      } as any,
    )
    const evLabel = tooltipLabel!.call(
      {} as any,
      {
        dataset: earnedValueDataset,
        parsed: { y: 21 },
      } as any,
    )

    expect(acLabel).toContain("Actual Cost (AC)")
    expect(acLabel).toContain("€42.00")
    expect(evLabel).toContain("Earned Value (EV)")
    expect(evLabel).toContain("€21.00")
  })
})
