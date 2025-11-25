import { Button } from "@chakra-ui/react"
import { useMutation, useQueryClient } from "@tanstack/react-query"
import { useState } from "react"
import { FaTrash } from "react-icons/fa"
import { type ApiError, ChangeOrdersService } from "@/client"
import useCustomToast from "@/hooks/useCustomToast"
import { handleError } from "@/utils"
import {
  DialogBody,
  DialogCloseTrigger,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogRoot,
  DialogTitle,
  DialogTrigger,
} from "../ui/dialog"

interface DeleteChangeOrderProps {
  changeOrderId: string
  changeOrderNumber: string
  projectId: string
}

const DeleteChangeOrder = ({
  changeOrderId,
  changeOrderNumber,
  projectId,
}: DeleteChangeOrderProps) => {
  const [isOpen, setIsOpen] = useState(false)
  const queryClient = useQueryClient()
  const { showSuccessToast } = useCustomToast()

  const mutation = useMutation({
    mutationFn: () =>
      ChangeOrdersService.deleteChangeOrder({
        projectId,
        changeOrderId,
      }),
    onSuccess: () => {
      showSuccessToast("Change Order deleted successfully.")
      setIsOpen(false)
    },
    onError: (err: ApiError) => {
      handleError(err)
    },
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: ["change-orders"] })
    },
  })

  const handleDelete = () => {
    mutation.mutate()
  }

  return (
    <DialogRoot
      size={{ base: "xs", md: "md" }}
      placement="center"
      open={isOpen}
      onOpenChange={({ open }) => setIsOpen(open)}
    >
      <DialogTrigger asChild>
        <Button
          variant="ghost"
          size="sm"
          aria-label="Delete change order"
          title="Delete change order"
          colorPalette="red"
        >
          <FaTrash fontSize="16px" />
        </Button>
      </DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Delete Change Order</DialogTitle>
        </DialogHeader>
        <DialogBody>
          <p>
            Are you sure you want to delete change order{" "}
            <strong>{changeOrderNumber}</strong>? This action cannot be undone.
          </p>
        </DialogBody>
        <DialogFooter gap={2}>
          <DialogCloseTrigger asChild>
            <Button
              variant="subtle"
              colorPalette="gray"
              disabled={mutation.isPending}
            >
              Cancel
            </Button>
          </DialogCloseTrigger>
          <Button
            variant="solid"
            colorPalette="red"
            onClick={handleDelete}
            disabled={mutation.isPending}
            loading={mutation.isPending}
          >
            Delete
          </Button>
        </DialogFooter>
        <DialogCloseTrigger />
      </DialogContent>
    </DialogRoot>
  )
}

export default DeleteChangeOrder
