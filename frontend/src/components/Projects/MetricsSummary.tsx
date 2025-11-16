import { Box } from "@chakra-ui/react"
import BudgetSummary from "@/components/Projects/BudgetSummary"
import CostSummary from "@/components/Projects/CostSummary"
import EarnedValueSummary from "@/components/Projects/EarnedValueSummary"

interface MetricsSummaryProps {
  level: "project" | "wbe" | "cost-element"
  projectId?: string
  wbeId?: string
  costElementId?: string
}

export default function MetricsSummary({
  level,
  projectId,
  wbeId,
  costElementId,
}: MetricsSummaryProps) {
  return (
    <Box mt={4}>
      {level !== "cost-element" && (
        <BudgetSummary
          level={level as "project" | "wbe"}
          projectId={projectId}
          wbeId={wbeId}
        />
      )}
      <Box mt={6}>
        <CostSummary
          level={level === "cost-element" ? "cost-element" : level}
          projectId={projectId}
          wbeId={wbeId}
          costElementId={costElementId}
        />
      </Box>
      {level !== "cost-element" && (
        <Box mt={6}>
          <EarnedValueSummary
            level={level}
            projectId={projectId}
            wbeId={wbeId}
            costElementId={costElementId}
          />
        </Box>
      )}
    </Box>
  )
}
