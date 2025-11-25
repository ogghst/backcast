import { Box } from "@chakra-ui/react"
import { useBranch } from "@/context/BranchContext"

const BranchSelector = () => {
  const { currentBranch, setCurrentBranch, availableBranches, isLoading } =
    useBranch()

  return (
    <Box>
      <select
        value={currentBranch}
        onChange={(e) => setCurrentBranch(e.target.value)}
        disabled={isLoading}
        style={{
          width: "200px",
          padding: "6px 8px",
          borderRadius: "4px",
          border: "1px solid var(--chakra-colors-border)",
          fontSize: "14px",
        }}
        aria-label="Select branch"
      >
        {availableBranches.map((branch) => (
          <option key={branch} value={branch}>
            {branch}
          </option>
        ))}
      </select>
    </Box>
  )
}

export default BranchSelector
