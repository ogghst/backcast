import { useQuery, useQueryClient } from "@tanstack/react-query"
import {
  createContext,
  type PropsWithChildren,
  useCallback,
  useContext,
  useMemo,
  useState,
} from "react"

import { ChangeOrdersService } from "@/client"

type BranchContextValue = {
  currentBranch: string
  isLoading: boolean
  setCurrentBranch: (branch: string) => void
  availableBranches: string[]
}

const BranchContext = createContext<BranchContextValue | undefined>(undefined)

export function BranchProvider({
  children,
  projectId,
}: PropsWithChildren<{ projectId: string }>) {
  const queryClient = useQueryClient()
  const [currentBranch, setCurrentBranchState] = useState<string>("main")

  // Fetch change orders to get available branches
  const { data: changeOrdersData, isLoading } = useQuery({
    queryKey: ["change-orders", projectId],
    queryFn: () =>
      ChangeOrdersService.listChangeOrders({
        projectId,
        skip: 0,
        limit: 1000,
      }),
    enabled: !!projectId,
    staleTime: 5 * 60 * 1000, // 5 minutes
  })

  // Extract unique branches from change orders
  const availableBranches = useMemo(() => {
    const branches = new Set<string>(["main"]) // Always include 'main'
    changeOrdersData?.forEach((co) => {
      if (co.branch) {
        branches.add(co.branch)
      }
    })
    return Array.from(branches).sort()
  }, [changeOrdersData])

  const setCurrentBranch = useCallback(
    (branch: string) => {
      setCurrentBranchState(branch)
      // Invalidate queries that depend on branch
      queryClient.invalidateQueries({
        predicate: (query) => {
          // Invalidate queries that have branch in their key or are branch-dependent
          const key = query.queryKey
          return (
            key.includes("wbes") ||
            key.includes("cost-elements") ||
            key.includes("change-orders")
          )
        },
        refetchType: "active",
      })
    },
    [queryClient],
  )

  const value = useMemo<BranchContextValue>(
    () => ({
      currentBranch,
      isLoading,
      setCurrentBranch,
      availableBranches,
    }),
    [currentBranch, isLoading, setCurrentBranch, availableBranches],
  )

  return (
    <BranchContext.Provider value={value}>{children}</BranchContext.Provider>
  )
}

export function useBranch() {
  const context = useContext(BranchContext)
  if (!context) {
    throw new Error("useBranch must be used within a BranchProvider")
  }
  return context
}
