import {
  Box,
  Button,
  DialogActionTrigger,
  DialogBody,
  DialogCloseTrigger,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogRoot,
  DialogTitle,
  Text,
  VStack,
} from "@chakra-ui/react"
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { BranchComparisonService, ChangeOrdersService } from "@/client"
import type { ApiError } from "@/client/core/ApiError"
import useCustomToast from "@/hooks/useCustomToast"
import { handleError } from "@/utils"
import BranchComparisonView from "./BranchComparisonView"

interface MergeBranchDialogProps {
  projectId: string
  branch: string
  changeOrderId: string
  isOpen: boolean
  onClose: () => void
}

const MergeBranchDialog = ({
  projectId,
  branch,
  changeOrderId,
  isOpen,
  onClose,
}: MergeBranchDialogProps) => {
  const queryClient = useQueryClient()
  const { showSuccessToast } = useCustomToast()

  // Fetch comparison data
  const { data: comparisonData, isLoading: isLoadingComparison } = useQuery({
    queryKey: ["branch-comparison", projectId, branch, "main"],
    queryFn: () =>
      BranchComparisonService.compareBranches({
        projectId,
        branch,
        baseBranch: "main",
      }),
    enabled: isOpen && !!projectId && !!branch,
  })

  // Mutation to transition change order status (approve → execute triggers merge)
  const mergeMutation = useMutation({
    mutationFn: () =>
      ChangeOrdersService.transitionChangeOrderStatus({
        projectId,
        changeOrderId,
        requestBody: {
          workflow_status: "execute",
        },
      }),
    onSuccess: () => {
      showSuccessToast("Branch merged successfully.")
      queryClient.invalidateQueries({ queryKey: ["change-orders"] })
      queryClient.invalidateQueries({ queryKey: ["wbes"] })
      queryClient.invalidateQueries({ queryKey: ["cost-elements"] })
      onClose()
    },
    onError: (err: ApiError) => {
      handleError(err)
    },
  })

  const handleMerge = () => {
    mergeMutation.mutate()
  }

  return (
    <DialogRoot open={isOpen} onOpenChange={({ open }) => !open && onClose()}>
      <DialogContent size={{ base: "xs", md: "xl" }}>
        <DialogHeader>
          <DialogTitle>Merge Branch: {branch}</DialogTitle>
        </DialogHeader>
        <DialogBody>
          <VStack gap={4} align="stretch">
            <Text>
              This will merge the branch <strong>{branch}</strong> into the main
              branch. Review the changes below before confirming.
            </Text>

            {isLoadingComparison ? (
              <Text>Loading comparison...</Text>
            ) : comparisonData ? (
              <Box maxH="400px" overflowY="auto">
                <BranchComparisonView
                  projectId={projectId}
                  branch={branch}
                  baseBranch="main"
                />
              </Box>
            ) : (
              <Text color="red.500">Error loading comparison data</Text>
            )}
          </VStack>
        </DialogBody>
        <DialogFooter gap={2}>
          <DialogActionTrigger asChild>
            <Button
              variant="subtle"
              colorPalette="gray"
              disabled={mergeMutation.isPending}
            >
              Cancel
            </Button>
          </DialogActionTrigger>
          <Button
            variant="solid"
            colorPalette="blue"
            onClick={handleMerge}
            disabled={mergeMutation.isPending || isLoadingComparison}
            loading={mergeMutation.isPending}
          >
            Confirm Merge
          </Button>
        </DialogFooter>
        <DialogCloseTrigger />
      </DialogContent>
    </DialogRoot>
  )
}

export default MergeBranchDialog
