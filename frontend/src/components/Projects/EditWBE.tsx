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
import { useEffect, useState } from "react"
import { Controller, type SubmitHandler, useForm } from "react-hook-form"
import { FaExchangeAlt } from "react-icons/fa"
import { type WBEPublic, type WBEUpdate, WbesService } from "@/client"
import type { ApiError } from "@/client/core/ApiError"
import useCustomToast from "@/hooks/useCustomToast"
import { useRevenueAllocationValidation } from "@/hooks/useRevenueAllocationValidation"
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

interface EditWBEProps {
  wbe: WBEPublic
}

const EditWBE = ({ wbe }: EditWBEProps) => {
  const [isOpen, setIsOpen] = useState(false)
  const queryClient = useQueryClient()
  const { showSuccessToast } = useCustomToast()
  const {
    control,
    register,
    handleSubmit,
    reset,
    watch,
    setError,
    clearErrors,
    formState: { errors, isValid, isSubmitting },
  } = useForm<WBEUpdate>({
    mode: "onBlur",
    criteriaMode: "all",
    defaultValues: {
      machine_type: wbe.machine_type,
      serial_number: wbe.serial_number,
      contracted_delivery_date: wbe.contracted_delivery_date || null,
      revenue_allocation: wbe.revenue_allocation,
      status: wbe.status,
      notes: wbe.notes,
    },
  })

  // Watch revenue_allocation for real-time validation
  const revenueAllocationValue = watch("revenue_allocation")

  // Validate revenue_allocation against project contract_value limit
  const revenueValidation = useRevenueAllocationValidation(
    wbe.project_id,
    wbe.wbe_id,
    revenueAllocationValue !== undefined
      ? Number(revenueAllocationValue)
      : undefined,
  )

  // Update form error state based on validation (using useEffect to avoid infinite loops)
  useEffect(() => {
    if (
      revenueValidation.errorMessage &&
      revenueAllocationValue !== undefined
    ) {
      setError("revenue_allocation", {
        type: "manual",
        message: revenueValidation.errorMessage,
      })
    } else if (
      !revenueValidation.errorMessage &&
      errors.revenue_allocation?.type === "manual"
    ) {
      clearErrors("revenue_allocation")
    }
  }, [
    revenueValidation.errorMessage,
    revenueAllocationValue,
    setError,
    clearErrors,
    errors.revenue_allocation?.type,
  ])

  // Form is valid only if React Hook Form validation passes AND revenue validation passes
  const isFormValid = isValid && revenueValidation.isValid

  const mutation = useMutation({
    mutationFn: (data: WBEUpdate) =>
      WbesService.updateWbe({ id: wbe.wbe_id, requestBody: data }),
    onSuccess: () => {
      showSuccessToast("WBE updated successfully.")
      reset()
      setIsOpen(false)
    },
    onError: (err: ApiError) => {
      handleError(err)
    },
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: ["wbes"] })
      queryClient.invalidateQueries({ queryKey: ["wbes", wbe.wbe_id] })
    },
  })

  const onSubmit: SubmitHandler<WBEUpdate> = (data) => {
    mutation.mutate(data)
  }

  return (
    <DialogRoot
      size={{ base: "xs", md: "lg" }}
      placement="center"
      open={isOpen}
      onOpenChange={({ open }) => setIsOpen(open)}
    >
      <DialogTrigger asChild>
        <Button variant="ghost" size="sm">
          <FaExchangeAlt fontSize="16px" />
        </Button>
      </DialogTrigger>
      <DialogContent>
        <form onSubmit={handleSubmit(onSubmit)}>
          <DialogHeader>
            <DialogTitle>Edit WBE</DialogTitle>
          </DialogHeader>
          <DialogBody>
            <Text mb={4}>Update the WBE details below.</Text>
            <VStack gap={4}>
              <Field
                required
                invalid={!!errors.machine_type}
                errorText={errors.machine_type?.message}
                label="Machine Type"
              >
                <Input
                  {...register("machine_type", {
                    required: "Machine type is required",
                  })}
                  placeholder="Machine Type"
                  type="text"
                />
              </Field>

              <Field
                invalid={!!errors.serial_number}
                errorText={errors.serial_number?.message}
                label="Serial Number"
              >
                <Input
                  {...register("serial_number")}
                  placeholder="Serial Number"
                  type="text"
                />
              </Field>

              <Field
                invalid={!!errors.contracted_delivery_date}
                errorText={errors.contracted_delivery_date?.message}
                label="Contracted Delivery Date"
              >
                <Input {...register("contracted_delivery_date")} type="date" />
              </Field>

              <Field
                invalid={
                  !!errors.revenue_allocation || !revenueValidation.isValid
                }
                errorText={
                  errors.revenue_allocation?.message ||
                  revenueValidation.errorMessage
                }
                label="Revenue Allocation"
              >
                <Input
                  {...register("revenue_allocation", {
                    min: {
                      value: 0,
                      message: "Revenue allocation must be positive",
                    },
                  })}
                  placeholder="0.00"
                  type="number"
                  step="0.01"
                />
                {revenueAllocationValue !== undefined &&
                  revenueValidation.limit > 0 && (
                    <Text fontSize="xs" color="gray.600" mt={1}>
                      Total: €
                      {revenueValidation.currentTotal.toLocaleString("en-US", {
                        minimumFractionDigits: 2,
                        maximumFractionDigits: 2,
                      })}{" "}
                      / Limit: €
                      {revenueValidation.limit.toLocaleString("en-US", {
                        minimumFractionDigits: 2,
                        maximumFractionDigits: 2,
                      })}{" "}
                      ({revenueValidation.remaining >= 0 ? "+" : ""}€
                      {revenueValidation.remaining.toLocaleString("en-US", {
                        minimumFractionDigits: 2,
                        maximumFractionDigits: 2,
                      })}{" "}
                      remaining)
                    </Text>
                  )}
              </Field>

              <Field
                invalid={!!errors.status}
                errorText={errors.status?.message}
                label="Status"
              >
                <Controller
                  control={control}
                  name="status"
                  render={({ field }) => (
                    <select
                      {...field}
                      value={field.value || ""}
                      style={{
                        width: "100%",
                        padding: "8px",
                        borderRadius: "4px",
                        border: "1px solid #e2e8f0",
                      }}
                    >
                      <option value="designing">Designing</option>
                      <option value="in-production">In Production</option>
                      <option value="shipped">Shipped</option>
                      <option value="commissioning">Commissioning</option>
                      <option value="completed">Completed</option>
                    </select>
                  )}
                />
              </Field>

              <Field
                invalid={!!errors.notes}
                errorText={errors.notes?.message}
                label="Notes"
              >
                <Textarea {...register("notes")} placeholder="Notes" rows={3} />
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
              disabled={!isFormValid || isSubmitting}
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

export default EditWBE
