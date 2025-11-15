import { Button, DialogTitle, Text } from "@chakra-ui/react"
import { useMutation, useQueryClient } from "@tanstack/react-query"
import { useState } from "react"
import { useForm } from "react-hook-form"
import { FiXCircle } from "react-icons/fi"
import { BaselineLogsService } from "@/client"
import type { ApiError } from "@/client/core/ApiError"
import {
  DialogActionTrigger,
  DialogBody,
  DialogCloseTrigger,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogRoot,
  DialogTrigger,
} from "@/components/ui/dialog"
import { useTimeMachine } from "@/context/TimeMachineContext"
import useCustomToast from "@/hooks/useCustomToast"
import { handleError } from "@/utils"

interface CancelBaselineLogProps {
  baselineId: string
  projectId: string
  description?: string | null
}

const CancelBaselineLog = ({
  baselineId,
  projectId,
  description,
}: CancelBaselineLogProps) => {
  const [isOpen, setIsOpen] = useState(false)
  const queryClient = useQueryClient()
  const { controlDate } = useTimeMachine()
  const { showSuccessToast } = useCustomToast()
  const {
    handleSubmit,
    formState: { isSubmitting },
  } = useForm()

  const mutation = useMutation({
    mutationFn: () =>
      BaselineLogsService.cancelBaselineLog({
        projectId,
        baselineId,
      }),
    onSuccess: () => {
      showSuccessToast("Baseline cancelled successfully")
      setIsOpen(false)
    },
    onError: (err: ApiError) => {
      handleError(err)
    },
    onSettled: () => {
      queryClient.invalidateQueries({
        queryKey: ["baseline-logs", { projectId }, controlDate],
      })
    },
  })

  const onSubmit = async () => {
    mutation.mutate()
  }

  return (
    <DialogRoot
      size={{ base: "xs", md: "md" }}
      placement="center"
      role="alertdialog"
      open={isOpen}
      onOpenChange={({ open }) => setIsOpen(open)}
    >
      <DialogTrigger asChild>
        <Button variant="ghost" size="sm" colorPalette="red">
          <FiXCircle fontSize="16px" />
        </Button>
      </DialogTrigger>
      <DialogContent>
        <form onSubmit={handleSubmit(onSubmit)}>
          <DialogHeader>
            <DialogTitle>Cancel Baseline</DialogTitle>
          </DialogHeader>
          <DialogBody>
            <Text mb={4}>
              Are you sure you want to cancel this baseline?
              {description && (
                <>
                  <br />
                  <strong>{description}</strong>
                </>
              )}
              <br />
              <br />
              This will mark the baseline as cancelled (soft delete). The
              baseline and its snapshot data will be preserved but will no
              longer be active. This action can be reversed by editing the
              baseline.
            </Text>
          </DialogBody>

          <DialogFooter gap={2}>
            <DialogActionTrigger asChild>
              <Button
                variant="subtle"
                colorPalette="gray"
                disabled={isSubmitting}
              >
                Cancel
              </Button>
            </DialogActionTrigger>
            <Button
              variant="solid"
              colorPalette="red"
              type="submit"
              loading={isSubmitting}
            >
              Cancel Baseline
            </Button>
          </DialogFooter>
          <DialogCloseTrigger />
        </form>
      </DialogContent>
    </DialogRoot>
  )
}

export default CancelBaselineLog
