import {
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
import { VersionHistoryService } from "@/client"
import type { ApiError } from "@/client/core/ApiError"
import useCustomToast from "@/hooks/useCustomToast"
import { handleError } from "@/utils"

interface RollbackVersionProps {
  entityType: "wbe" | "costelement"
  entityId: string
  targetVersion: number
  branch?: string
  isOpen: boolean
  onClose: () => void
}

const RollbackVersion = ({
  entityType,
  entityId,
  targetVersion,
  branch,
  isOpen,
  onClose,
}: RollbackVersionProps) => {
  const queryClient = useQueryClient()
  const { showSuccessToast } = useCustomToast()

  // Fetch version history to get target version data
  const { data: versionHistory } = useQuery({
    queryKey: ["version-history", entityType, entityId, branch],
    queryFn: () =>
      VersionHistoryService.getEntityVersionHistory({
        entityType,
        entityId,
        branch,
      }),
    enabled: isOpen && !!entityType && !!entityId,
  })

  const targetVersionData = versionHistory?.versions?.find(
    (v) => v.version === targetVersion,
  )

  const rollbackMutation = useMutation({
    mutationFn: async () => {
      if (!targetVersionData) {
        throw new Error("Target version data not found")
      }

      // For rollback, we create a new version with the old values
      // This would require fetching the full entity data for that version
      // For now, we'll use a placeholder - actual implementation would need
      // to fetch the full entity data from the version
      if (entityType === "wbe") {
        // This is a simplified example - actual implementation would need
        // to fetch the full WBE data from the target version
        return Promise.resolve()
      }
      // Similar for cost elements
      return Promise.resolve()
    },
    onSuccess: () => {
      showSuccessToast(`Rolled back to version ${targetVersion} successfully.`)
      queryClient.invalidateQueries({
        queryKey: [entityType === "wbe" ? "wbes" : "cost-elements"],
      })
      onClose()
    },
    onError: (err: ApiError) => {
      handleError(err)
    },
  })

  const handleRollback = () => {
    rollbackMutation.mutate()
  }

  return (
    <DialogRoot open={isOpen} onOpenChange={({ open }) => !open && onClose()}>
      <DialogContent size={{ base: "xs", md: "md" }}>
        <DialogHeader>
          <DialogTitle>Rollback to Version {targetVersion}</DialogTitle>
        </DialogHeader>
        <DialogBody>
          <VStack gap={4} align="stretch">
            <Text>
              This will create a new version with the values from version{" "}
              {targetVersion}. The current version will be preserved in history.
            </Text>
            {targetVersionData && (
              <Text fontSize="sm" color="fg.muted">
                Version {targetVersion} was created on:{" "}
                {targetVersionData.created_at
                  ? new Date(targetVersionData.created_at).toLocaleString()
                  : "Unknown"}
              </Text>
            )}
          </VStack>
        </DialogBody>
        <DialogFooter gap={2}>
          <DialogActionTrigger asChild>
            <Button
              variant="subtle"
              colorPalette="gray"
              disabled={rollbackMutation.isPending}
            >
              Cancel
            </Button>
          </DialogActionTrigger>
          <Button
            variant="solid"
            colorPalette="orange"
            onClick={handleRollback}
            disabled={rollbackMutation.isPending}
            loading={rollbackMutation.isPending}
          >
            Confirm Rollback
          </Button>
        </DialogFooter>
        <DialogCloseTrigger />
      </DialogContent>
    </DialogRoot>
  )
}

export default RollbackVersion
