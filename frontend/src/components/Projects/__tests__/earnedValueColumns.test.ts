import { describe, expect, it } from "vitest"

import { buildEarnedValueColumns } from "../earnedValueColumns"

describe("buildEarnedValueColumns", () => {
  it("creates a visible percent complete column", () => {
    const columns = buildEarnedValueColumns("cost-element-id", null)
    const percentColumn = columns.find(
      (column) =>
        "accessorKey" in column && column.accessorKey === "percent_complete",
    )
    expect(percentColumn).toBeDefined()
  })
})
