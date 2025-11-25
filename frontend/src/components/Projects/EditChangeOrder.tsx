import {
  Button,
  DialogActionTrigger,
  DialogTitle,
  Input,
  Text,
  Textarea,
  VStack,
} from "@chakra-ui/react"
import { useMutation, useQueryClient } from "@tanstack/react-query"
import { useState } from "react"
import { Controller, type SubmitHandler, useForm } from "react-hook-form"
import { FaExchangeAlt } from "react-icons/fa"
import {
  type ApiError,
  type ChangeOrderPublic,
  ChangeOrdersService,
  type ChangeOrderUpdate,
} from "@/client"
import { handleError } from "@/utils"
import {
  DialogBody,
  DialogCloseTrigger,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogRoot,
  DialogTrigger,
} from "../ui/dialog"
import { Field } from "../ui/field"

interface EditChangeOrderProps {
  changeOrder: ChangeOrderPublic
}

const EditChangeOrder = ({ changeOrder }: EditChangeOrderProps) => {
  const [isOpen, setIsOpen] = useState(false)
  const queryClient = useQueryClient()

  // Only allow editing in 'design' status
  const canEdit = changeOrder.workflow_status === "design"

  const {
    control,
    register,
    handleSubmit,
    reset,
    formState: { errors, isValid, isSubmitting },
  } = useForm<ChangeOrderUpdate>({
    mode: "onBlur",
    criteriaMode: "all",
    defaultValues: {
      title: changeOrder.title,
      description: changeOrder.description,
      requesting_party: changeOrder.requesting_party,
      justification: changeOrder.justification,
      effective_date: changeOrder.effective_date,
      cost_impact: changeOrder.cost_impact
        ? parseFloat(changeOrder.cost_impact)
        : null,
      revenue_impact: changeOrder.revenue_impact
        ? parseFloat(changeOrder.revenue_impact)
        : null,
      workflow_status: changeOrder.workflow_status,
    },
  })

  const mutation = useMutation({
    mutationFn: (data: ChangeOrderUpdate) =>
      ChangeOrdersService.updateChangeOrder({
        projectId: changeOrder.project_id,
        changeOrderId: changeOrder.change_order_id,
        requestBody: data,
      }),
    onSuccess: () => {
      reset()
      setIsOpen(false)
    },
    onError: (err: ApiError) => {
      handleError(err)
    },
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: ["change-orders"] })
      queryClient.invalidateQueries({
        queryKey: ["change-orders", changeOrder.change_order_id],
      })
    },
  })

  const onSubmit: SubmitHandler<ChangeOrderUpdate> = async (data) => {
    if (!canEdit) {
      return
    }
    await mutation.mutateAsync(data)
  }

  return (
    <DialogRoot
      size={{ base: "xs", md: "xl" }}
      placement="center"
      open={isOpen}
      onOpenChange={({ open }) => setIsOpen(open)}
    >
      <DialogTrigger asChild>
        <Button
          variant="ghost"
          size="sm"
          aria-label="Edit change order"
          title="Edit change order"
          disabled={!canEdit}
        >
          <FaExchangeAlt fontSize="16px" />
        </Button>
      </DialogTrigger>
      <DialogContent>
        <form onSubmit={handleSubmit(onSubmit)}>
          <DialogHeader>
            <DialogTitle>Edit Change Order</DialogTitle>
          </DialogHeader>
          <DialogBody>
            {!canEdit && (
              <Text mb={4} color="fg.error">
                This change order cannot be edited because it is not in 'design'
                status.
              </Text>
            )}
            <Text mb={4}>Update the change order details below.</Text>
            <VStack gap={4}>
              <Field
                required
                invalid={!!errors.title}
                errorText={errors.title?.message}
                label="Title"
              >
                <Input
                  {...register("title", {
                    required: "Title is required",
                  })}
                  placeholder="Change Order Title"
                  type="text"
                  disabled={!canEdit}
                />
              </Field>

              <Field
                required
                invalid={!!errors.description}
                errorText={errors.description?.message}
                label="Description"
              >
                <Textarea
                  {...register("description", {
                    required: "Description is required",
                  })}
                  placeholder="Change Order Description"
                  rows={4}
                  disabled={!canEdit}
                />
              </Field>

              <Field
                required
                invalid={!!errors.requesting_party}
                errorText={errors.requesting_party?.message}
                label="Requesting Party"
              >
                <Input
                  {...register("requesting_party", {
                    required: "Requesting party is required",
                  })}
                  placeholder="Requesting Party"
                  type="text"
                  disabled={!canEdit}
                />
              </Field>

              <Field
                invalid={!!errors.justification}
                errorText={errors.justification?.message}
                label="Justification"
              >
                <Textarea
                  {...register("justification")}
                  placeholder="Justification (optional)"
                  rows={3}
                  disabled={!canEdit}
                />
              </Field>

              <Field
                required
                invalid={!!errors.effective_date}
                errorText={errors.effective_date?.message}
                label="Effective Date"
              >
                <Input
                  {...register("effective_date", {
                    required: "Effective date is required",
                  })}
                  type="date"
                  disabled={!canEdit}
                />
              </Field>

              <Field
                invalid={!!errors.cost_impact}
                errorText={errors.cost_impact?.message}
                label="Cost Impact"
              >
                <Input
                  {...register("cost_impact", {
                    min: {
                      value: 0,
                      message: "Cost impact must be positive",
                    },
                  })}
                  placeholder="0.00"
                  type="number"
                  step="0.01"
                  disabled={!canEdit}
                />
              </Field>

              <Field
                invalid={!!errors.revenue_impact}
                errorText={errors.revenue_impact?.message}
                label="Revenue Impact"
              >
                <Input
                  {...register("revenue_impact", {
                    min: {
                      value: 0,
                      message: "Revenue impact must be positive",
                    },
                  })}
                  placeholder="0.00"
                  type="number"
                  step="0.01"
                  disabled={!canEdit}
                />
              </Field>

              <Field
                required
                invalid={!!errors.workflow_status}
                errorText={errors.workflow_status?.message}
                label="Workflow Status"
              >
                <Controller
                  control={control}
                  name="workflow_status"
                  rules={{ required: "Workflow status is required" }}
                  render={({ field }) => (
                    <select
                      {...field}
                      value={field.value || ""}
                      disabled={!canEdit}
                      style={{
                        width: "100%",
                        padding: "8px",
                        borderRadius: "4px",
                        border: errors.workflow_status
                          ? "1px solid #ef4444"
                          : "1px solid #e2e8f0",
                      }}
                    >
                      <option value="design">Design</option>
                      <option value="approve">Approve</option>
                      <option value="execute">Execute</option>
                    </select>
                  )}
                />
              </Field>
            </VStack>
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
              type="submit"
              disabled={!isValid || isSubmitting || !canEdit}
              loading={isSubmitting}
            >
              Save
            </Button>
          </DialogFooter>
        </form>
        <DialogCloseTrigger />
      </DialogContent>
    </DialogRoot>
  )
}

export default EditChangeOrder
