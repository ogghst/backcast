import { Box, Heading, Text } from "@chakra-ui/react"
import { useQuery } from "@tanstack/react-query"
import { BranchComparisonService } from "@/client"
import BranchComparisonView from "./BranchComparisonView"

interface BranchDiffVisualizationProps {
  projectId: string
  branch: string
  baseBranch?: string
}

const BranchDiffVisualization = ({
  projectId,
  branch,
  baseBranch = "main",
}: BranchDiffVisualizationProps) => {
  const { data, isLoading } = useQuery({
    queryKey: ["branch-comparison", projectId, branch, baseBranch],
    queryFn: () =>
      BranchComparisonService.compareBranches({
        projectId,
        branch,
        baseBranch,
      }),
    enabled: !!projectId && !!branch && branch !== baseBranch,
  })

  if (isLoading) {
    return (
      <Box p={4}>
        <Text>Loading diff visualization...</Text>
      </Box>
    )
  }

  if (!data) {
    return (
      <Box p={4}>
        <Text>No diff data available</Text>
      </Box>
    )
  }

  return (
    <Box p={4}>
      <Heading size="sm" mb={4}>
        Branch Diff: {branch} vs {baseBranch}
      </Heading>
      <BranchComparisonView
        projectId={projectId}
        branch={branch}
        baseBranch={baseBranch}
      />
    </Box>
  )
}

export default BranchDiffVisualization
