import { Button, DialogTitle, Text } from "@chakra-ui/react"
import { useMutation, useQueryClient } from "@tanstack/react-query"
import { useState } from "react"
import { useForm } from "react-hook-form"
import { FiTrash2 } from "react-icons/fi"

import { ForecastsService } from "@/client"
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
import useCustomToast from "@/hooks/useCustomToast"
import { handleError } from "@/utils"

interface DeleteForecastProps {
  forecastId: string
  isCurrent: boolean
  forecastDate: string
  eac: string | number
}

const DeleteForecast = ({
  forecastId,
  isCurrent,
  forecastDate,
  eac,
}: DeleteForecastProps) => {
  const [isOpen, setIsOpen] = useState(false)
  const queryClient = useQueryClient()
  const { showSuccessToast } = useCustomToast()
  const {
    handleSubmit,
    formState: { isSubmitting },
  } = useForm()

  const mutation = useMutation({
    mutationFn: () =>
      ForecastsService.deleteForecast({
        forecastId,
      }),
    onSuccess: () => {
      showSuccessToast(
        isCurrent
          ? "Forecast deleted. Previous forecast has been promoted to current."
          : "Forecast deleted successfully.",
      )
      setIsOpen(false)
    },
    onError: (error: ApiError) => {
      handleError(error)
    },
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: ["forecasts"] })
    },
  })

  const onSubmit = () => {
    mutation.mutate()
  }

  const eacFormatted = typeof eac === "string" ? parseFloat(eac) : Number(eac)
  const eacDisplay = Number.isNaN(eacFormatted)
    ? "N/A"
    : `€${eacFormatted.toLocaleString("en-US", {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2,
      })}`

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
          <FiTrash2 fontSize="16px" />
        </Button>
      </DialogTrigger>
      <DialogContent>
        <form onSubmit={handleSubmit(onSubmit)}>
          <DialogHeader>
            <DialogTitle>Delete Forecast</DialogTitle>
          </DialogHeader>
          <DialogBody>
            <Text mb={4}>
              Are you sure you want to delete this forecast?
              <br />
              <strong>
                Date: {new Date(forecastDate).toLocaleDateString()}, EAC:{" "}
                {eacDisplay}
              </strong>
              {isCurrent && (
                <>
                  <br />
                  <br />
                  <Text color="orange.500" fontWeight="semibold">
                    This is the current forecast. The previous forecast will be
                    automatically promoted to current.
                  </Text>
                </>
              )}
              <br />
              <br />
              This action cannot be undone.
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
              Delete
            </Button>
          </DialogFooter>
          <DialogCloseTrigger />
        </form>
      </DialogContent>
    </DialogRoot>
  )
}

export default DeleteForecast
