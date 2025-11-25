import { Button } from "@chakra-ui/react"
import { useMutation, useQueryClient } from "@tanstack/react-query"
import { RestoreService } from "@/client"
import type { ApiError } from "@/client/core/ApiError"
import useCustomToast from "@/hooks/useCustomToast"
import { handleError } from "@/utils"

interface RestoreEntityProps {
  entityType: "wbe" | "costelement" | "changeorder" | "project"
  entityId: string
  branch?: string
}

const RestoreEntity = ({
  entityType,
  entityId,
  branch,
}: RestoreEntityProps) => {
  const queryClient = useQueryClient()
  const { showSuccessToast } = useCustomToast()

  const restoreMutation = useMutation({
    mutationFn: () => {
      switch (entityType) {
        case "wbe":
          return RestoreService.restoreWbe({
            wbeId: entityId,
            branch,
          })
        case "costelement":
          return RestoreService.restoreCostElement({
            costElementId: entityId,
            branch,
          })
        case "changeorder":
          return RestoreService.restoreChangeOrder({
            changeOrderId: entityId,
          })
        case "project":
          return RestoreService.restoreProject({
            projectId: entityId,
          })
        default:
          throw new Error(`Unsupported entity type: ${entityType}`)
      }
    },
    onSuccess: () => {
      showSuccessToast(`${entityType} restored successfully.`)
      queryClient.invalidateQueries({
        queryKey: [
          entityType === "wbe"
            ? "wbes"
            : entityType === "costelement"
              ? "cost-elements"
              : entityType === "changeorder"
                ? "change-orders"
                : "projects",
        ],
      })
    },
    onError: (err: ApiError) => {
      handleError(err)
    },
  })

  return (
    <Button
      variant="outline"
      colorPalette="green"
      size="sm"
      onClick={() => restoreMutation.mutate()}
      disabled={restoreMutation.isPending}
      loading={restoreMutation.isPending}
    >
      Restore
    </Button>
  )
}

export default RestoreEntity
